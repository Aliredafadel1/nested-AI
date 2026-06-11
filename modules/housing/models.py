from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from modules.area_intel.models import Neighborhood  # area_intel owns this table


class University(Base):
    __tablename__ = "universities"

    id:   Mapped[int]   = mapped_column(Integer, primary_key=True)
    name: Mapped[str]   = mapped_column(String(200), unique=True, nullable=False)
    lat:  Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    lng:  Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)


class Listing(Base):
    __tablename__ = "listings"

    id:               Mapped[int]        = mapped_column(Integer, primary_key=True)
    landlord_id:      Mapped[int]        = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    neighbourhood_id: Mapped[int]        = mapped_column(Integer, ForeignKey("neighborhoods.id"), nullable=False)
    title:            Mapped[str]        = mapped_column(String(300), nullable=False)
    description:      Mapped[str | None] = mapped_column(Text)
    price:            Mapped[int]        = mapped_column(Integer, nullable=False)
    bedrooms:         Mapped[int]        = mapped_column(SmallInteger, nullable=False)
    bathrooms:        Mapped[int]        = mapped_column(SmallInteger, default=1)
    area_sqm:         Mapped[int | None] = mapped_column(Integer)
    amenities:        Mapped[dict]       = mapped_column(JSONB, default=dict)
    address:          Mapped[str | None] = mapped_column(String(300))
    lat:              Mapped[float | None] = mapped_column(Numeric(10, 7))
    lng:              Mapped[float | None] = mapped_column(Numeric(10, 7))
    status:           Mapped[str]        = mapped_column(String(20), default="active")
    ip_address:       Mapped[str | None] = mapped_column(String(45))
    fraud_score:      Mapped[float]      = mapped_column(Numeric(4, 3), default=0.000)
    embedding:        Mapped[list | None] = mapped_column(Vector(384))
    created_at:       Mapped[str]        = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at:       Mapped[str]        = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    neighborhood:   Mapped["Neighborhood"]         = relationship(foreign_keys=[neighbourhood_id], viewonly=True)
    photos:         Mapped[list["ListingPhoto"]]   = relationship(back_populates="listing", cascade="all, delete-orphan")
    verification:   Mapped["ListingVerification | None"] = relationship(back_populates="listing", uselist=False)


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id:         Mapped[int]        = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int]        = mapped_column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    minio_key:  Mapped[str]        = mapped_column(String(500), nullable=False)
    phash:      Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool]       = mapped_column(Boolean, default=False)
    created_at: Mapped[str]        = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    listing: Mapped["Listing"] = relationship(back_populates="photos")


class ListingVerification(Base):
    __tablename__ = "listing_verifications"

    id:             Mapped[int]  = mapped_column(Integer, primary_key=True)
    listing_id:     Mapped[int]  = mapped_column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), unique=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    photos_reviewed:Mapped[bool] = mapped_column(Boolean, default=False)
    price_in_range: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at:    Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))

    listing: Mapped["Listing"] = relationship(back_populates="verification")


class SavedListing(Base):
    __tablename__ = "saved_listings"

    user_id:    Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    saved_at:   Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
