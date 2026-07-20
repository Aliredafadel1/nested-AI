import logging
import sys
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging import RequestIDMiddleware, SecurityHeadersMiddleware, configure_logging
from core.security import RateLimitMiddleware
from modules.agent.router import router as agent_router
from modules.area_intel.router import router as area_intel_router
from modules.contracts.router import router as contracts_router
from modules.estimator.router import router as estimator_router
from modules.fraud.router import router as fraud_router
from modules.housing.router import router as housing_router
from modules.notifications.router import router as notifications_router
from modules.reputation.router import router as reputation_router
from modules.roommate.router import router as roommate_router
from modules.users.router import router as users_router

_startup_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0.1)
    if settings.ENVIRONMENT == "testing" and "pytest" not in sys.modules:
        _startup_logger.warning(
            "ENVIRONMENT=testing outside of pytest — IP rate limiting is disabled. "
            "Check your deployment configuration."
        )
    yield


app = FastAPI(
    title="NestAI API",
    description="AI-powered student housing platform for Lebanon",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# Middleware (order matters — outermost runs first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users_router)
app.include_router(housing_router)
app.include_router(roommate_router)
app.include_router(agent_router)
app.include_router(fraud_router)
app.include_router(contracts_router)
app.include_router(area_intel_router)
app.include_router(estimator_router)
app.include_router(notifications_router)
app.include_router(reputation_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "nestai-api"}
