"""3-tier LLM router — Claude Sonnet (powerful) + Groq (cheap) with Redis stale-cache fallback."""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Iterator

import anthropic as _anthropic_sdk
from openai import OpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier → task mapping
# ---------------------------------------------------------------------------

TASK_TIERS: dict[str, str] = {
    # free tier (BGE-M3 local)
    "embed_listing":              "free",
    "embed_profile":              "free",
    "embed_query":                "free",
    "embed_rag_chunk":            "free",
    # cheap tier (Groq Llama 3.1 8B — fast, free)
    "parse_intent":               "cheap",
    "explain_compatibility":      "cheap",
    "summarize_area":             "cheap",
    "classify_fraud_text":        "cheap",
    "summarize_session":          "cheap",
    # arabic tier (Groq Llama 3.3 70B — Lebanese dialect + 3arabizi aware)
    "agent_compare_explain_ar":   "arabic",
    "analyze_contract_ar":        "arabic",
    # powerful tier (Claude Sonnet — deep reasoning, English)
    "agent_compare_explain":      "powerful",
    "analyze_contract":           "powerful",
    "ocr_analyze_contract":       "powerful",
    "validate_coherence":         "powerful",
}

TIER_MODELS: dict[str, str] = {
    "powerful": "claude-sonnet-4-6",
    "arabic":   "claude-sonnet-4-6",   # Claude handles Lebanese dialect reliably
    "cheap":    "llama-3.1-8b-instant",
    "free":     "bge-m3",
}

# System prompt injected for every Arabic-tier call
_ARABIC_SYSTEM = """You are a housing assistant for Lebanese students in Beirut.

LANGUAGE RULES (STRICT):
1. ALWAYS reply in Lebanese colloquial Arabic — يا حبيبي، شو رأيك، منيح، كتير، هلق، يلا، بس، مش.
2. NEVER use Egyptian Arabic (دي، مفيش، إزيك — FORBIDDEN).
3. NEVER use formal فصحى.
4. NEVER output Chinese, Korean, Japanese, or any non-Arabic/non-Latin characters.
5. If the student writes 3arabizi or mixes French/English, reply in Arabic script.

FRAUD SCORE RULES (CRITICAL — read carefully):
- fraud_score is between 0.0 and 1.0.
- 0.0 = completely safe, 1.0 = definite scam.
- A listing with fraud_score = 0.97 is 97% likely a SCAM — NEVER recommend it.
- Only recommend listings with fraud_score BELOW 0.3.
- If all listings have high fraud scores (> 0.5), warn the student strongly.
- Example: fraud_score 0.05 = safe ✓, fraud_score 0.97 = scam ✗

CONTENT RULES:
- Always mention electricity hours (ساعات الكهرباء), generator (مولّد), water (مي), internet (إنترنت).
- Be like a trusted local friend — warm, direct, honest about risks.
- If something looks like a scam (too cheap, same listing repeated, no deposit) — say it clearly."""

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ---------------------------------------------------------------------------
# Clients (lazy-initialised)
# ---------------------------------------------------------------------------

def _anthropic_client() -> _anthropic_sdk.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OSError("ANTHROPIC_API_KEY is not set")
    return _anthropic_sdk.Anthropic(api_key=api_key)


