from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.llm_router import call_llm
from core.redis import RedisKeys
from core.features import amenity_vs_price_anomaly, urgency_word_count, external_contact_flag
from modules.fraud.repository import FraudRepository
from modules.fraud.schemas import FraudEvidence, FraudReportOut

logger = logging.getLogger(__name__)

FRAUD_CACHE_TTL = 12 * 3600  # 12 hours


def _hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two hex phash strings."""
    if len(a) != len(b):
        return 999
    a_bits = bin(int(a, 16))[2:].zfill(len(a) * 4)
    b_bits = bin(int(b, 16))[2:].zfill(len(b) * 4)
    return sum(x != y for x, y in zip(a_bits, b_bits))


class FraudService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._db    = db
        self._repo  = FraudRepository(db)
        self._redis = redis

    async def get_report(self, listing_id: int) -> FraudReportOut:
        cached = await self._redis.get(RedisKeys.fraud_cache(listing_id))
        if cached:
            data = json.loads(cached)
            return FraudReportOut(**data)

        report = await self._repo.get_by_listing(listing_id)
        if report:
            out = FraudReportOut(
                listing_id=report.listing_id,
                score=float(report.score),
                price_zscore=float(report.price_zscore) if report.price_zscore else None,
                evidence=FraudEvidence(**(report.evidence or {})),
                computed_at=report.updated_at or report.created_at,
            )
            await self._cache(listing_id, out)
            return out

        return FraudReportOut(
            listing_id=listing_id,
            score=0.0,
            price_zscore=None,
            evidence=FraudEvidence(),
            computed_at=datetime.now(timezone.utc),
        )

    async def compute_fraud_score(self, listing_id: int) -> None:
        from modules.housing.service import HousingService
        housing = HousingService(self._db)

        listing = await housing.get_listing(listing_id)
        evidence = {
            "price_flags":  [],
            "phone_flags":  [],
            "photo_flags":  [],
            "ip_flags":     [],
            "content_flags":[],
            "text_flags":   [],
        }
        price_component   = 0.0
        phone_component   = 0.0
        photo_component   = 0.0
        ip_component      = 0.0
        content_component = 0.0
        amenity_component = 0.0
        price_zscore      = None

        # ── Signal 1: Price z-score (35%) ────────────────────────────────────
        try:
            stats = await housing.get_neighbourhood_stats(listing.neighbourhood_id)
            median = stats["median"] or listing.price
            stddev = stats["stddev"] or 1.0
            z = (listing.price - median) / stddev
            price_zscore = z
            if z < -2.0:
                evidence["price_flags"].append("price_suspicious_low")
                price_component = min(abs(z) / 3.0, 1.0)
            elif z > 3.0:
                evidence["price_flags"].append("price_suspicious_high")
                price_component = min(z / 5.0, 1.0)
        except Exception as e:
            logger.warning("fraud.compute | price z-score failed: %s", e)

        # ── Signal 2: Landlord listing count (10%) ───────────────────────────
        try:
            listing_count = await housing.get_landlord_listing_count(listing.landlord_id)
            if listing_count >= 3:
                evidence["phone_flags"].append("multiple_listings_same_landlord")
                phone_component = min((listing_count - 1) / 5.0, 1.0)
        except Exception as e:
            logger.warning("fraud.compute | phone dedup failed: %s", e)

        # ── Signal 3: Photo phash dedup (15%) ───────────────────────────────
        try:
            listing_phashes   = await housing.get_listing_photo_phashes(listing_id)
            all_other_phashes = await self._repo.get_all_phashes_except(listing_id)
            for phash in listing_phashes:
                for other in all_other_phashes:
                    if _hamming_distance(phash, other) <= 10:
                        evidence["photo_flags"].append("duplicate_photo_detected")
                        photo_component = 1.0
                        break
                if photo_component > 0:
                    break
        except Exception as e:
            logger.warning("fraud.compute | photo phash failed: %s", e)

        # ── Signal 4: IP velocity — same IP, many listings in 24h (25%) ──────
        try:
            if listing.ip_address:
                ip_count = await housing.get_ip_listing_count(listing.ip_address, hours=24)
                if ip_count >= 3:
                    evidence["ip_flags"].append(f"ip_velocity_{ip_count}_listings_24h")
                    ip_component = min((ip_count - 2) / 5.0, 1.0)
        except Exception as e:
            logger.warning("fraud.compute | IP velocity failed: %s", e)

        # ── Signal 5: Description similarity — copy-paste detection (15%) ────
        # Cosine distance < 0.05 means >95% similar — almost certainly copy-pasted.
        try:
            similar = await housing.get_similar_listing_embeddings(listing_id, limit=3)
            if similar and similar[0]["distance"] < 0.05:
                evidence["content_flags"].append(
                    f"description_near_duplicate_of_listing_{similar[0]['listing_id']}"
                )
                content_component = 1.0
            elif similar and similar[0]["distance"] < 0.12:
                evidence["content_flags"].append("description_highly_similar_to_existing_listing")
                content_component = 0.5
        except Exception as e:
            logger.warning("fraud.compute | description similarity failed: %s", e)

        # ── Signal 6b: Amenity-vs-price anomaly (10%) ────────────────────────
        # High amenity score at impossibly low price is a strong fraud signal.
        # Replaces raw price check — catches "$99 all-inclusive" type scams.
        try:
            amenity_component = amenity_vs_price_anomaly(listing.amenities, listing.price)
            if amenity_component > 0.6:
                evidence["price_flags"].append("amenity_vs_price_anomaly")

            # Also flag urgency language and off-platform contact
            urgency = urgency_word_count(listing.title, listing.description)
            if urgency >= 2:
                evidence["text_flags"].append(f"urgency_word_count_{urgency}")
            if external_contact_flag(listing.title, listing.description):
                evidence["text_flags"].append("external_contact_detected")
        except Exception as e:
            logger.warning("fraud.compute | amenity anomaly failed: %s", e)

        # ── Signal 7: LLM text flags (qualitative — no score weight) ─────────
        try:
            text_input = f"{listing.title}. {listing.description or ''}"
            flags_raw = call_llm(
                "classify_fraud_text",
                f"Identify fraud indicators in this rental listing. "
                f"Return a JSON list of short flag strings (max 5). Text: {text_input}",
                max_tokens=200,
            )
            import json as json_mod
            try:
                flags = json_mod.loads(flags_raw)
                if isinstance(flags, list):
                    evidence["text_flags"] = [str(f) for f in flags[:5]]
            except Exception:
                pass
        except Exception as e:
            logger.warning("fraud.compute | text classification failed: %s", e)

        # ── Final score — 6 numeric signals ──────────────────────────────────
        # price 30% | ip_velocity 20% | amenity_anomaly 20% | photo 12% | content 12% | phone 6%
        score = (
            0.30 * price_component
            + 0.20 * ip_component
            + 0.20 * amenity_component
            + 0.12 * photo_component
            + 0.12 * content_component
            + 0.06 * phone_component
        )
        score = round(min(score, 1.0), 3)
        logger.info(
            "fraud.compute | listing=%s score=%.3f "
            "(price=%.2f ip=%.2f amenity=%.2f photo=%.2f content=%.2f phone=%.2f)",
            listing_id, score,
            price_component, ip_component, amenity_component,
            photo_component, content_component, phone_component,
        )

        report = await self._repo.upsert(listing_id, score, price_zscore, evidence)
        await self._db.commit()

        # Update listings.fraud_score
        from sqlalchemy import text
        await self._db.execute(
            text("UPDATE listings SET fraud_score = :score WHERE id = :id"),
            {"score": score, "id": listing_id},
        )
        await self._db.commit()

        out = FraudReportOut(
            listing_id=listing_id,
            score=score,
            price_zscore=price_zscore,
            evidence=FraudEvidence(**evidence),
            computed_at=report.updated_at or report.created_at,
        )
        await self._cache(listing_id, out)

    async def _cache(self, listing_id: int, out: FraudReportOut) -> None:
        try:
            data = out.model_dump()
            data["computed_at"] = data["computed_at"].isoformat()
            await self._redis.setex(
                RedisKeys.fraud_cache(listing_id),
                FRAUD_CACHE_TTL,
                json.dumps(data),
            )
        except Exception:
            pass
