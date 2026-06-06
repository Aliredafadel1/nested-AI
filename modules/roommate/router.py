from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_student_role
from modules.roommate.schemas import MatchOut, RequestCreate, RequestOut
from modules.roommate.service import RoommateService

router = APIRouter(prefix="/roommate", tags=["roommate"])


def _svc(db: AsyncSession = Depends(get_db)) -> RoommateService:
    return RoommateService(db)


@router.get("/matches", response_model=list[MatchOut])
async def get_matches(
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.get_matches(int(current_user["sub"]))


@router.post("/requests", response_model=RequestOut, status_code=201)
async def send_request(
    body: RequestCreate,
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.send_request(int(current_user["sub"]), body.to_user_id)
