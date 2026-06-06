from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id:           Mapped[int]  = mapped_column(Integer, primary_key=True)
    email:        Mapped[str]  = mapped_column(String(255), unique=True, nullable=False)
    password_hash:Mapped[str]  = mapped_column(String(255), nullable=False)
    role:         Mapped[str]  = mapped_column(String(20), nullable=False)
    created_at:   Mapped[str]  = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    student_profile:  Mapped["StudentProfile | None"]  = relationship(back_populates="user", uselist=False)
    landlord_profile: Mapped["LandlordProfile | None"] = relationship(back_populates="user", uselist=False)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id:                Mapped[int]       = mapped_column(Integer, primary_key=True)
    user_id:           Mapped[int]       = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    university_id:     Mapped[int | None]= mapped_column(Integer, ForeignKey("universities.id"))
    budget_min:        Mapped[int | None]= mapped_column(Integer)
    budget_max:        Mapped[int | None]= mapped_column(Integer)
    sleep_schedule:    Mapped[str | None]= mapped_column(String(20))
    study_habits:      Mapped[str | None]= mapped_column(String(20))
    cleanliness:       Mapped[str | None]= mapped_column(String(20))
    guests:            Mapped[str | None]= mapped_column(String(20))
    language:          Mapped[str | None]= mapped_column(String(20))
    priorities:        Mapped[list]      = mapped_column(JSONB, default=list)
    embedding:         Mapped[list | None] = mapped_column(Vector(1024))
    preference_vector: Mapped[list | None] = mapped_column(Vector(1024))
    updated_at:        Mapped[str]       = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="student_profile")


class LandlordProfile(Base):
    __tablename__ = "landlord_profiles"

    id:               Mapped[int]        = mapped_column(Integer, primary_key=True)
    user_id:          Mapped[int]        = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone:            Mapped[str | None] = mapped_column(String(30))
    phone_verified:   Mapped[bool]       = mapped_column(Boolean, default=False)
    reputation_score: Mapped[float]      = mapped_column(Numeric(3, 2), default=0.00)

    user: Mapped["User"] = relationship(back_populates="landlord_profile")
