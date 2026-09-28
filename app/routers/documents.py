from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.compliance import detect_trend, evaluate_covenant
from app.extraction.financials_chain import extract_financial_figures
from app.models import ComplianceResult, FinancialSnapshot, Loan
from app.schemas import ComplianceResultOut, StatementSubmission

router = APIRouter(prefix="/loans", tags=["statements"])


@router.post("/{loan_id}/statements", response_model=list[ComplianceResultOut], status_code=201)
def submit_statement(loan_id: str, payload: StatementSubmission, db: Session = Depends(get_db)):
    """Ingest one period's financial statement, extract only the figures the
    loan's covenants need, and compute a fresh, immutable compliance result
    for each one — never overwriting history, only appending to it.
    """
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    active_metrics = sorted({c.metric for c in loan.covenants})
    if not active_metrics:
        raise HTTPException(status_code=400, detail="Loan has no covenants to test against.")

    extraction = extract_financial_figures(payload.text, active_metrics)
    figures = extraction.as_dict()

    snapshot = FinancialSnapshot(
        loan_id=loan.id,
        period_label=payload.period_label,
        figures=figures,
        source_reference=payload.period_label,
    )
    db.add(snapshot)
    db.flush()

    results: list[ComplianceResult] = []
    for covenant in loan.covenants:
        if covenant.metric not in figures:
            continue
        actual = figures[covenant.metric]
        evaluation = evaluate_covenant(covenant.operator, covenant.threshold, actual)

        history = (
            db.query(ComplianceResult)
            .filter(ComplianceResult.covenant_id == covenant.id)
            .order_by(ComplianceResult.computed_at)
            .all()
        )
        headroom_history = [r.headroom_pct for r in history] + [evaluation.headroom_pct]
        trend = detect_trend(headroom_history)

        result = ComplianceResult(
            covenant_id=covenant.id,
            snapshot_id=snapshot.id,
            actual_value=evaluation.actual_value,
            headroom_pct=evaluation.headroom_pct,
            status=evaluation.status,
            trend=trend,
        )
        db.add(result)
        results.append(result)

    db.commit()
    for r in results:
        db.refresh(r)
    return results
