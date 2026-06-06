"""NestAI agent pipeline — optimised for low latency.

Changes vs original 6-node design:
  - parse_intent result cached in Redis (identical queries skip GPT call entirely)
  - RLHF few-shot fetch runs in parallel with parse_intent via asyncio.gather
  - per-listing commute + fraud enrichment runs in parallel via asyncio.gather
  - Nodes 4 (compare) and 5 (validate_comparison) REMOVED — they added 3-5 s of
    blocking Sonnet calls before streaming could start. The single streaming Node 4
    now does compare + explain in one shot, so the first token arrives 3-5 s sooner.
  - SSE progress events emitted between nodes so the user sees activity immediately
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.llm_router import call_llm, stream_llm
from core.security import sanitize_llm_input
from modules.agent.schemas import AgentState
from modules.agent.repository import AgentRepository
from modules.agent import tools as mcp

logger = logging.getLogger(__name__)

INTENT_CACHE_TTL = 3600   # 1 h — identical query → same intent


# ── helpers ───────────────────────────────────────────────────────────────────

def _progress(text: str) -> str:
    """SSE progress frame — frontend filters by type='progress'."""
    return f'data: {json.dumps({"type": "progress", "text": text})}\n\n'


def _token(text: str) -> str:
    return f"data: {text}\n\n"


# ── Node 1: parse_intent ──────────────────────────────────────────────────────

async def _fetch_rlhf(db: AsyncSession) -> str:
    """Fetch top-rated examples for few-shot injection (runs in parallel with parse_intent)."""
    try:
        repo = AgentRepository(db)
        good = await repo.get_good_responses(limit=3)
        if not good:
            return ""
        lines = "\n".join(
            f"Example query: {ex['query']}\nExample response excerpt: {ex['response']}"
            for ex in good
        )
        return (
            "\n\nHere are highly-rated past responses (use as quality guidance):\n"
            + lines + "\n"
        )
    except Exception as e:
        logger.warning("_fetch_rlhf | failed: %s", e)
        return ""


async def parse_intent_node(state: AgentState, db: AsyncSession, redis: aioredis.Redis) -> dict:
    query = sanitize_llm_input(state["query"])

    # Cache key: sha256 of the sanitised query
    cache_key = "intent:" + hashlib.sha256(query.encode()).hexdigest()[:24]
    cached = await redis.get(cache_key)
    if cached:
        logger.info("parse_intent | cache hit")
        try:
            return {"intent": json.loads(cached)}
        except Exception:
            pass

    # Run RLHF fetch and the LLM call in parallel
    few_shot_task = asyncio.create_task(_fetch_rlhf(db))

    prompt_base = (
        "Extract the housing search intent from the following query. "
        "Return JSON with keys: area (string or null), bedrooms (int or null), "
        "min_price (int or null), max_price (int or null), must_haves (list of strings). "
        f"Query: {query}"
    )
    # call_llm is sync — run in executor so it doesn't block the event loop
    loop = asyncio.get_event_loop()
    raw, few_shot = await asyncio.gather(
        loop.run_in_executor(None, lambda: call_llm("parse_intent", prompt_base, max_tokens=300)),
        few_shot_task,
    )

    try:
        intent = json.loads(raw)
        if not isinstance(intent, dict):
            intent = {}
    except Exception:
        intent = {}

    # Store few-shot examples for later use in the streaming node
    intent["_few_shot"] = few_shot

    # Cache the intent so the next identical query is instant
    try:
        await redis.setex(cache_key, INTENT_CACHE_TTL, json.dumps(intent))
    except Exception:
        pass

    return {"intent": intent}


# ── Node 2: search_and_rank (parallel enrichment) ─────────────────────────────

async def _enrich_listing(listing: dict, intent: dict, db, redis) -> dict:
    """Enrich a single listing with commute + fraud in parallel."""
    enriched = dict(listing)

    async def get_commute():
        if listing.get("lat") and intent.get("university_lat"):
            return await mcp.calculate_commute(
                listing["lat"], listing["lng"],
                intent["university_lat"], intent["university_lng"],
            )
        return {"commute_minutes": None}

    async def get_fraud():
        return await mcp.check_fraud(db, redis, listing["id"])

    commute, fraud = await asyncio.gather(get_commute(), get_fraud())

    enriched["commute"] = commute
    enriched["fraud_score"] = fraud.get("score", 0.0)
    return enriched


async def search_and_rank_node(state: AgentState, db: AsyncSession, redis) -> dict:
    intent = state["intent"]
    retry = state.get("retry_count", 0)

    # Widen price filter on retries
    if retry > 0 and intent.get("max_price"):
        intent = {**intent, "max_price": int(intent["max_price"] * 1.2)}

    raw_listings = await mcp.search_listings(db, intent)

    # Enrich all listings in parallel instead of one-by-one
    enriched = await asyncio.gather(
        *[_enrich_listing(l, intent, db, redis) for l in raw_listings[:10]]
    )

    errors: list[str] = list(state.get("errors", []))
    for l in enriched:
        note = l.get("commute", {}).get("note")
        if note:
            errors.append(note)

    return {"listings": list(enriched), "errors": errors}


# ── Node 3: validate_results ──────────────────────────────────────────────────

async def validate_results_node(state: AgentState, db, redis) -> dict:
    if not state["listings"] and state.get("retry_count", 0) < 2:
        return {"retry_count": state.get("retry_count", 0) + 1}
    return {}


def _should_retry(state: AgentState) -> bool:
    return not state["listings"] and state.get("retry_count", 0) < 2


# ── Node 4: stream_compare_and_respond ────────────────────────────────────────
# Replaces the old blocking compare (Node 4) + validate_comparison (Node 5)
# + explain_and_respond (Node 6).  One Sonnet streaming call — first token
# arrives within ~0.5 s of the search completing.

async def stream_compare_and_respond_node(
    state: AgentState, db: AsyncSession, redis
) -> AsyncGenerator[str, None]:
    listings = state.get("listings", [])
    query    = state["query"]

    # No-match path
    if not listings:
        yield _token("I couldn't find any listings matching your criteria. "
                     "Try broadening your search area or adjusting your budget.")
        yield "data: [DONE]\n\n"
        await _persist_session(state, "No matches found.", db, redis)
        return

    # Build context for the single streaming call
    top = listings[:3]
    context = json.dumps(top, indent=2, default=str)
    few_shot = state.get("intent", {}).get("_few_shot", "")
    errors_note = ""
    if state.get("errors"):
        errors_note = "\nNote: " + "; ".join(state["errors"])

    prompt = sanitize_llm_input(
        f"You are a helpful housing assistant for Lebanese students.\n"
        f"A student asked: \"{query}\"\n\n"
        f"Here are the top matching listings in Beirut:\n{context}\n"
        f"{errors_note}\n"
        f"{few_shot}\n"
        "In one warm, conversational response:\n"
        "1. Compare the listings on price, location, fraud score (lower = safer), and commute\n"
        "2. Recommend the best option with a clear reason\n"
        "3. Mention any caveats (generator cost, water, etc.) specific to the neighbourhood\n"
        "Be direct and practical. 3-4 short paragraphs."
    )

    full_parts: list[str] = []
    try:
        for token in stream_llm("agent_compare_explain", prompt, max_tokens=700):
            full_parts.append(token)
            yield _token(token)
    except Exception as e:
        fallback = "I found some listings for you — please review the results above."
        logger.error("stream_compare_and_respond | streaming failed: %s", e)
        full_parts = [fallback]
        yield _token(fallback)

    yield "data: [DONE]\n\n"
    await _persist_session(state, "".join(full_parts), db, redis)


# ── session persistence ───────────────────────────────────────────────────────

async def _persist_session(state: AgentState, response: str, db: AsyncSession, redis) -> None:
    try:
        from core.redis import RedisKeys
        turn    = {"query": state["query"], "response": response}
        history = list(state.get("history", [])) + [turn]

        await redis.setex(
            RedisKeys.session(state.get("user_id", 0), state["session_id"]),
            7200,
            json.dumps({**state, "response": response, "history": history}, default=str),
        )

        # Summarise in background (GPT-4o mini) — doesn't block the response
        loop = asyncio.get_event_loop()
        history_text = "\n".join(f"Q: {t['query']}\nA: {t['response']}" for t in history[-5:])

        async def _save():
            summary = await loop.run_in_executor(
                None,
                lambda: call_llm(
                    "summarize_session",
                    f"Summarise this housing search in 2-3 sentences:\n{history_text}",
                    max_tokens=150,
                ),
            )
            repo = AgentRepository(db)
            await repo.update_session(state["session_id"], history, str(summary))

            user_id = state.get("user_id", 0)
            if user_id:
                from modules.notifications.service import NotificationsService
                await NotificationsService.publish(
                    redis, user_id, "search_complete",
                    {"query": state["query"], "listing_count": len(state.get("listings", []))},
                )

        asyncio.create_task(_save())
    except Exception as e:
        logger.error("_persist_session | failed: %s", e)


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(db: AsyncSession, redis):
    """
    Returns a callable that runs the optimised 4-step agent pipeline:
      1. parse_intent (cached + parallel RLHF fetch)
      2. search_and_rank (parallel per-listing enrichment)
      3. validate_results (retry up to 2×)
      4. stream_compare_and_respond (one Sonnet streaming call)
    """
    async def run(state: AgentState) -> AsyncGenerator[str, None]:
        # ── Step 1: parse intent ──────────────────────────────────────────────
        yield _progress("🧠 Understanding your query…")
        update = await parse_intent_node(state, db, redis)
        state = {**state, **update}

        # ── Steps 2 + 3: search with retry ───────────────────────────────────
        yield _progress("🔍 Searching listings…")
        for _ in range(3):
            update = await search_and_rank_node(state, db, redis)
            state = {**state, **update}
            update = await validate_results_node(state, db, redis)
            state = {**state, **update}
            if not _should_retry(state):
                break
            yield _progress("🔍 Widening search criteria…")

        count = len(state.get("listings", []))
        if count:
            yield _progress(f"📊 Found {count} listings — preparing recommendation…")
        else:
            yield _progress("😕 No exact matches — generating helpful response…")

        # ── Step 4: stream compare + respond ─────────────────────────────────
        async for chunk in stream_compare_and_respond_node(state, db, redis):
            yield chunk

    return run
