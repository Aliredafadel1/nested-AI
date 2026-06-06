from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.database import get_db
from core.redis import get_redis_dep
from core.security import require_student_role
from modules.estimator.service import EstimatorService
from modules.estimator.schemas import EstimateRequest, EstimateOut

router = APIRouter(prefix="/estimator", tags=["estimator"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> EstimatorService:
    return EstimatorService(db, redis)


@router.post("/calculate", response_model=EstimateOut)
async def calculate_cost(
    req: EstimateRequest,
    current_user=Depends(require_student_role),
    svc: EstimatorService = Depends(_svc),
):
    return await svc.calculate(int(current_user["sub"]), req)
