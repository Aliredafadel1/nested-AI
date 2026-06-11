import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from core.security import get_current_user, require_student_role
from modules.contracts.schemas import ContractCreateOut, ContractOut
from modules.contracts.service import ContractsService

router = APIRouter(prefix="/contracts", tags=["contracts"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> ContractsService:
    return ContractsService(db, redis)


@router.post("/analyze", response_model=ContractCreateOut, status_code=202)
async def analyze_contract(
    file: UploadFile = File(...),
    current_user=Depends(require_student_role),
    svc: ContractsService = Depends(_svc),
):
    return await svc.upload_and_queue(int(current_user["sub"]), file)


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(
    contract_id: int,
    current_user=Depends(get_current_user),
    svc: ContractsService = Depends(_svc),
):
    return await svc.get_contract(int(current_user["sub"]), contract_id)
