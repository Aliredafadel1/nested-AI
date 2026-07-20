from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.reputation.models import LandlordReview


class ReputationRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def landlord_exists(self, landlord_id: int) -> bool:
        result = await self._db.execute(
            text("SELECT 1 FROM users WHERE id = :id AND role = 'landlord'"),
            {"id": landlord_id},
        )
        return result.one_or_none() is not None

    async def get_existing_review(
        self, landlord_id: int, reviewer_id: int, listing_id: int | None
    ) -> LandlordReview | None:
        result = await self._db.execute(
            select(LandlordReview).where(
                LandlordReview.landlord_id == landlord_id,
                LandlordReview.reviewer_id == reviewer_id,
                LandlordReview.listing_id == listing_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_review(
        self,
        landlord_id: int,
        reviewer_id: int,
        listing_id: int | None,
        maintenance: int | None,
        responsiveness: int | None,
        honesty: int | None,
        hidden_fees: int | None,
    ) -> LandlordReview:
        review = LandlordReview(
            landlord_id=landlord_id,
            reviewer_id=reviewer_id,
            listing_id=listing_id,
            maintenance=maintenance,
            responsiveness=responsiveness,
            honesty=honesty,
            hidden_fees=hidden_fees,
        )
        self._db.add(review)
        await self._db.flush()
        return review

    async def get_reviews_for_landlord(self, landlord_id: int) -> list[LandlordReview]:
        result = await self._db.execute(
            select(LandlordReview)
            .where(LandlordReview.landlord_id == landlord_id)
            .order_by(LandlordReview.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_averages(self, landlord_id: int) -> dict:
        result = await self._db.execute(
            select(
                func.count(LandlordReview.id),
                func.avg(LandlordReview.maintenance),
                func.avg(LandlordReview.responsiveness),
                func.avg(LandlordReview.honesty),
                func.avg(LandlordReview.hidden_fees),
            ).where(LandlordReview.landlord_id == landlord_id)
        )
        row = result.one()
        return {
            "review_count":       row[0],
            "avg_maintenance":    float(row[1]) if row[1] is not None else None,
            "avg_responsiveness": float(row[2]) if row[2] is not None else None,
            "avg_honesty":        float(row[3]) if row[3] is not None else None,
            "avg_hidden_fees":    float(row[4]) if row[4] is not None else None,
        }
