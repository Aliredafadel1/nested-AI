from __future__ import annotations

import io
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.storage import Bucket, get_minio_client
from modules.contracts.repository import ContractsRepository
from modules.contracts.schemas import ContractAnalysis, ContractCreateOut, ContractOut

MAX_CONTRACT_SIZE = 10 * 1024 * 1024  # 10 MB
PDF_MAGIC = b"%PDF"


class ContractsService:
    def __init__(self, db: AsyncSession):
        self._db   = db
        self._repo = ContractsRepository(db)

    async def upload_and_queue(self, user_id: int, file: UploadFile) -> ContractCreateOut:
        # Read entire file into memory for validation
        file_bytes = await file.read()

        if len(file_bytes) > MAX_CONTRACT_SIZE:
            raise HTTPException(status_code=400, detail="File exceeds 10 MB limit.")

        # Magic bytes check — must be PDF
        if not file_bytes[:4] == PDF_MAGIC:
            raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

        # Password protection check — must complete within seconds (no hang)
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            is_locked = doc.needs_pass
            doc.close()
            if is_locked:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs cannot be analyzed.",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # PyMuPDF unavailable — continue without check

        # Upload bytes directly to MinIO (bypasses UploadFile re-read issues)
        minio_key = f"contracts/{user_id}/{uuid.uuid4()}.pdf"
        client = get_minio_client()
        try:
            client.put_object(
                bucket_name=Bucket.CONTRACTS.value,
                object_name=minio_key,
                data=io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type="application/pdf",
                metadata={"owner_id": str(user_id)},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage error: {e}") from e

        contract = await self._repo.create(user_id, minio_key)

        from modules.contracts.tasks import analyze_contract_async
        analyze_contract_async.delay(contract.id)

        return ContractCreateOut(contract_id=contract.id, status="pending")

    async def get_contract(self, user_id: int, contract_id: int) -> ContractOut:
        contract = await self._repo.get_by_id(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found.")
        if contract.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your contract.")

        analysis = None
        if contract.analysis and isinstance(contract.analysis, dict):
            analysis = ContractAnalysis(**contract.analysis)

        return ContractOut(
            id=contract.id,
            ocr_used=bool(contract.ocr_used),
            status=contract.status,
            analysis=analysis,
            created_at=contract.created_at,
        )
