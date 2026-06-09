from datetime import datetime

from pydantic import BaseModel


class FraudEvidence(BaseModel):
    price_flags:   list[str] = []
    phone_flags:   list[str] = []
    photo_flags:   list[str] = []
    ip_flags:      list[str] = []
    content_flags: list[str] = []
    text_flags:    list[str] = []


class FraudReportOut(BaseModel):
    listing_id:   int
    score:        float
    price_zscore: float | None
    evidence:     FraudEvidence
    computed_at:  datetime

    model_config = {"from_attributes": True}
