from datetime import timedelta

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.redis import RedisKeys
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from modules.users.repository import UserRepository
from modules.users.schemas import (  # noqa: F401
    LoginRequest,
    OnboardingRequest,
    RegisterRequest,
    TokenResponse,
)


class UserService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._repo = UserRepository(db)
        self._redis = redis

    async def register(self, req: RegisterRequest) -> TokenResponse:
        existing = await self._repo.get_by_email(req.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")

        user = await self._repo.create(
            email=req.email,
            password_hash=hash_password(req.password),
            role=req.role,
        )
        if req.role == "landlord":
            await self._repo.create_landlord_profile(user.id)

        access_token = create_access_token(user.id, user.role)
        raw_refresh, hashed_refresh = create_refresh_token(user.id)
        await self._redis.setex(
            RedisKeys.refresh(user.id),
            int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            hashed_refresh,
        )
        return TokenResponse(access_token=access_token, role=user.role), raw_refresh

    async def login(self, req: LoginRequest):
        user = await self._repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        access_token = create_access_token(user.id, user.role)
        raw_refresh, hashed_refresh = create_refresh_token(user.id)
        await self._redis.setex(
            RedisKeys.refresh(user.id),
            int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            hashed_refresh,
        )
        return TokenResponse(access_token=access_token, role=user.role), raw_refresh

    async def refresh(self, user_id: int, raw_refresh: str) -> TokenResponse:
        stored_hash = await self._redis.get(RedisKeys.refresh(user_id))
        if not stored_hash or stored_hash != hash_refresh_token(raw_refresh):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Rotate: issue new, delete old
        await self._redis.delete(RedisKeys.refresh(user_id))
        access_token = create_access_token(user.id, user.role)
        raw_new, hashed_new = create_refresh_token(user.id)
        await self._redis.setex(
            RedisKeys.refresh(user.id),
            int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            hashed_new,
        )
        return TokenResponse(access_token=access_token, role=user.role), raw_new

    async def logout(self, user_id: int) -> None:
        await self._redis.delete(RedisKeys.refresh(user_id))

    async def demo_login(self):
        from fastapi import HTTPException
        user = await self._repo.get_by_email("jawad@demo.com")
        if not user:
            raise HTTPException(status_code=503, detail="Demo persona not seeded. Run: docker compose exec db psql -U nestai -d nestai -f /seed/listings.sql")
        access_token = create_access_token(user.id, user.role)
        raw_refresh, hashed_refresh = create_refresh_token(user.id)
        from datetime import timedelta

        from core.config import settings
        from core.redis import RedisKeys
        await self._redis.setex(
            RedisKeys.refresh(user.id),
            int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
            hashed_refresh,
        )
        return TokenResponse(access_token=access_token, role=user.role), raw_refresh

    async def forgot_password(self, email: str) -> None:
        import secrets
        from core.email import send_password_reset_email
        user = await self._repo.get_by_email(email)
        if not user:
            return  # Don't leak whether the email exists
        token = secrets.token_urlsafe(32)
        await self._redis.setex(RedisKeys.reset_token(token), 900, str(user.id))
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_password_reset_email(user.email, reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        user_id_str = await self._redis.get(RedisKeys.reset_token(token))
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Reset token is invalid or has expired.")
        await self._redis.delete(RedisKeys.reset_token(token))
        await self._repo.update_password(int(user_id_str), hash_password(new_password))

    async def get_me(self, user_id: int, role: str):
        from modules.users.schemas import StudentProfileOut, UserMeOut
        user = await self._repo.get_by_id(user_id)
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found.")
        profile = None
        if role == "student":
            sp = await self._repo.get_student_profile(user_id)
            if sp:
                profile = StudentProfileOut.model_validate(sp)
        elif role == "landlord":
            lp = await self._repo.get_landlord_profile(user_id)
            if lp:
                profile = {"user_id": lp.user_id}
        return UserMeOut(id=user.id, email=user.email, role=user.role, profile=profile)

    async def save_onboarding(self, user_id: int, req: OnboardingRequest):
        data = req.model_dump(exclude_none=True)
        profile = await self._repo.upsert_student_profile(user_id, data)
        from modules.users.tasks import embed_profile
        embed_profile.delay(user_id)
        return profile
