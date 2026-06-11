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


# ── Relocation Simulator ──────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    neighbourhood_id: int
    budget:           int            # student's monthly rent budget
    university_id:    int | None = None


class CostBreakdown(BaseModel):
    rent:          int
    generator:     int
    water:         int
    internet:      int
    transport:     int
    total_monthly: int


class AreaScores(BaseModel):
    electricity_hours:       float | None
    electricity_reliability: float
    generator_cost:          int | None
    internet:                int | None
    transport:               int | None
    safety:                  int | None
    student_vibe:            int | None
    livability_score:        float
    student_score:           float


class SimulateOut(BaseModel):
    neighbourhood_name:    str
    neighbourhood_name_ar: str | None
    area_scores:           AreaScores
    cost_breakdown:        CostBreakdown
    commute_minutes:       int | None
    fit_score:             float       # 0–1
    electricity_label:     str         # e.g. "12h EDL · 12h generator"
    budget_feasibility:    str         # "comfortable" / "tight" / "over budget"
