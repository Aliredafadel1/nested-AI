from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.contracts.models import Contract


class ContractsRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, user_id: int, minio_key: str) -> Contract:
        contract = Contract(user_id=user_id, minio_key=minio_key, status="pending")
        self._db.add(contract)
        await self._db.commit()
        await self._db.refresh(contract)
        return contract

    async def get_by_id(self, contract_id: int) -> Contract | None:
        result = await self._db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, contract_id: int, status: str) -> None:
        from sqlalchemy import text
        await self._db.execute(
            text("UPDATE contracts SET status = :status WHERE id = :id"),
            {"status": status, "id": contract_id},
        )
        await self._db.commit()

    async def update_analysis(
        self,
        contract_id: int,
        ocr_used: bool,
        analysis: dict,
        status: str = "complete",
    ) -> None:
        from sqlalchemy import text
        await self._db.execute(
            text(
                "UPDATE contracts SET ocr_used = :ocr, analysis = :analysis::jsonb, "
                "status = :status WHERE id = :id"
            ),
            {
                "ocr":      ocr_used,
                "analysis": __import__("json").dumps(analysis),
                "status":   status,
                "id":       contract_id,
            },
        )
        await self._db.commit()
