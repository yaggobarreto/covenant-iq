from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ComplianceResult, Loan
from app.schemas import PortfolioSummary

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)) -> PortfolioSummary:
    """Latest compliance status per covenant, rolled up into portfolio counts."""
    latest_per_covenant = (
        db.query(ComplianceResult.covenant_id, func.max(ComplianceResult.computed_at).label("latest"))
        .group_by(ComplianceResult.covenant_id)
        .subquery()
    )
    latest_results = (
        db.query(ComplianceResult)
        .join(
            latest_per_covenant,
            (ComplianceResult.covenant_id == latest_per_covenant.c.covenant_id)
            & (ComplianceResult.computed_at == latest_per_covenant.c.latest),
        )
        .all()
    )

    counts: dict[str, int] = {"compliant": 0, "warning": 0, "breach": 0}
    for r in latest_results:
        counts[r.status] = counts.get(r.status, 0) + 1

    total_exposure = db.query(func.coalesce(func.sum(Loan.principal), 0.0)).scalar() or 0.0

    return PortfolioSummary(
        total_loans=db.query(Loan).count(),
        total_exposure=float(total_exposure),
        covenant_status_counts=counts,
    )
