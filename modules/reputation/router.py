import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from core.security import require_student_role
from modules.reputation.schemas import LandlordReputationOut, ReviewCreate, ReviewOut
from modules.reputation.service import ReputationService

router = APIRouter(prefix="/reputation", tags=["reputation"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> ReputationService:
    return ReputationService(db, redis)


@router.get("/{landlord_id}", response_model=LandlordReputationOut)
async def get_landlord_reputation(
    landlord_id: int,
    svc: ReputationService = Depends(_svc),
):
    return await svc.get_landlord_reputation(landlord_id)


@router.post("/{landlord_id}/reviews", response_model=ReviewOut, status_code=201)
async def submit_review(
    landlord_id: int,
    req: ReviewCreate,
    current_user: dict = Depends(require_student_role),
    svc: ReputationService = Depends(_svc),
):
    return await svc.submit_review(landlord_id, int(current_user["sub"]), req)
