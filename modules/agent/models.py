from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, Column, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from core.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, nullable=False)
    session_id = Column(String(100), unique=True, nullable=False)
    state      = Column(JSONB, default={})
    history    = Column(JSONB, default=[])
    summary    = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentMemory(Base):
    __tablename__ = "student_memory"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, unique=True, nullable=False)
    preferred_areas = Column(JSONB, default=[])
    preference_vector = Column(Vector(384))
    liked_count     = Column(Integer, default=0)
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ResponseFeedback(Base):
    __tablename__ = "response_feedback"

    id          = Column(Integer, primary_key=True)
    session_id  = Column(String(100), nullable=False)
    turn_index  = Column(Integer, nullable=False)
    user_id     = Column(Integer, nullable=False)
    rating      = Column(SmallInteger)
    query_text  = Column(Text)
    created_at  = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id          = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False)
    source_id   = Column(Integer)
    chunk_text  = Column(Text, nullable=False)
    embedding   = Column(Vector(384))
    language    = Column(String(10), default="en")
    created_at  = Column(TIMESTAMP(timezone=True), server_default=func.now())
