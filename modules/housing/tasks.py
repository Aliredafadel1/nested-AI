"""Housing module Celery tasks — listing embedding pipeline."""
import logging

from core.celery_config import celery_app
from core.database import get_sync_db
from core.redis import get_sync_redis, RedisKeys

logger = logging.getLogger(__name__)

LOCK_TTL = 30  # seconds


@celery_app.task(
    name="modules.housing.tasks.embed_listing",
    bind=True,
    queue="nestai:low",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=90,
)
def embed_listing(self, listing_id: int) -> None:
    redis = get_sync_redis()
    lock_key = RedisKeys.embed_lock(listing_id)

    acquired = redis.set(lock_key, "1", nx=True, ex=LOCK_TTL)
    if not acquired:
        logger.info("embed_listing: lock held for listing %s, skipping", listing_id)
        redis.close()
        return

    try:
        from core.embeddings import embed_text
        from sqlalchemy import select, text
        from modules.housing.models import Listing, Neighborhood

        # Step 1: read listing data — close session before slow inference
        embed_input = None
        with get_sync_db() as db:
            row = db.execute(
                select(
                    Listing.id,
                    Listing.title,
                    Listing.description,
                    Listing.amenities,
                    Neighborhood.name.label("neighbourhood_name"),
                )
                .join(Neighborhood, Listing.neighbourhood_id == Neighborhood.id)
                .where(Listing.id == listing_id)
            ).one_or_none()

            if row is None:
                logger.info("embed_listing: listing %s not found (deleted?), skipping", listing_id)
                return

            amenity_keys = " ".join(k for k, v in (row.amenities or {}).items() if v)
            embed_input = (
                f"{row.title}. {row.description or ''}. "
                f"Neighbourhood: {row.neighbourhood_name}. "
                f"Amenities: {amenity_keys}"
            ).strip()

        # Step 2: embed — no DB connection held during CPU inference
        vector = embed_text(embed_input)

        # Step 3: write result in a fresh session
        with get_sync_db() as db:
            db.execute(
                text("UPDATE listings SET embedding = :vec WHERE id = :id"),
                {"vec": str(vector), "id": listing_id},
            )
        logger.info("embed_listing: listing %s embedded (%d-dim)", listing_id, len(vector))

    finally:
        redis.delete(lock_key)
        redis.close()


@celery_app.task(
    name="modules.housing.tasks.batch_embed_seed_data",
    queue="nestai:low",
)
def batch_embed_seed_data() -> None:
    from sqlalchemy import select, text
    from modules.housing.models import Listing

    with get_sync_db() as db:
        rows = db.execute(
            select(Listing.id).where(Listing.embedding.is_(None))
        ).scalars().all()

    logger.info("batch_embed_seed_data: queuing %d listings", len(rows))
    for listing_id in rows:
        embed_listing.delay(listing_id)
