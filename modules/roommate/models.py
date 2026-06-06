from sqlalchemy import Integer, Numeric, ForeignKey, TIMESTAMP, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

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
