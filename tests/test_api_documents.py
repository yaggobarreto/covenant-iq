from __future__ import annotations

import app.routers.documents as documents_router
import app.routers.loans as loans_router
from app.extraction.schemas import CovenantExtractionResult, ExtractedCovenant, FinancialFigures


def _create_loan_with_one_covenant(client, monkeypatch):
    extraction = CovenantExtractionResult(
        borrower_name="Aurora Indústria e Comércio Ltda.",
        principal=8_200_000.0,
        covenants=[
            ExtractedCovenant(
                name="DSCR",
                metric="dscr",
                operator="gte",
                threshold=1.20,
                test_frequency="quarterly",
                cure_period_days=30,
                source_clause="...",
                source_page=2,
            )
        ],
    )
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: extraction)
    return client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()


def test_submit_statement_computes_and_persists_compliance(client, monkeypatch):
    loan = _create_loan_with_one_covenant(client, monkeypatch)

    monkeypatch.setattr(
        documents_router,
        "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T3", dscr=1.09),
    )

    response = client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T3", "text": "..."})

    assert response.status_code == 201
    results = response.json()
    assert len(results) == 1
    assert results[0]["actual_value"] == 1.09
    assert results[0]["status"] == "breach"
    assert results[0]["trend"] is None  # only one snapshot so far — nothing to trend yet


def test_second_statement_produces_a_trend(client, monkeypatch):
    loan = _create_loan_with_one_covenant(client, monkeypatch)

    monkeypatch.setattr(
        documents_router,
        "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T2", dscr=1.40),
    )
    client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T2", "text": "..."})

    monkeypatch.setattr(
        documents_router,
        "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T3", dscr=1.09),
    )
    response = client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T3", "text": "..."})

    results = response.json()
    assert results[0]["status"] == "breach"
    assert results[0]["trend"] == "shrinking"


def test_submit_statement_skips_metrics_the_statement_does_not_cover(client, monkeypatch):
    loan = _create_loan_with_one_covenant(client, monkeypatch)

    monkeypatch.setattr(
        documents_router,
        "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T3"),  # dscr missing
    )

    response = client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T3", "text": "..."})

    assert response.status_code == 201
    assert response.json() == []


def test_submit_statement_for_loan_without_covenants_is_rejected(client, monkeypatch):
    monkeypatch.setattr(
        loans_router,
        "extract_covenants",
        lambda text: CovenantExtractionResult(borrower_name="No Covenants Ltda.", covenants=[]),
    )
    loan = client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()

    response = client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T1", "text": "x"})

    assert response.status_code == 400


def test_submit_statement_for_missing_loan_returns_404(client):
    response = client.post("/loans/does-not-exist/statements", json={"period_label": "2026-T1", "text": "x"})
    assert response.status_code == 404
