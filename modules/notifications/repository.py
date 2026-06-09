from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.notifications.models import Notification


class NotificationsRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_unread(self, user_id: int) -> list[Notification]:
        result = await self._db.execute(
            select(Notification)
            .where(Notification.user_id == user_id, ~Notification.read)
            .order_by(Notification.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_all(self, user_id: int, limit: int = 50) -> list[Notification]:
        result = await self._db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, notification_id: int) -> Notification | None:
        result = await self._db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def mark_read(self, notification_id: int, user_id: int) -> bool:
        result = await self._db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read=True)
            .returning(Notification.id)
        )
        await self._db.commit()
        return result.scalar_one_or_none() is not None

    async def create(self, user_id: int, type_: str, payload: dict) -> Notification:
        notif = Notification(user_id=user_id, type=type_, payload=payload)
        self._db.add(notif)
        await self._db.commit()
        await self._db.refresh(notif)
        return notif
