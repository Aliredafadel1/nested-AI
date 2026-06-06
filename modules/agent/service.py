from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.redis import RedisKeys
from modules.agent.repository import AgentRepository
from modules.agent.schemas import AgentState, ChatRequest

logger = logging.getLogger(__name__)

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".mp4", ".wav", ".m4a", ".mp3"}
SESSION_TTL = 7200  # 2 hours


class AgentService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._db    = db
        self._redis = redis

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

        graph = build_graph(self._db, self._redis)
        async for chunk in graph(state):
            yield chunk

    async def transcribe(self, file: UploadFile) -> str:
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

        return transcribe_audio(file_bytes, filename)

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
