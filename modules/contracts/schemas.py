from datetime import datetime

from pydantic import BaseModel


class RiskItem(BaseModel):
    level:       str   # "high" | "medium" | "low"
    clause_text: str
    explanation: str


class ContractAnalysis(BaseModel):
    risk_items: list[RiskItem] = []


class ContractCreateOut(BaseModel):
    contract_id: int
    status:      str


class ContractOut(BaseModel):
    id:         int
    ocr_used:   bool
    status:     str
    analysis:   ContractAnalysis | None
    created_at: datetime

    model_config = {"from_attributes": True}
