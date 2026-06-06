from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from core.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, nullable=False)
    minio_key  = Column(String(500), nullable=False)
    ocr_used   = Column(Boolean, default=False)
    analysis   = Column(JSONB)
    status     = Column(String(30), default="pending")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
