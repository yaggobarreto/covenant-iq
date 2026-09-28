"""Pydantic request/response models for the HTTP API — kept separate from
app/extraction/schemas.py, which shapes what the LLM returns, not what the
API exposes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgreementPage(BaseModel):
    page: int
    text: str


class AgreementSubmission(BaseModel):
    pages: list[AgreementPage] = Field(min_length=1)
    principal_hint: float | None = Field(
        default=None, description="Used only if the agreement text itself doesn't state a principal."
    )


class CovenantOut(BaseModel):
    id: str
    name: str
    metric: str
    operator: str
    threshold: float
    test_frequency: str
    cure_period_days: int | None
    source_clause: str | None
    source_page: int | None
    reviewed: bool

    model_config = {"from_attributes": True}


class LoanOut(BaseModel):
    id: str
    borrower_name: str
    sector: str | None
    principal: float
    interest_rate: float | None
    maturity_date: str | None
    instrument_type: str | None
    status: str
    covenants: list[CovenantOut] = []

    model_config = {"from_attributes": True}


class StatementSubmission(BaseModel):
    period_label: str
    text: str


class ComplianceResultOut(BaseModel):
    id: str
    covenant_id: str
    snapshot_id: str
    actual_value: float
    headroom_pct: float
    status: str
    trend: str | None

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    question: str


class ChatSourceOut(BaseModel):
    loan_id: str
    page: int
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSourceOut]


class PortfolioSummary(BaseModel):
    total_loans: int
    total_exposure: float
    covenant_status_counts: dict[str, int]
