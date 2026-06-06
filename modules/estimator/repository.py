from sqlalchemy.ext.asyncio import AsyncSession

from modules.estimator.models import CostEstimate


class EstimatorRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(
        self,
        user_id: int,
        rent: int,
        generator: int,
        water: int,
        internet: int,
        transport: int,
        total_monthly: int,
        university_id: int | None = None,
    ) -> CostEstimate:
        estimate = CostEstimate(
            user_id=user_id,
            rent=rent,
            generator=generator,
            water=water,
            internet=internet,
            transport=transport,
            total_monthly=total_monthly,
            university_id=university_id,
        )
        self._db.add(estimate)
        await self._db.commit()
        await self._db.refresh(estimate)
        return estimate
