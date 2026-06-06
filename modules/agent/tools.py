"""9 MCP tool functions for the NestAI LangGraph agent.

Each function is a plain Python callable (no Celery, no async).
They are invoked synchronously from graph node closures that hold db/redis refs.
Cross-module data access goes through service.py only — never repository.py.
"""
from __future__ import annotations

import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


# ── Tool 1: search_listings ────────────────────────────────────────────────────

async def search_listings(db, intent: dict) -> list[dict]:
    """Semantic search on listings using BGE-M3 embedding of the intent query."""
    from core.embeddings import embed_text
    from modules.housing.service import HousingService

    query_text = _intent_to_query_text(intent)
    try:
        embedding = embed_text(query_text)
    except NotImplementedError:
        logger.warning("search_listings | BGE-M3 not loaded — returning empty")
        return []

    filters = {}
    if intent.get("min_price"):
        filters["min_price"] = intent["min_price"]
    if intent.get("max_price"):
        filters["max_price"] = intent["max_price"]
    if intent.get("neighbourhood_id"):
        filters["neighbourhood_id"] = intent["neighbourhood_id"]

    svc = HousingService(db)
    listings = await svc.semantic_search(embedding, filters, limit=10)
    return [_listing_to_dict(l) for l in listings]


# ── Tool 2: calculate_commute ──────────────────────────────────────────────────

async def calculate_commute(
    listing_lat: float, listing_lng: float,
    uni_lat: float, uni_lng: float,
) -> dict:
    """OSRM commute calculation. Returns null on any error."""
    try:
        url = (
            f"{settings.OSRM_URL}/route/v1/driving/"
            f"{listing_lng},{listing_lat};"
            f"{uni_lng},{uni_lat}"
            f"?overview=false"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            data = resp.json()
            minutes = int(data["routes"][0]["duration"] / 60)
            return {"commute_minutes": minutes}
    except Exception as e:
        logger.warning("calculate_commute | OSRM unavailable: %s", e)
        return {"commute_minutes": None, "note": "Commute data temporarily unavailable"}


# ── Tool 3: get_area_scores ────────────────────────────────────────────────────

async def get_area_scores(db, redis, area_name: str) -> dict:
    from modules.area_intel.service import AreaIntelService
    try:
        svc = AreaIntelService(db, redis)
        out = await svc.get_by_name(area_name)
        return out.model_dump()
    except Exception as e:
        logger.warning("get_area_scores | failed for '%s': %s", area_name, e)
        return {}


# ── Tool 4: check_fraud ────────────────────────────────────────────────────────

async def check_fraud(db, redis, listing_id: int) -> dict:
    from modules.fraud.service import FraudService
    try:
        svc = FraudService(db, redis)
        report = await svc.get_report(listing_id)
        return {"score": report.score, "listing_id": listing_id}
    except Exception as e:
        logger.warning("check_fraud | failed for listing %s: %s", listing_id, e)
        return {"score": 0.0, "listing_id": listing_id}


# ── Tool 5: get_roommate_matches ───────────────────────────────────────────────

async def get_roommate_matches(db, user_id: int) -> list[dict]:
    from modules.roommate.service import RoommateService
    try:
        svc = RoommateService(db)
        matches = await svc.get_matches(user_id)
        return [m.model_dump() for m in matches]
    except Exception as e:
        logger.warning("get_roommate_matches | failed for user %s: %s", user_id, e)
        return []


# ── Tool 6: estimate_cost ──────────────────────────────────────────────────────

async def estimate_cost(db, redis, rent: int, neighbourhood_id: int, university_id: int | None) -> dict:
    from modules.estimator.service import EstimatorService
    from modules.estimator.schemas import EstimateRequest
    try:
        svc = EstimatorService(db, redis)
        req = EstimateRequest(rent=rent, neighbourhood_id=neighbourhood_id, university_id=university_id)
        out = await svc.calculate(user_id=0, req=req)
        return out.model_dump()
    except Exception as e:
        logger.warning("estimate_cost | failed: %s", e)
        return {}


# ── Tool 7: compare_areas ─────────────────────────────────────────────────────

async def compare_areas(db, redis, area_a: str, area_b: str) -> dict:
    from modules.area_intel.service import AreaIntelService
    try:
        svc = AreaIntelService(db, redis)
        out = await svc.compare(area_a, area_b)
        return out.model_dump()
    except Exception as e:
        logger.warning("compare_areas | failed: %s", e)
        return {}


# ── Tool 8: transcribe_audio ───────────────────────────────────────────────────

def transcribe_audio_tool(file_bytes: bytes, filename: str) -> str:
    from core.llm_router import transcribe_audio
    return transcribe_audio(file_bytes, filename)


# ── Tool 9: survival_search ────────────────────────────────────────────────────

async def survival_search(db, query_text: str) -> list[dict]:
    """Semantic search over rag_chunks (source_type='housing_faq') for Lebanon survival info."""
    from core.embeddings import embed_text
    from modules.agent.repository import AgentRepository

    try:
        embedding = embed_text(query_text)
    except NotImplementedError:
        logger.warning("survival_search | BGE-M3 not loaded")
        return []

    repo = AgentRepository(db)
    return await repo.search_rag_chunks(embedding, limit=3)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _intent_to_query_text(intent: dict) -> str:
    parts = []
    if intent.get("area"):
        parts.append(f"apartment in {intent['area']}")
    if intent.get("bedrooms"):
        parts.append(f"{intent['bedrooms']} bedrooms")
    if intent.get("max_price"):
        parts.append(f"under {intent['max_price']} USD")
    if intent.get("must_haves"):
        parts.append(" ".join(intent["must_haves"]))
    return " ".join(parts) if parts else "student apartment Beirut"


def _listing_to_dict(listing) -> dict:
    return {
        "id":              listing.id,
        "title":           listing.title,
        "price":           listing.price,
        "bedrooms":        listing.bedrooms,
        "neighbourhood_id": listing.neighbourhood_id,
        "description":     listing.description or "",
        "lat":             float(listing.lat) if listing.lat else None,
        "lng":             float(listing.lng) if listing.lng else None,
        "fraud_score":     float(listing.fraud_score) if listing.fraud_score else 0.0,
        "status":          listing.status,
    }
