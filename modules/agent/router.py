import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from core.security import require_student_role
from modules.agent.schemas import ChatRequest, FeedbackRequest, FeedbackResponse, TranscribeResponse
from modules.agent.service import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> AgentService:
    return AgentService(db, redis)


@router.post("/chat")
async def agent_chat(
    req: ChatRequest,
    current_user=Depends(require_student_role),
    svc: AgentService = Depends(_svc),
):
    user_id = int(current_user["sub"])
    await svc.check_chat_rate(user_id)
    return StreamingResponse(
        svc.chat(user_id, req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user=Depends(require_student_role),
    svc: AgentService = Depends(_svc),
):
    user_id = int(current_user["sub"])
    await svc.check_transcribe_rate(user_id)
    text = await svc.transcribe(user_id, file)
    return TranscribeResponse(text=text)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    current_user=Depends(require_student_role),
    svc: AgentService = Depends(_svc),
):
    return await svc.save_feedback(int(current_user["sub"]), req)
