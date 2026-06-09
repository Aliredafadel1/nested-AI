import asyncio
import logging

from core.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="modules.fraud.tasks.run_fraud_check",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    time_limit=120,
)
def run_fraud_check(listing_id: int) -> None:
    """Compute fraud score for a listing. Triggered after every create_listing."""
    logger.info("run_fraud_check | listing_id=%s", listing_id)

    async def _run():
        import redis.asyncio as aioredis
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from core.config import settings
        from modules.fraud.service import FraudService

        engine = create_async_engine(settings.DATABASE_URL)
        async with AsyncSession(engine) as db:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                svc = FraudService(db, r)
                await svc.compute_fraud_score(listing_id)
            finally:
                await r.aclose()
        await engine.dispose()

    asyncio.run(_run())
    logger.info("run_fraud_check | completed for listing_id=%s", listing_id)
