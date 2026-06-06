from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from core.redis import RedisKeys
from modules.notifications.repository import NotificationsRepository
from modules.notifications.schemas import NotificationOut

logger = logging.getLogger(__name__)


class NotificationsService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._repo = NotificationsRepository(db)
        self._redis = redis

    async def get_all(self, user_id: int) -> list[NotificationOut]:
        rows = await self._repo.get_all(user_id)
        return [NotificationOut.model_validate(r) for r in rows]

    async def mark_read(self, user_id: int, notification_id: int) -> None:
        notif = await self._repo.get_by_id(notification_id)
        if not notif:
            raise HTTPException(status_code=404, detail="Notification not found.")
        if notif.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your notification.")
        await self._repo.mark_read(notification_id, user_id)

    async def stream_events(
        self, db: AsyncSession, user_id: int
    ) -> AsyncGenerator[str, None]:
        # Deliver pending unread notifications on connect
        unread = await self._repo.get_unread(user_id)
        for notif in unread:
            data = NotificationOut.model_validate(notif).model_dump()
            data["created_at"] = data["created_at"].isoformat()
            yield f"data: {json.dumps(data)}\n\n"

        # Subscribe to Redis pub/sub for real-time events
        pubsub = self._redis.pubsub()
        channel = RedisKeys.sse_channel(user_id)
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    @staticmethod
    async def publish(redis: aioredis.Redis, user_id: int, type_: str, payload: dict) -> None:
        message = json.dumps({"type": type_, "payload": payload})
        try:
            await redis.publish(RedisKeys.sse_channel(user_id), message)
        except Exception:
            logger.warning("notifications.publish | failed to publish to user_id=%s", user_id)
