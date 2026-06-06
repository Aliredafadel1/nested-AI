from datetime import datetime
from pydantic import BaseModel


class DimensionScores(BaseModel):
    sleep:       float
    study:       float
    cleanliness: float
    guests:      float
    budget:      float


class MatchOut(BaseModel):
    user_id:    int
    score:      float
    dimensions: DimensionScores

    model_config = {"from_attributes": True}


class RequestCreate(BaseModel):
    to_user_id: int


class RequestOut(BaseModel):
    id:           int
    from_user_id: int
    to_user_id:   int
    score:        float | None
    dimensions:   dict
    status:       str
    created_at:   datetime

    model_config = {"from_attributes": True}
