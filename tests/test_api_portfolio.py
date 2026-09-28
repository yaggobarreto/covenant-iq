from __future__ import annotations

import app.routers.documents as documents_router
import app.routers.loans as loans_router
from app.extraction.schemas import CovenantExtractionResult, ExtractedCovenant, FinancialFigures


def test_portfolio_summary_on_an_empty_portfolio(client):
    response = client.get("/portfolio/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_loans": 0,
        "total_exposure": 0.0,
        "covenant_status_counts": {"compliant": 0, "warning": 0, "breach": 0},
    }


def test_portfolio_summary_counts_latest_status_per_covenant(client, monkeypatch):
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
    loan = client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()

    monkeypatch.setattr(
        documents_router,
        "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T3", dscr=1.09),
    )
    client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T3", "text": "x"})

    response = client.get("/portfolio/summary")

    body = response.json()
    assert body["total_loans"] == 1
    assert body["total_exposure"] == 8_200_000.0
    assert body["covenant_status_counts"]["breach"] == 1


def test_portfolio_summary_only_counts_each_covenants_latest_result(client, monkeypatch):
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
    loan = client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()

    # First snapshot: compliant. Second snapshot: breach. Only the second
    # should count in the portfolio summary.
    monkeypatch.setattr(
        documents_router, "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T2", dscr=1.60),
    )
    client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T2", "text": "x"})

    monkeypatch.setattr(
        documents_router, "extract_financial_figures",
        lambda text, metrics: FinancialFigures(period_label="2026-T3", dscr=1.09),
    )
    client.post(f"/loans/{loan['id']}/statements", json={"period_label": "2026-T3", "text": "x"})

    counts = client.get("/portfolio/summary").json()["covenant_status_counts"]
    assert counts == {"compliant": 0, "warning": 0, "breach": 1}
