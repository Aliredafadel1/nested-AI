import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.redis import get_redis_dep
from core.security import get_current_user, require_student_role
from modules.users.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    OnboardingRequest,
    RegisterRequest,
    ResetPasswordRequest,
    StudentProfileOut,
    TokenResponse,
    UserMeOut,
)
from modules.users.service import UserService

router = APIRouter(tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/auth/refresh",
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    token, raw_refresh = await svc.register(req)
    _set_refresh_cookie(response, raw_refresh)
    return token


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    token, raw_refresh = await svc.login(req)
    _set_refresh_cookie(response, raw_refresh)
    return token


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    from fastapi import HTTPException
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided.")

    try:
        user_id = int(refresh_token.split("_")[1])
    except (IndexError, ValueError) as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token format.") from e

    svc = UserService(db, redis)
    token, raw_new = await svc.refresh(user_id, refresh_token)
    _set_refresh_cookie(response, raw_new)
    return token


@router.post("/auth/forgot-password", status_code=202)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    await svc.forgot_password(req.email)
    return {"message": "If this email is registered, a reset link has been sent."}


@router.post("/auth/reset-password", status_code=204)
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    await svc.reset_password(req.token, req.new_password)


@router.post("/auth/demo", response_model=TokenResponse)
async def demo_login(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    """One-click demo login as Jawad — no password required. Demo use only."""
    svc = UserService(db, redis)
    token, raw_refresh = await svc.demo_login()
    _set_refresh_cookie(response, raw_refresh)
    return token


@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    await svc.logout(int(current_user["sub"]))
    response.delete_cookie(REFRESH_COOKIE)


@router.get("/users/me", response_model=UserMeOut)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    return await svc.get_me(int(current_user["sub"]), current_user["role"])


@router.post("/users/onboarding", response_model=StudentProfileOut)
async def onboarding(
    req: OnboardingRequest,
    current_user: dict = Depends(require_student_role),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = UserService(db, redis)
    return await svc.save_onboarding(int(current_user["sub"]), req)
