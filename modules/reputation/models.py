from sqlalchemy import TIMESTAMP, Integer, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class LandlordReview(Base):
    __tablename__ = "landlord_reviews"

    id:             Mapped[int]        = mapped_column(Integer, primary_key=True)
    landlord_id:    Mapped[int]        = mapped_column(Integer, nullable=False)
    reviewer_id:    Mapped[int]        = mapped_column(Integer, nullable=False)
    listing_id:     Mapped[int | None] = mapped_column(Integer)
    maintenance:    Mapped[int | None] = mapped_column(SmallInteger)
    responsiveness: Mapped[int | None] = mapped_column(SmallInteger)
    honesty:        Mapped[int | None] = mapped_column(SmallInteger)
    hidden_fees:    Mapped[int | None] = mapped_column(SmallInteger)
    ai_summary:     Mapped[str | None] = mapped_column(Text)
    created_at:     Mapped[str]        = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
