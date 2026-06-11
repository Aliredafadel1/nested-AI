from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class RoommateRequest(Base):
    __tablename__ = "roommate_requests"

    id:           Mapped[int]        = mapped_column(Integer, primary_key=True)
    from_user_id: Mapped[int]        = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id:   Mapped[int]        = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    score:        Mapped[float | None] = mapped_column(Numeric(4, 3))
    dimensions:   Mapped[dict]       = mapped_column(JSONB, default=dict)
    status:       Mapped[str]        = mapped_column(String(20), default="pending")
    created_at:   Mapped[str]        = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RoommateMessage(Base):
    __tablename__ = "roommate_messages"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("roommate_requests.id"), nullable=False)
    sender_id:  Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content:    Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
