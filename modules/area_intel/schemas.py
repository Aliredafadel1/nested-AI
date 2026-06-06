from pydantic import BaseModel


class NeighborhoodOut(BaseModel):
    id:              int
    name:            str
    name_ar:         str | None
    electricity_hours: float | None
    generator_cost:  int | None
    internet:        int | None
    transport:       int | None
    safety:          int | None
    student_vibe:    int | None

    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    area_a: str
    area_b: str


class CompareOut(BaseModel):
    area_a: NeighborhoodOut
    area_b: NeighborhoodOut
