from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    listing_id:     int | None = None
    maintenance:    int | None = Field(None, ge=1, le=5)
    responsiveness: int | None = Field(None, ge=1, le=5)
    honesty:        int | None = Field(None, ge=1, le=5)
    hidden_fees:    int | None = Field(None, ge=1, le=5)


class ReviewOut(BaseModel):
    id:             int
    landlord_id:    int
    reviewer_id:    int
    listing_id:     int | None
    maintenance:    int | None
    responsiveness: int | None
    honesty:        int | None
    hidden_fees:    int | None
    ai_summary:     str | None
    created_at:     datetime

    model_config = {"from_attributes": True}


class LandlordReputationOut(BaseModel):
    landlord_id:        int
    review_count:       int
    avg_maintenance:    float | None
    avg_responsiveness: float | None
    avg_honesty:        float | None
    avg_hidden_fees:    float | None
    avg_overall:        float | None
    reviews:            list[ReviewOut]
