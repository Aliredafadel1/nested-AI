from sqlalchemy import Column, Integer, TIMESTAMP
from sqlalchemy.sql import func
from core.database import Base


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer)
    listing_id    = Column(Integer)
    university_id = Column(Integer)
    rent          = Column(Integer)
    generator     = Column(Integer)
    water         = Column(Integer, default=15)
    internet      = Column(Integer, default=30)
    transport     = Column(Integer)
    total_monthly = Column(Integer)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())
