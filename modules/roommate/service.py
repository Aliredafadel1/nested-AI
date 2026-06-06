from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.roommate.repository import RoommateRepository
from modules.roommate.schemas import MatchOut, RequestOut


class RoommateService:
    def __init__(self, db: AsyncSession):
        self._repo = RoommateRepository(db)

    async def get_matches(self, current_user_id: int) -> list[MatchOut]:
        dim_vectors = await self._repo.get_caller_dim_vectors(current_user_id)
        if dim_vectors is None:
            raise HTTPException(
                status_code=422,
                detail="Complete your onboarding first — your profile has no embedding yet.",
            )
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
