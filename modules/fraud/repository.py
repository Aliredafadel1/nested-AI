from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.fraud.models import FraudReport


class FraudRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_listing(self, listing_id: int) -> FraudReport | None:
        result = await self._db.execute(
            select(FraudReport).where(FraudReport.listing_id == listing_id)
            .order_by(FraudReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        listing_id: int,
        score: float,
        price_zscore: float | None,
        evidence: dict,
    ) -> FraudReport:
        existing = await self.get_by_listing(listing_id)
        if existing:
            existing.score        = score
            existing.price_zscore = price_zscore
            existing.evidence     = evidence
            await self._db.flush()
            return existing
        report = FraudReport(
            listing_id=listing_id,
            score=score,
            price_zscore=price_zscore,
            evidence=evidence,
        )
        self._db.add(report)
        await self._db.flush()
        return report

    async def get_all_phashes_except(self, listing_id: int) -> list[str]:
        """
        Read-only aggregation across listing_photos for fraud phash dedup.
        This accesses housing-owned data — acceptable only as a read-only
        aggregation that cannot be served by housing.service without leaking
        implementation details of the fraud scoring algorithm.
        """
        result = await self._db.execute(
            text(
                """
                SELECT lp.phash FROM listing_photos lp
                JOIN listings l ON l.id = lp.listing_id
                WHERE lp.listing_id != :lid
                  AND lp.phash IS NOT NULL
                  AND l.status = 'active'
                """
            ),
            {"lid": listing_id},
        )
        return [row[0] for row in result.fetchall()]
