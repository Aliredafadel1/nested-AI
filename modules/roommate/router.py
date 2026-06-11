from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_student_role
from modules.roommate.schemas import MatchOut, MessageCreate, MessageOut, RequestCreate, RequestOut, RequestRespond
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


@router.get("/requests", response_model=list[RequestOut])
async def list_my_requests(
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.get_my_requests(int(current_user["sub"]))


@router.patch("/requests/{request_id}", response_model=RequestOut)
async def respond_to_request(
    request_id: int,
    body: RequestRespond,
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.respond_to_request(request_id, int(current_user["sub"]), body.accept)


@router.post("/requests/{request_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    request_id: int,
    body: MessageCreate,
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.send_message(request_id, int(current_user["sub"]), body.content)


@router.get("/requests/{request_id}/messages", response_model=list[MessageOut])
async def get_thread(
    request_id: int,
    current_user: dict = Depends(require_student_role),
    svc: RoommateService = Depends(_svc),
):
    return await svc.get_thread(request_id, int(current_user["sub"]))
