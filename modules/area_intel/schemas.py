from pydantic import BaseModel, computed_field

from core.features import electricity_reliability, livability_score, student_score


class NeighborhoodOut(BaseModel):
    id:               int
    name:             str
    name_ar:          str | None
    electricity:      float | None
    generator_cost:   int | None
    internet:         int | None
    transport:        int | None
    safety:           int | None
    student_vibe:     int | None

    model_config = {"from_attributes": True, "extra": "ignore"}

    # ── Composite scores ─────────────────────────────────────────────────────
    @computed_field
    @property
    def livability_score(self) -> float:
        return livability_score(self.electricity, self.internet,
                                self.safety, self.transport)

    @computed_field
    @property
    def student_score(self) -> float:
        return student_score(self.student_vibe, self.transport,
                             self.safety, self.internet)

    @computed_field
    @property
    def electricity_reliability(self) -> float:
        return electricity_reliability(self.electricity)


class CompareRequest(BaseModel):
    area_a: str
    area_b: str


class CompareOut(BaseModel):
    area_a: NeighborhoodOut
    area_b: NeighborhoodOut
