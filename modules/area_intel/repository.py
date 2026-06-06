from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.area_intel.models import Neighborhood


class AreaIntelRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_name(self, name: str) -> Neighborhood | None:
        result = await self._db.execute(
            select(Neighborhood).where(Neighborhood.name.ilike(name))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, neighbourhood_id: int) -> Neighborhood | None:
        result = await self._db.execute(
            select(Neighborhood).where(Neighborhood.id == neighbourhood_id)
        )
        return result.scalar_one_or_none()
