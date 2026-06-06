import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.redis import RedisKeys
from modules.area_intel.repository import AreaIntelRepository
from modules.area_intel.schemas import NeighborhoodOut, CompareOut

AREA_CACHE_TTL = 24 * 3600


class AreaIntelService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._repo = AreaIntelRepository(db)
        self._redis = redis

    async def get_by_name(self, name: str) -> NeighborhoodOut:
        neighbourhood = await self._repo.get_by_name(name)
        if not neighbourhood:
            raise HTTPException(status_code=404, detail=f"Area '{name}' not found.")
        out = self._to_out(neighbourhood)
        await self._cache(neighbourhood.id, out)
        return out

    async def get_by_id(self, neighbourhood_id: int) -> NeighborhoodOut:
        cached = await self._redis.get(RedisKeys.area_cache(neighbourhood_id))
        if cached:
            return NeighborhoodOut(**json.loads(cached))

        neighbourhood = await self._repo.get_by_id(neighbourhood_id)
        if not neighbourhood:
            raise HTTPException(status_code=404, detail=f"Area id={neighbourhood_id} not found.")
        out = self._to_out(neighbourhood)
        await self._cache(neighbourhood_id, out)
        return out

    async def compare(self, area_a: str, area_b: str) -> CompareOut:
        n_a = await self.get_by_name(area_a)
        n_b = await self.get_by_name(area_b)
        return CompareOut(area_a=n_a, area_b=n_b)

    def _to_out(self, n) -> NeighborhoodOut:
        return NeighborhoodOut(
            id=n.id,
            name=n.name,
            name_ar=n.name_ar,
            electricity_hours=float(n.electricity) if n.electricity is not None else None,
            generator_cost=n.generator_cost,
            internet=n.internet,
            transport=n.transport,
            safety=n.safety,
            student_vibe=n.student_vibe,
        )

    async def _cache(self, neighbourhood_id: int, out: NeighborhoodOut) -> None:
        try:
            await self._redis.setex(
                RedisKeys.area_cache(neighbourhood_id),
                AREA_CACHE_TTL,
                json.dumps(out.model_dump()),
            )
        except Exception:
            pass
