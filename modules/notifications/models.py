from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, nullable=False)
    type       = Column(String(50), nullable=False)
    payload    = Column(JSONB, default={})
    read       = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
