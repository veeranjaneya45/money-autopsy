from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class DatasetStats(BaseModel):
    merchants: int
    orders: int
    payments: int
    refunds: int
    fees: int
    settlements: int
    bank_transactions: int
    ledger_entries: int
    cases: int
    ground_truth_cases: int


class HumanReviewRequest(BaseModel):
    decision: str
    reason: str
    reviewer: str