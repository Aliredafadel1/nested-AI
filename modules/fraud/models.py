from sqlalchemy import TIMESTAMP, Column, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from core.database import Base


class FraudReport(Base):
    __tablename__ = "fraud_reports"

    id           = Column(Integer, primary_key=True)
    listing_id   = Column(Integer, nullable=False)
    score        = Column(Numeric(4, 3), default=0.000)
    price_zscore = Column(Numeric(6, 3))
    evidence     = Column(JSONB, default={
        "price_flags": [], "phone_flags": [], "photo_flags": [], "text_flags": []
    })
    created_at   = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at   = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
