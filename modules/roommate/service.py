from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from modules.roommate.repository import RoommateRepository
from modules.roommate.schemas import MatchOut, MessageOut, RequestOut


class RoommateService:
    def __init__(self, db: AsyncSession):
        self._repo = RoommateRepository(db)

    async def get_matches(self, current_user_id: int) -> list[MatchOut]:
        result = await self._repo._db.execute(
            text("SELECT 1 FROM student_profiles WHERE user_id = :uid"),
            {"uid": current_user_id},
        )
        if result.one_or_none() is None:
            raise HTTPException(
                status_code=422,
                detail="Complete your onboarding first to see roommate matches.",
            )

        dim_vectors = await self._repo.get_caller_dim_vectors(current_user_id)
        if dim_vectors is None:
            return await self._repo.get_matches_fallback(current_user_id)
        return await self._repo.get_matches(current_user_id, dim_vectors)

    async def send_request(self, from_user_id: int, to_user_id: int) -> RequestOut:
        exists = await self._repo.target_student_exists(to_user_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Target student not found.")

        req = await self._repo.create_request(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            score=None,
            dimensions={},
        )
        return RequestOut.model_validate(req)

    async def get_my_requests(self, user_id: int) -> list[RequestOut]:
        requests = await self._repo.get_my_requests(user_id)
        return [RequestOut.model_validate(r) for r in requests]

    async def respond_to_request(self, request_id: int, user_id: int, accept: bool) -> RequestOut:
        req = await self._repo.get_request_by_id(request_id)
        if req is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if req.to_user_id != user_id:
            raise HTTPException(status_code=403, detail="Only the recipient can respond.")
        if req.status != "pending":
            raise HTTPException(status_code=409, detail="Request already responded to.")

        updated = await self._repo.update_request_status(
            request_id, "accepted" if accept else "declined"
        )
        return RequestOut.model_validate(updated)

    async def send_message(self, request_id: int, sender_id: int, content: str) -> MessageOut:
        req = await self._repo.get_request_by_id(request_id)
        if req is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if req.from_user_id != sender_id and req.to_user_id != sender_id:
            raise HTTPException(status_code=403, detail="Not a participant in this thread.")
        if req.status != "accepted":
            raise HTTPException(status_code=409, detail="Messaging is only available for accepted requests.")

        msg = await self._repo.create_message(request_id, sender_id, content)
        return MessageOut.model_validate(msg)

    async def get_thread(self, request_id: int, user_id: int) -> list[MessageOut]:
        req = await self._repo.get_request_by_id(request_id)
        if req is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if req.from_user_id != user_id and req.to_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not a participant in this thread.")

        messages = await self._repo.get_messages(request_id)
        return [MessageOut.model_validate(m) for m in messages]
