"""These tests never touch a real LLM: `build_covenant_chain` /
`build_financials_chain` are monkeypatched to return a FakeInvokable, so
what's actually under test is the wrapper logic around the chain — that
inputs are passed through correctly and results are normalized — not model
behavior.
"""

from __future__ import annotations

from app.extraction import covenant_chain, financials_chain
from app.extraction.schemas import CovenantExtractionResult, ExtractedCovenant, FinancialFigures
from tests.fakes import FakeInvokable


def _sample_covenant() -> ExtractedCovenant:
    return ExtractedCovenant(
        name="Net Debt / EBITDA",
        metric="net_debt_ebitda",
        operator="lte",
        threshold=3.0,
        test_frequency="quarterly",
        cure_period_days=None,
        source_clause="A Devedora obriga-se a manter Dívida Líquida/EBITDA <= 3,00x.",
        source_page=2,
    )


def test_extract_covenants_invokes_the_chain_with_the_document_text(monkeypatch):
    canned = CovenantExtractionResult(
        borrower_name="Aurora Indústria e Comércio Ltda.",
        principal=8_200_000.0,
        interest_rate=14.5,
        maturity_date="2029-06-30",
        instrument_type="term_loan",
        covenants=[_sample_covenant()],
    )
    fake_chain = FakeInvokable(canned)
    monkeypatch.setattr(covenant_chain, "build_covenant_chain", lambda llm: fake_chain)

    result = covenant_chain.extract_covenants("some agreement text", llm=object())

    assert result is canned
    assert fake_chain.last_inputs == {"document_text": "some agreement text"}


def test_extract_covenants_normalizes_a_plain_dict_result(monkeypatch):
    """Some chat models hand back a dict instead of the Pydantic model when
    structured output isn't natively supported — the wrapper should still
    return a validated CovenantExtractionResult, not the raw dict."""
    raw = {"borrower_name": "Aurora Indústria e Comércio Ltda.", "covenants": []}
    fake_chain = FakeInvokable(raw)
    monkeypatch.setattr(covenant_chain, "build_covenant_chain", lambda llm: fake_chain)

    result = covenant_chain.extract_covenants("text", llm=object())

    assert isinstance(result, CovenantExtractionResult)
    assert result.borrower_name == "Aurora Indústria e Comércio Ltda."
    assert result.covenants == []


def test_extract_financial_figures_passes_active_metrics_into_the_prompt(monkeypatch):
    canned = FinancialFigures(period_label="2026-T3", dscr=1.09, net_debt_ebitda=2.41)
    fake_chain = FakeInvokable(canned)
    monkeypatch.setattr(financials_chain, "build_financials_chain", lambda llm: fake_chain)

    result = financials_chain.extract_financial_figures("statement text", ["dscr", "net_debt_ebitda"], llm=object())

    assert result is canned
    assert fake_chain.last_inputs == {
        "statement_text": "statement text",
        "active_metrics": "dscr, net_debt_ebitda",
    }
    assert result.as_dict() == {"dscr": 1.09, "net_debt_ebitda": 2.41}


def test_financial_figures_as_dict_omits_unset_metrics():
    figures = FinancialFigures(period_label="2026-T3", dscr=1.09)
    assert figures.as_dict() == {"dscr": 1.09}
