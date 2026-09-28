"""End-to-end smoke demo against the real LLM.

Reads the synthetic agreement and statement in data/synthetic/, runs both
extraction chains for real, and prints the resulting compliance evaluation.

Requires OPENAI_API_KEY (see .env.example). The test suite does NOT need
this script or a real key — it injects a fake model instead.

Usage:
    python scripts/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.compliance import evaluate_covenant  # noqa: E402
from app.extraction.covenant_chain import extract_covenants  # noqa: E402
from app.extraction.financials_chain import extract_financial_figures  # noqa: E402
from data.synthetic.sample_agreement import AGREEMENT_PAGES  # noqa: E402
from data.synthetic.sample_statement import PERIOD_LABEL, STATEMENT_TEXT  # noqa: E402


def main() -> None:
    document_text = "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in AGREEMENT_PAGES)

    print(f"Extracting covenants from a {len(AGREEMENT_PAGES)}-page synthetic agreement...\n")
    extraction = extract_covenants(document_text)

    print(f"Borrower: {extraction.borrower_name}")
    print(f"Principal: R$ {extraction.principal:,.2f}" if extraction.principal else "Principal: (not extracted)")
    print(f"Instrument: {extraction.instrument_type}")
    print(f"Covenants found: {len(extraction.covenants)}\n")

    if not extraction.covenants:
        print("No covenants extracted — nothing to test against the statement.")
        return

    active_metrics = sorted({c.metric for c in extraction.covenants})
    print(f"Extracting {active_metrics} from the {PERIOD_LABEL} statement...\n")
    figures = extract_financial_figures(STATEMENT_TEXT, active_metrics).as_dict()

    print(f"{'Covenant':35} {'Actual':>10} {'Threshold':>10} {'Headroom':>10}  Status")
    print("-" * 90)
    for c in extraction.covenants:
        if c.metric not in figures:
            print(f"{c.name:35} (no matching figure extracted from the statement)")
            continue
        actual = figures[c.metric]
        result = evaluate_covenant(c.operator, c.threshold, actual)
        print(
            f"{c.name:35} {actual:>10.2f} {c.threshold:>10.2f} "
            f"{result.headroom_pct:>9.1f}%  {result.status.upper()}"
        )


if __name__ == "__main__":
    main()
