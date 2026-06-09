from __future__ import annotations

import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.agent.models import AgentSession, StudentMemory


class AgentRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_session(self, user_id: int, session_id: str) -> AgentSession:
        session = AgentSession(user_id=user_id, session_id=session_id, state={}, history=[])
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> AgentSession | None:
        result = await self._db.execute(
            select(AgentSession).where(AgentSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_session(self, session_id: str, history: list, summary: str) -> None:
        await self._db.execute(
            text(
                "UPDATE agent_sessions SET history = CAST(:history AS jsonb), summary = :summary, "
                "updated_at = NOW() WHERE session_id = :sid"
            ),
            {
                "history": json.dumps(history),
                "summary": summary,
                "sid":     session_id,
            },
        )
        await self._db.commit()

    async def listing_exists(self, listing_id: int) -> bool:
        result = await self._db.execute(
            text("SELECT EXISTS(SELECT 1 FROM listings WHERE id = :id)"),
            {"id": listing_id},
        )
        return bool(result.scalar_one())

    async def search_rag_chunks(
        self, embedding: list[float], limit: int = 3
    ) -> list[dict]:
        result = await self._db.execute(
            text(
                """
                SELECT chunk_text, source_type, language
                FROM rag_chunks
                WHERE source_type = 'housing_faq'
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :vec::vector
                LIMIT :limit
                """
            ),
            {"vec": str(embedding), "limit": limit},
        )
        return [
            {"chunk_text": row[0], "source_type": row[1], "language": row[2]}
            for row in result.fetchall()
        ]

    async def save_feedback(
        self, session_id: str, turn_index: int, user_id: int, rating: int, query_text: str | None
    ) -> None:
        await self._db.execute(
            text(
                "INSERT INTO response_feedback (session_id, turn_index, user_id, rating, query_text) "
                "VALUES (:sid, :ti, :uid, :rating, :qt)"
            ),
            {"sid": session_id, "ti": turn_index, "uid": user_id, "rating": rating, "qt": query_text},
        )
        await self._db.commit()

    async def get_good_responses(self, limit: int = 5) -> list[dict]:
        """Retrieve recent highly-rated (👍) Q&A turns for few-shot injection."""
        result = await self._db.execute(
            text(
                """
                SELECT rf.query_text, ags.history
                FROM response_feedback rf
                JOIN agent_sessions ags ON ags.session_id = rf.session_id
                WHERE rf.rating = 1
                  AND rf.query_text IS NOT NULL
                  AND ags.history IS NOT NULL
                ORDER BY rf.created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        rows = result.fetchall()
        examples = []
        for query_text, history_json in rows:
            import json as _json
            try:
                history = _json.loads(history_json) if isinstance(history_json, str) else history_json
                if history:
                    last_turn = history[-1]
                    examples.append({"query": query_text, "response": last_turn.get("response", "")[:400]})
            except Exception:
                pass
        return examples

    async def upsert_student_memory(
        self, user_id: int, preferred_areas: list, liked_count: int
    ) -> StudentMemory:
        result = await self._db.execute(
            select(StudentMemory).where(StudentMemory.user_id == user_id)
        )
        memory = result.scalar_one_or_none()
        if memory:
            memory.preferred_areas = preferred_areas
            memory.liked_count     = liked_count
        else:
            memory = StudentMemory(
                user_id=user_id,
                preferred_areas=preferred_areas,
                liked_count=liked_count,
            )
            self._db.add(memory)
        await self._db.commit()
        return memory
