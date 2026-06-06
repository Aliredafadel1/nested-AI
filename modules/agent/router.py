from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.database import get_db
from core.redis import get_redis_dep
from core.security import require_student_role
from modules.agent.repository import AgentRepository
from modules.agent.service import AgentService
from modules.agent.schemas import ChatRequest, TranscribeResponse, FeedbackRequest, FeedbackResponse

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
    return StreamingResponse(
        svc.chat(int(current_user["sub"]), req),
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
    text = await svc.transcribe(file)
    return TranscribeResponse(text=text)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    current_user=Depends(require_student_role),
    db: AsyncSession = Depends(get_db),
):
    """Store a thumbs-up/down rating on an agent response turn. Used for RLHF."""
    if req.rating not in (1, -1):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="rating must be 1 or -1")
    repo = AgentRepository(db)
    session = await repo.get_session(req.session_id)
    query_text = None
    if session and session.history:
        import json as _json
        history = _json.loads(session.history) if isinstance(session.history, str) else session.history
        if isinstance(history, list) and req.turn_index < len(history):
            query_text = history[req.turn_index].get("query")
    await repo.save_feedback(
        session_id=req.session_id,
        turn_index=req.turn_index,
        user_id=int(current_user["sub"]),
        rating=req.rating,
        query_text=query_text,
    )
    return FeedbackResponse(saved=True)
