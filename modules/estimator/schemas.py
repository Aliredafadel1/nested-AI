from pydantic import BaseModel


class EstimateRequest(BaseModel):
    rent:             int
    neighbourhood_id: int
    university_id:    int | None = None


class EstimateOut(BaseModel):
    rent:            int
    generator:       int
    water:           int
    internet:        int
    transport:       int
    total_monthly:   int
    commute_minutes: int | None

    model_config = {"from_attributes": True}
