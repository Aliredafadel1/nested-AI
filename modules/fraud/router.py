import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from modules.fraud.schemas import FraudReportOut
from modules.fraud.service import FraudService

router = APIRouter(prefix="/fraud", tags=["fraud"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> FraudService:
    return FraudService(db, redis)


@router.get("/{listing_id}", response_model=FraudReportOut)
async def get_fraud_report(
    listing_id: int,
    svc: FraudService = Depends(_svc),
):
    return await svc.get_report(listing_id)
