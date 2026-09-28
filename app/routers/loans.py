from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.extraction.covenant_chain import extract_covenants
from app.models import Covenant, DocumentChunk, Loan
from app.retrieval.embeddings import embed_text
from app.schemas import AgreementSubmission, CovenantOut, LoanOut

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanOut, status_code=201)
def create_loan_from_agreement(payload: AgreementSubmission, db: Session = Depends(get_db)) -> Loan:
    """Ingest a credit agreement: extract the borrower, terms, and every
    covenant, and index the document text for the portfolio chat.

    Every extracted covenant starts with `reviewed=False` — see
    PATCH /loans/{id}/covenants/{id}/review. Nothing here goes live
    unreviewed; this mirrors the human-in-the-loop design in the whitepaper.
    """
    document_text = "\n\n".join(f"[Page {p.page}]\n{p.text}" for p in payload.pages)
    extraction = extract_covenants(document_text)

    loan = Loan(
        borrower_name=extraction.borrower_name,
        principal=extraction.principal or payload.principal_hint or 0.0,
        interest_rate=extraction.interest_rate,
        maturity_date=extraction.maturity_date,
        instrument_type=extraction.instrument_type,
    )
    for c in extraction.covenants:
        loan.covenants.append(
            Covenant(
                name=c.name,
                metric=c.metric,
                operator=c.operator,
                threshold=c.threshold,
                test_frequency=c.test_frequency,
                cure_period_days=c.cure_period_days,
                source_clause=c.source_clause,
                source_page=c.source_page,
                reviewed=False,
            )
        )

    db.add(loan)
    db.flush()  # assigns loan.id before the chunks below reference it

    for p in payload.pages:
        db.add(DocumentChunk(loan_id=loan.id, page=p.page, text=p.text, embedding=embed_text(p.text)))

    db.commit()
    db.refresh(loan)
    return loan


@router.get("", response_model=list[LoanOut])
def list_loans(db: Session = Depends(get_db)) -> list[Loan]:
    return db.query(Loan).all()


@router.get("/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: str, db: Session = Depends(get_db)) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.patch("/{loan_id}/covenants/{covenant_id}/review", response_model=CovenantOut)
def review_covenant(loan_id: str, covenant_id: str, db: Session = Depends(get_db)) -> Covenant:
    covenant = db.get(Covenant, covenant_id)
    if covenant is None or covenant.loan_id != loan_id:
        raise HTTPException(status_code=404, detail="Covenant not found")
    covenant.reviewed = True
    db.commit()
    db.refresh(covenant)
    return covenant
