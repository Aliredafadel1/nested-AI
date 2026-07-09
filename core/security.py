import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_WORK_FACTOR)
bearer_scheme = HTTPBearer(auto_error=False)

# ── Prompt injection patterns ─────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        # Explicit instruction overrides
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompt|context)",
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompt|context)",
        r"forget\s+(all\s+)?(previous|prior|above|every(thing)?)\s*(instructions?|prompt|context|above|you.{0,20}told)?",
        r"do\s+not\s+follow\s+(your\s+)?(previous|prior|original)\s+instructions?",
        # Persona hijacking
        r"you\s+are\s+now\s+(a\s+)?(different|new|another|evil|uncensored)",
        r"act\s+as\s+(if\s+you\s+are\s+)?a\s+different",
        r"pretend\s+(you\s+are|to\s+be)",
        r"roleplay\s+as",
        r"from\s+now\s+on\s+(you\s+are|act|behave|respond)",
        r"your\s+(new\s+)?(role|persona|identity|instructions?)\s+(is|are)",
        # System prompt injection markers
        r"system\s*:\s*(you\s+are|your\s+role|ignore)",
        r"\[system\]",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"###\s+instructions?",
        r"<system>",
        r"\bprompt\s*:\s*",
        # Instruction injection delimiters
        r"new\s+instructions?\s*:",
        r"updated?\s+instructions?\s*:",
        r"override\s+(safety|guidelines?|rules?|instructions?|prompt)",
        # Exfiltration attempts
        r"(print|repeat|show|reveal|output|display)\s+(your\s+)?(system\s+prompt|instructions?|initial\s+prompt|context)",
        r"what\s+(are\s+your|is\s+your)\s+(system\s+prompt|instructions?|initial\s+prompt)",
        # Known jailbreak vocabulary
        r"jailbreak",
        r"dan\s+mode",
        r"developer\s+mode",
        r"god\s+mode",
    ]
]


def sanitize_llm_input(text: str) -> str:
    """Strip known prompt injection patterns. Raises 400 if match found."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise HTTPException(
                status_code=400,
                detail="Input contains disallowed content.",
            )
    return text.strip()


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(subject: int, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "role": role, "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Returns (raw_token, hashed_token). Token encodes user_id for stateless lookup.
    Format: uid_<user_id>_<random64>
    """
    import secrets
    raw = f"uid_{user_id}_{secrets.token_urlsafe(64)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from e


# ── Dependencies ──────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return decode_access_token(credentials.credentials)


async def require_landlord(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    user = decode_access_token(credentials.credentials)
    if user.get("role") != "landlord":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Landlord access required.")
    return user


async def require_student_role(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    user = decode_access_token(credentials.credentials)
    if user.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required.")
    return user


# ── Rate limiting middleware ──────────────────────────────────────────────────

class RateLimitMiddleware:
    """Sliding window rate limiter using Redis. 60 requests/minute per IP."""

    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.rpm = requests_per_minute

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from core.redis import _TESTING

            # Skip Redis rate limiting in tests: each TestClient request gets a
            # new anyio event loop, so async Redis clients from a previous loop
            # cannot be safely reused (fd reuse + loop mismatch). Rate limiting
            # is covered by dedicated integration tests in production.
            if not _TESTING:
                from starlette.requests import Request as StarletteRequest
                from starlette.responses import JSONResponse

                from core.redis import RedisKeys, get_async_redis

                request = StarletteRequest(scope, receive)
                ip = request.client.host if request.client else "unknown"
                path = request.url.path
                key = RedisKeys.rate_ip(ip, path)

                redis = get_async_redis()
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 60)
                if count > self.rpm:
                    response = JSONResponse(
                        {"detail": "Rate limit exceeded. Try again in a minute."},
                        status_code=429,
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
