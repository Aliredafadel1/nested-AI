from datetime import datetime

from pydantic import BaseModel, Field


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


class RequestRespond(BaseModel):
    accept: bool


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class MessageOut(BaseModel):
    id:         int
    request_id: int
    sender_id:  int
    content:    str
    created_at: datetime

    model_config = {"from_attributes": True}
