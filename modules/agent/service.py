from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import RedisKeys
from core.storage import Bucket, validate_magic_bytes
from modules.agent.repository import AgentRepository
from modules.agent.schemas import AgentState, ChatRequest, FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".mp4", ".wav", ".m4a", ".mp3"}
SESSION_TTL = 7200  # 2 hours


class AgentService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._db    = db
        self._redis = redis

    async def _check_llm_rate(self, user_id: int, task: str, limit: int) -> None:
        key = RedisKeys.rate_llm(user_id, task)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 86400)
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit reached. You can use this feature up to {limit} times per day.",
            )

    async def check_chat_rate(self, user_id: int) -> None:
        await self._check_llm_rate(user_id, "agent_chat", 50)

    async def check_transcribe_rate(self, user_id: int) -> None:
        await self._check_llm_rate(user_id, "transcribe", 20)

    async def chat(self, user_id: int, req: ChatRequest) -> AsyncGenerator[str, None]:
        from modules.agent.graph import build_graph

        session_id = req.session_id or str(uuid.uuid4())

        # Load or initialise session state from Redis
        state_raw = await self._redis.get(RedisKeys.session(user_id, session_id))
        if state_raw:
            try:
                state: AgentState = json.loads(state_raw)
            except Exception:
                state = self._init_state(user_id, session_id, req.query)
        else:
            state = self._init_state(user_id, session_id, req.query)
            # Ensure the session row exists in PostgreSQL
            repo = AgentRepository(self._db)
            existing = await repo.get_session(session_id)
            if not existing:
                await repo.create_session(user_id, session_id)

        state["query"] = req.query
        if req.language in ("ar", "en", "3arabizi"):
            state["language"] = req.language

        graph = build_graph(self._db, self._redis)
        async for chunk in graph(state):
            yield chunk

    async def transcribe(self, user_id: int, file: UploadFile) -> str:
        import os

        from core.llm_router import transcribe_audio

        filename = file.filename or "audio.webm"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        if len(file_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit.")

        # Magic-byte validation — constitution requires this before any upload/processing
        validate_magic_bytes(file_bytes, Bucket.AUDIO)

        return transcribe_audio(file_bytes, filename)

    async def save_feedback(self, user_id: int, req: FeedbackRequest) -> FeedbackResponse:
        import json as _json

        if req.rating not in (1, -1):
            raise HTTPException(status_code=400, detail="rating must be 1 or -1")

        repo = AgentRepository(self._db)
        session = await repo.get_session(req.session_id)
        query_text = None
        if session and session.history:
            history = (
                _json.loads(session.history)
                if isinstance(session.history, str)
                else session.history
            )
            if isinstance(history, list) and req.turn_index < len(history):
                query_text = history[req.turn_index].get("query")

        await repo.save_feedback(
            session_id=req.session_id,
            turn_index=req.turn_index,
            user_id=user_id,
            rating=req.rating,
            query_text=query_text,
        )
        return FeedbackResponse(saved=True)

    def _init_state(self, user_id: int, session_id: str, query: str) -> AgentState:
        return AgentState(
            query=query,
            session_id=session_id,
            intent={},
            listings=[],
            retry_count=0,
            comparison=None,
            response=None,
            errors=[],
            _regen=False,
            user_id=user_id,
            history=[],
        )
