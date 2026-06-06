from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.database import get_db
from core.redis import get_redis_dep
from modules.area_intel.service import AreaIntelService
from modules.area_intel.schemas import NeighborhoodOut, CompareRequest, CompareOut

router = APIRouter(prefix="/areas", tags=["area_intel"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> AreaIntelService:
    return AreaIntelService(db, redis)


@router.get("/{name}", response_model=NeighborhoodOut)
async def get_area(name: str, svc: AreaIntelService = Depends(_svc)):
    return await svc.get_by_name(name)


@router.post("/compare", response_model=CompareOut)
async def compare_areas(req: CompareRequest, svc: AreaIntelService = Depends(_svc)):
    return await svc.compare(req.area_a, req.area_b)
