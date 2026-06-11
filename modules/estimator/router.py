import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from core.security import require_student_role
from modules.estimator.schemas import EstimateOut, EstimateRequest, SimulateOut, SimulateRequest
from modules.estimator.service import EstimatorService

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


@router.post("/simulate", response_model=SimulateOut)
async def simulate(
    req: SimulateRequest,
    current_user=Depends(require_student_role),
    svc: EstimatorService = Depends(_svc),
):
    return await svc.simulate(int(current_user["sub"]), req)
