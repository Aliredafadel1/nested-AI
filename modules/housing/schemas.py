from pydantic import BaseModel, ConfigDict, computed_field

from core.features import (
    amenity_count,
    amenity_score,
    bedroom_type,
    detect_language,
    has_essentials,
    is_premium,
    price_per_sqm,
)


class NeighborhoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    name_ar: str | None
    electricity: float | None
    generator_cost: int | None
    internet: int | None
    transport: int | None
    safety: int | None
    student_vibe: int | None


class ListingPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    minio_key: str
    is_primary: bool


class ListingVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone_verified: bool
    photos_reviewed: bool
    price_in_range: bool


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: int
    landlord_id: int
    neighbourhood_id: int
    title: str
    description: str | None
    price: int
    bedrooms: int
    bathrooms: int
    area_sqm: int | None
    amenities: dict
    address: str | None
    lat: float | None
    lng: float | None
    status: str
    fraud_score: float
    photos: list[ListingPhotoOut] = []
    verification: ListingVerificationOut | None = None

    # ── Computed features ────────────────────────────────────────────────────
    @computed_field
    @property
    def price_per_sqm(self) -> float | None:
        return price_per_sqm(self.price, self.area_sqm)

    @computed_field
    @property
    def amenity_count(self) -> int:
        return amenity_count(self.amenities)

    @computed_field
    @property
    def amenity_score(self) -> float:
        return amenity_score(self.amenities)

    @computed_field
    @property
    def bedroom_type(self) -> str:
        return bedroom_type(self.bedrooms, self.area_sqm)

    @computed_field
    @property
    def has_essentials(self) -> bool:
        return has_essentials(self.amenities)

    @computed_field
    @property
    def is_premium(self) -> bool:
        return is_premium(self.amenities)

    @computed_field
    @property
    def listing_language(self) -> str:
        return detect_language(f"{self.title} {self.description or ''}")


class ListingCreate(BaseModel):
    neighbourhood_id: int
    title: str
    description: str | None = None
    price: int
    bedrooms: int
    bathrooms: int = 1
    area_sqm: int | None = None
    amenities: dict = {}
    address: str | None = None
    lat: float | None = None
    lng: float | None = None


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqm: int | None = None
    amenities: dict | None = None
    address: str | None = None


class ListingFilters(BaseModel):
    neighbourhood: str | None = None
    neighbourhood_id: int | None = None
    min_price: int | None = None
    max_price: int | None = None
    bedrooms: int | None = None
    status: str = "active"
    skip: int = 0
    limit: int = 50
