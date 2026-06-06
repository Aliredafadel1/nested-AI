"""3-tier LLM router with fallback chain and streaming support. Phase 2b."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Iterator

from openai import OpenAI
import anthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier → task mapping
# ---------------------------------------------------------------------------

TASK_TIERS: dict[str, str] = {
    # free tier (BGE-M3 local)
    "embed_listing":           "free",
    "embed_profile":           "free",
    "embed_query":             "free",
    "embed_rag_chunk":         "free",
    # cheap tier (GPT-4o mini)
    "parse_intent":            "cheap",
    "explain_compatibility":   "cheap",
    "summarize_area":          "cheap",
    "classify_fraud_text":     "cheap",
    "summarize_session":       "cheap",
    # powerful tier (Claude Sonnet)
    "agent_compare_explain":   "powerful",
    "analyze_contract":        "powerful",
    "ocr_analyze_contract":    "powerful",
    "validate_coherence":      "powerful",
}

TIER_MODELS: dict[str, str] = {
    "powerful": "claude-sonnet-4-5",
    "cheap":    "gpt-4o-mini",
    "free":     "bge-m3",
}

# ---------------------------------------------------------------------------
# Clients (lazy-initialised)
# ---------------------------------------------------------------------------

def _anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Per-tier call helpers
# ---------------------------------------------------------------------------

def _call_powerful(prompt: str, **kwargs) -> str:
    model = TIER_MODELS["powerful"]
    max_tokens = kwargs.get("max_tokens", 1024)
    system = kwargs.get("system", "You are a helpful assistant.")
    client = _anthropic_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_cheap(prompt: str, **kwargs) -> str:
    model = TIER_MODELS["cheap"]
    max_tokens = kwargs.get("max_tokens", 1024)
    system = kwargs.get("system", "You are a helpful assistant.")
    client = _openai_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _call_free(prompt: str, **kwargs) -> list[float]:
    """Delegates to the worker-level BGE-M3 singleton in core.embeddings."""
    from core.embeddings import embed_text
    return embed_text(prompt)


# ---------------------------------------------------------------------------
# Redis stale-cache fallback helper
# ---------------------------------------------------------------------------

def _prompt_hash(task: str, prompt: str) -> str:
    return hashlib.sha256(f"{task}:{prompt}".encode()).hexdigest()[:16]


def _get_llm_cache(task: str, prompt: str) -> str | None:
    try:
        from core.redis import get_sync_redis, RedisKeys
        r = get_sync_redis()
        try:
            return r.get(RedisKeys.llm_cache(task, _prompt_hash(task, prompt)))
        finally:
            r.close()
    except Exception:
        return None


def _set_llm_cache(task: str, prompt: str, result: str, ttl: int = 6 * 3600) -> None:
    try:
        from core.redis import get_sync_redis, RedisKeys
        r = get_sync_redis()
        try:
            r.setex(RedisKeys.llm_cache(task, _prompt_hash(task, prompt)), ttl, result)
        finally:
            r.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public interface — call_llm with fallback chain
# ---------------------------------------------------------------------------

def get_tier(task: str) -> str:
    tier = TASK_TIERS.get(task)
    if tier is None:
        raise ValueError(
            f"Unknown task '{task}'. Valid tasks: {sorted(TASK_TIERS)}"
        )
    return tier


def call_llm(task: str, prompt: str, **kwargs) -> str | list[float]:
    """
    Route task to the appropriate model tier with full fallback chain.

    Fallback chain (powerful/cheap tiers only):
      Claude Sonnet → GPT-4o → GPT-4o mini → stale Redis cache → graceful message

    Returns str for powerful/cheap tiers, list[float] for free (embeddings).
    """
    tier = get_tier(task)
    model = TIER_MODELS[tier]
    logger.info("call_llm | task=%s tier=%s model=%s", task, tier, model)

    if tier == "free":
        return _call_free(prompt, **kwargs)

    # Attempt powerful tier (Claude Sonnet)
    if tier == "powerful":
        try:
            result = _call_powerful(prompt, **kwargs)
            _set_llm_cache(task, prompt, result)
            return result
        except Exception as e:
            logger.warning("call_llm | powerful tier failed: %s — trying cheap fallback", e)

    # Fallback 1: cheap tier (GPT-4o mini)
    try:
        result = _call_cheap(prompt, **kwargs)
        _set_llm_cache(task, prompt, result)
        logger.warning("call_llm | task=%s served by cheap fallback", task)
        return result
    except Exception as e:
        logger.warning("call_llm | cheap tier failed: %s — trying GPT-4o fallback", e)

    # Fallback 2: GPT-4o (non-mini)
    try:
        client = _openai_client()
        max_tokens = kwargs.get("max_tokens", 1024)
        system = kwargs.get("system", "You are a helpful assistant.")
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )
        result = response.choices[0].message.content
        _set_llm_cache(task, prompt, result)
        logger.warning("call_llm | task=%s served by gpt-4o fallback", task)
        return result
    except Exception as e:
        logger.warning("call_llm | gpt-4o fallback failed: %s — trying stale cache", e)

    # Fallback 3: stale Redis cache
    cached = _get_llm_cache(task, prompt)
    if cached:
        logger.warning("call_llm | task=%s served from stale Redis cache", task)
        return cached

    # Final: graceful degradation message
    logger.error("call_llm | task=%s all providers failed — returning graceful message", task)
    return "Service temporarily unavailable. Please try again shortly."


# ---------------------------------------------------------------------------
# Streaming variant — powerful tier only
# ---------------------------------------------------------------------------

def stream_llm(task: str, prompt: str, **kwargs) -> Iterator[str]:
    """
    Stream tokens from Claude Sonnet for the given task.
    Only valid for powerful-tier tasks. Raises ValueError otherwise.

    Yields text chunks as they arrive from the Anthropic streaming API.
    On failure, yields the fallback message as a single chunk.
    """
    tier = get_tier(task)
    if tier != "powerful":
        raise ValueError(
            f"stream_llm only supports powerful-tier tasks. "
            f"Task '{task}' is tier '{tier}'."
        )

    model = TIER_MODELS["powerful"]
    max_tokens = kwargs.get("max_tokens", 2048)
    system = kwargs.get("system", "You are a helpful assistant.")

    try:
        client = _anthropic_client()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            full_text = []
            for text in stream.text_stream:
                full_text.append(text)
                yield text
            _set_llm_cache(task, prompt, "".join(full_text))
    except Exception as e:
        logger.warning("stream_llm | streaming failed: %s — falling back to call_llm", e)
        result = call_llm(task, prompt, **kwargs)
        if isinstance(result, str):
            yield result


# ---------------------------------------------------------------------------
# Audio transcription — Whisper (not routed through call_llm; different input type)
# ---------------------------------------------------------------------------

def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio using OpenAI Whisper.
    Lives in llm_router.py to satisfy the no-SDK-calls-outside-llm_router invariant.
    """
    try:
        client = _openai_client()
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, file_bytes),
        )
        return response.text
    except Exception as e:
        logger.error("transcribe_audio | Whisper failed: %s", e)
        raise
