from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from modules.reputation.repository import ReputationRepository
from modules.reputation.schemas import LandlordReputationOut, ReviewCreate, ReviewOut


class ReputationService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self._repo = ReputationRepository(db)

    async def submit_review(self, landlord_id: int, reviewer_id: int, req: ReviewCreate) -> ReviewOut:
        if landlord_id == reviewer_id:
            raise HTTPException(status_code=400, detail="You cannot review yourself.")
        if not await self._repo.landlord_exists(landlord_id):
            raise HTTPException(status_code=404, detail="Landlord not found.")

        existing = await self._repo.get_existing_review(landlord_id, reviewer_id, req.listing_id)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="You have already reviewed this landlord for this listing.",
            )

        if all(v is None for v in (req.maintenance, req.responsiveness, req.honesty, req.hidden_fees)):
            raise HTTPException(status_code=422, detail="At least one rating dimension is required.")

        review = await self._repo.create_review(
            landlord_id=landlord_id,
            reviewer_id=reviewer_id,
            listing_id=req.listing_id,
            maintenance=req.maintenance,
            responsiveness=req.responsiveness,
            honesty=req.honesty,
            hidden_fees=req.hidden_fees,
        )
        return ReviewOut.model_validate(review)

    async def get_landlord_reputation(self, landlord_id: int) -> LandlordReputationOut:
        if not await self._repo.landlord_exists(landlord_id):
            raise HTTPException(status_code=404, detail="Landlord not found.")

        averages = await self._repo.get_averages(landlord_id)
        reviews = await self._repo.get_reviews_for_landlord(landlord_id)

        dims = [
            averages["avg_maintenance"],
            averages["avg_responsiveness"],
            averages["avg_honesty"],
            averages["avg_hidden_fees"],
        ]
        present = [d for d in dims if d is not None]
        avg_overall = round(sum(present) / len(present), 2) if present else None

        return LandlordReputationOut(
            landlord_id=landlord_id,
            review_count=averages["review_count"],
            avg_maintenance=round(averages["avg_maintenance"], 2) if averages["avg_maintenance"] is not None else None,
            avg_responsiveness=round(averages["avg_responsiveness"], 2) if averages["avg_responsiveness"] is not None else None,
            avg_honesty=round(averages["avg_honesty"], 2) if averages["avg_honesty"] is not None else None,
            avg_hidden_fees=round(averages["avg_hidden_fees"], 2) if averages["avg_hidden_fees"] is not None else None,
            avg_overall=avg_overall,
            reviews=[ReviewOut.model_validate(r) for r in reviews],
        )
