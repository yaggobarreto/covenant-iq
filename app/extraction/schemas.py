"""Pydantic models the LLM's structured output is bound to.

These are deliberately narrow (a fixed `Literal` set of metrics/operators)
rather than free-form strings — a covenant the model can't classify into one
of these buckets fails extraction loudly, instead of silently producing a
value the compliance engine can't test later.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CovenantMetric = Literal[
    "net_debt_ebitda",
    "dscr",
    "min_liquidity",
    "min_equity",
    "current_ratio",
]

CovenantOperator = Literal["lte", "gte"]
TestFrequency = Literal["quarterly", "annual"]


class ExtractedCovenant(BaseModel):
    name: str = Field(description="Short human-readable name, e.g. 'Net Debt / EBITDA'.")
    metric: CovenantMetric
    operator: CovenantOperator = Field(
        description="'lte' if the actual value must stay at or below the threshold, "
        "'gte' if it must stay at or above it."
    )
    threshold: float
    test_frequency: TestFrequency
    cure_period_days: int | None = Field(
        default=None, description="Grace period to cure a breach, in days, if the agreement grants one."
    )
    source_clause: str = Field(description="The verbatim clause this covenant was extracted from.")
    source_page: int | None = Field(default=None, description="1-indexed page number the clause appears on.")


class CovenantExtractionResult(BaseModel):
    borrower_name: str
    principal: float | None = None
    interest_rate: float | None = Field(default=None, description="Annual rate as a percentage, e.g. 12.5.")
    maturity_date: str | None = Field(default=None, description="ISO date (YYYY-MM-DD) if stated.")
    instrument_type: str | None = Field(
        default=None, description="e.g. 'term_loan', 'revolving_facility', 'debenture'."
    )
    covenants: list[ExtractedCovenant] = Field(default_factory=list)


class FinancialFigures(BaseModel):
    """Output of the second extraction pass: the specific figures a loan's
    active covenants need, pulled from one financial statement.

    Fixed, optional named fields rather than a dynamic dict — an LLM's
    structured-output mode binds far more reliably to a known set of fields
    than to an open-ended mapping, and this mirrors the one metric per
    covenant type contract the compliance engine expects.
    """

    period_label: str = Field(description="e.g. '2026-Q2'.")
    net_debt_ebitda: float | None = None
    dscr: float | None = None
    min_liquidity: float | None = None
    min_equity: float | None = None
    current_ratio: float | None = None

    def as_dict(self) -> dict[str, float]:
        """The extracted metrics as {metric_name: value}, omitting any the
        statement didn't support."""
        data = self.model_dump(exclude={"period_label"})
        return {k: v for k, v in data.items() if v is not None}