def _groq_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise OSError("GROQ_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)


def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OSError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Per-tier call helpers
# ---------------------------------------------------------------------------

def _call_anthropic(model: str, prompt: str, **kwargs) -> str:
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


def _call_groq(model: str, prompt: str, **kwargs) -> str:
    max_tokens = kwargs.get("max_tokens", 1024)
    system = kwargs.get("system", "You are a helpful assistant.")
    client = _groq_client()
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
        from core.redis import RedisKeys, get_sync_redis
        r = get_sync_redis()
        try:
            return r.get(RedisKeys.llm_cache(task, _prompt_hash(task, prompt)))
        finally:
            r.close()
    except Exception:
        return None


def _set_llm_cache(task: str, prompt: str, result: str, ttl: int = 6 * 3600) -> None:
    try:
        from core.redis import RedisKeys, get_sync_redis
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
    Route task to the appropriate model tier with fallback chain.

    Fallback chain (powerful tier):
      Claude Sonnet (claude-sonnet-4-6)
      → Groq cheap (llama-3.1-8b-instant)
      → stale Redis cache
      → graceful user-facing message

    Fallback chain (cheap tier):
      Groq cheap (llama-3.1-8b-instant)
      → stale Redis cache
      → graceful user-facing message

    Returns str for powerful/cheap tiers, list[float] for free (embeddings).
    """
    tier = get_tier(task)
    model = TIER_MODELS[tier]
    logger.info("call_llm | task=%s tier=%s model=%s", task, tier, model)

    if tier == "free":
        return _call_free(prompt, **kwargs)

    # Arabic tier: inject Lebanese system prompt if caller didn't provide one
    if tier == "arabic" and "system" not in kwargs:
        kwargs = {**kwargs, "system": _ARABIC_SYSTEM}

    # Attempt primary model for tier
    try:
        if tier in ("powerful", "arabic"):
            result = _call_anthropic(model, prompt, **kwargs)
        else:
            result = _call_groq(model, prompt, **kwargs)
        _set_llm_cache(task, prompt, result)
        return result
    except Exception as e:
        logger.warning("call_llm | %s tier (%s) failed: %s", tier, model, e)

    # Fallback 1: Groq cheap (if primary was powerful/arabic failed)
    if tier in ("powerful", "arabic"):
        cheap_model = TIER_MODELS["cheap"]
        try:
            result = _call_groq(cheap_model, prompt, **kwargs)
            _set_llm_cache(task, prompt, result)
            logger.warning("call_llm | task=%s served by Groq cheap fallback (%s)", task, cheap_model)
            return result
        except Exception as e:
            logger.warning("call_llm | Groq cheap fallback (%s) failed: %s", cheap_model, e)

    # Fallback 2: stale Redis cache
    cached = _get_llm_cache(task, prompt)
    if cached:
        logger.warning("call_llm | task=%s served from stale Redis cache", task)
        return cached

    # Final: graceful degradation message
    logger.error("call_llm | task=%s all providers failed — returning graceful message", task)
    ar_tasks = {"agent_compare_explain_ar", "analyze_contract_ar"}
    if task in ar_tasks:
        return "الخدمة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى."
    return "Service temporarily unavailable. Please try again shortly."


# ---------------------------------------------------------------------------
# Streaming variant — powerful tier only (Claude Sonnet)
# ---------------------------------------------------------------------------

def stream_llm(task: str, prompt: str, **kwargs) -> Iterator[str]:
    """
    Stream tokens for the given task.
    Supports powerful (Claude Sonnet) and arabic (Groq Llama 3.3 70B) tiers.

    Yields text chunks as they arrive. On failure, falls back to call_llm.
    """
    tier = get_tier(task)
    if tier not in ("powerful", "arabic"):
        raise ValueError(
            f"stream_llm only supports powerful/arabic-tier tasks. "
            f"Task '{task}' is tier '{tier}'."
        )

    if tier == "arabic":
        # Stream from Claude Sonnet with Lebanese system prompt
        model = TIER_MODELS["arabic"]
        max_tokens = kwargs.get("max_tokens", 2048)
        system = kwargs.get("system", _ARABIC_SYSTEM)
        try:
            client = _anthropic_client()
            full_text: list[str] = []
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        full_text.append(text)
                        yield text
            _set_llm_cache(task, prompt, "".join(full_text))
            return
        except Exception as e:
            logger.warning("stream_llm | Claude Arabic streaming failed: %s — falling back", e)
            result = call_llm(task, prompt, **kwargs)
            if isinstance(result, str):
                yield result
            return

    # Powerful tier: stream from Claude Sonnet
    model = TIER_MODELS["powerful"]
    max_tokens = kwargs.get("max_tokens", 2048)
    system = kwargs.get("system", "You are a helpful assistant.")

    try:
        client = _anthropic_client()
        full_text: list[str] = []
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                if text:
                    full_text.append(text)
                    yield text
        _set_llm_cache(task, prompt, "".join(full_text))
    except Exception as e:
        logger.warning("stream_llm | Claude Sonnet streaming failed: %s — falling back to call_llm", e)
        result = call_llm(task, prompt, **kwargs)
        if isinstance(result, str):
            yield result


# ---------------------------------------------------------------------------
# Audio transcription — Whisper via Groq (free)
# ---------------------------------------------------------------------------

def ocr_pdf_page(img_b64: str) -> str:
    """OCR a single PDF page image via Groq vision. Routed here to satisfy no-SDK-outside-llm_router."""
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this lease contract page verbatim. Return only the text, no commentary."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("ocr_pdf_page | Groq vision failed: %s", e)
        return ""


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio using Groq Whisper (whisper-large-v3, free tier).
    Lives in llm_router.py to satisfy the no-SDK-calls-outside-llm_router invariant.
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise OSError("GROQ_API_KEY is not set — audio transcription unavailable")
    try:
        client = OpenAI(api_key=groq_key, base_url=_GROQ_BASE_URL)
        response = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename, file_bytes),
        )
        return response.text
    except Exception as e:
        logger.error("transcribe_audio | Groq Whisper failed: %s", e)
        raise
