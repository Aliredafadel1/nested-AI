from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.users.models import LandlordProfile, StudentProfile, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, role: str) -> User:
        user = User(email=email, password_hash=password_hash, role=role)
        self._db.add(user)
        await self._db.flush()
        return user

    async def get_student_profile(self, user_id: int) -> StudentProfile | None:
        result = await self._db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_student_profile(self, user_id: int, data: dict) -> StudentProfile:
        profile = await self.get_student_profile(user_id)
        if profile is None:
            profile = StudentProfile(user_id=user_id, **data)
            self._db.add(profile)
        else:
            for key, value in data.items():
                setattr(profile, key, value)
        await self._db.flush()
        return profile

    async def get_landlord_profile(self, user_id: int) -> LandlordProfile | None:
        result = await self._db.execute(
            select(LandlordProfile).where(LandlordProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_landlord_profile(self, user_id: int) -> LandlordProfile:
        profile = LandlordProfile(user_id=user_id)
        self._db.add(profile)
        await self._db.flush()
        return profile

    async def update_password(self, user_id: int, password_hash: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = password_hash
            await self._db.flush()

    async def update_profile_embeddings(
        self,
        user_id: int,
        embedding: list[float],
        dim_sleep: list[float],
        dim_study: list[float],
        dim_cleanliness: list[float],
        dim_guests: list[float],
        dim_budget: list[float],
    ) -> None:
        from sqlalchemy import text
        await self._db.execute(
            text("""
                UPDATE student_profiles SET
                    embedding        = :embedding,
                    dim_sleep        = :dim_sleep,
                    dim_study        = :dim_study,
                    dim_cleanliness  = :dim_cleanliness,
                    dim_guests       = :dim_guests,
                    dim_budget       = :dim_budget
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id,
                "embedding": str(embedding),
                "dim_sleep": str(dim_sleep),
                "dim_study": str(dim_study),
                "dim_cleanliness": str(dim_cleanliness),
                "dim_guests": str(dim_guests),
                "dim_budget": str(dim_budget),
            },
        )
        await self._db.flush()
