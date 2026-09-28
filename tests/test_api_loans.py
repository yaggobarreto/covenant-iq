from __future__ import annotations

import app.routers.loans as loans_router
from app.extraction.schemas import CovenantExtractionResult, ExtractedCovenant


def _canned_extraction(covenants: list[ExtractedCovenant] | None = None) -> CovenantExtractionResult:
    return CovenantExtractionResult(
        borrower_name="Aurora Indústria e Comércio Ltda.",
        principal=8_200_000.0,
        interest_rate=14.5,
        maturity_date="2029-06-30",
        instrument_type="term_loan",
        covenants=covenants
        if covenants is not None
        else [
            ExtractedCovenant(
                name="Net Debt / EBITDA",
                metric="net_debt_ebitda",
                operator="lte",
                threshold=3.0,
                test_frequency="quarterly",
                cure_period_days=None,
                source_clause="...",
                source_page=2,
            ),
            ExtractedCovenant(
                name="DSCR",
                metric="dscr",
                operator="gte",
                threshold=1.20,
                test_frequency="quarterly",
                cure_period_days=30,
                source_clause="...",
                source_page=2,
            ),
        ],
    )


def test_create_loan_extracts_and_persists_covenants_unreviewed(client, monkeypatch):
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: _canned_extraction())

    response = client.post(
        "/loans",
        json={"pages": [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["borrower_name"] == "Aurora Indústria e Comércio Ltda."
    assert body["principal"] == 8_200_000.0
    assert len(body["covenants"]) == 2
    assert all(c["reviewed"] is False for c in body["covenants"])


def test_create_loan_falls_back_to_principal_hint_when_not_extracted(client, monkeypatch):
    extraction_without_principal = _canned_extraction(covenants=[])
    extraction_without_principal.principal = None
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: extraction_without_principal)

    response = client.post(
        "/loans",
        json={"pages": [{"page": 1, "text": "..."}], "principal_hint": 1_000_000.0},
    )

    assert response.status_code == 201
    assert response.json()["principal"] == 1_000_000.0


def test_review_covenant_marks_it_reviewed(client, monkeypatch):
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: _canned_extraction())
    created = client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()
    loan_id = created["id"]
    covenant_id = created["covenants"][0]["id"]

    response = client.patch(f"/loans/{loan_id}/covenants/{covenant_id}/review")

    assert response.status_code == 200
    assert response.json()["reviewed"] is True


def test_review_unknown_covenant_returns_404(client, monkeypatch):
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: _canned_extraction())
    loan = client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]}).json()

    response = client.patch(f"/loans/{loan['id']}/covenants/does-not-exist/review")

    assert response.status_code == 404


def test_get_missing_loan_returns_404(client):
    assert client.get("/loans/does-not-exist").status_code == 404


def test_list_loans_returns_created_loans(client, monkeypatch):
    monkeypatch.setattr(loans_router, "extract_covenants", lambda text: _canned_extraction())
    client.post("/loans", json={"pages": [{"page": 1, "text": "x"}]})
    client.post("/loans", json={"pages": [{"page": 1, "text": "y"}]})

    response = client.get("/loans")

    assert response.status_code == 200
    assert len(response.json()) == 2
