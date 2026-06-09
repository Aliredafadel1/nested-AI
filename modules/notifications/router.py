import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis_dep
from core.security import get_current_user
from modules.notifications.schemas import NotificationOut
from modules.notifications.service import NotificationsService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _svc(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> NotificationsService:
    return NotificationsService(db, redis)


@router.get("/stream")
async def stream_notifications(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    svc = NotificationsService(db, redis)
    return StreamingResponse(
        svc.stream_events(db, int(current_user["sub"])),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    current_user=Depends(get_current_user),
    svc: NotificationsService = Depends(_svc),
):
    return await svc.get_all(int(current_user["sub"]))


@router.post("/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    svc: NotificationsService = Depends(_svc),
):
    await svc.mark_read(int(current_user["sub"]), notification_id)
