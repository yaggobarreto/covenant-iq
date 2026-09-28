"""The compliance engine is pure logic, so it gets the most exhaustive
coverage in the suite — everything downstream trusts these numbers.

The three main scenarios mirror the worked examples in docs/whitepaper.pdf
§5 and the "Loans requiring attention" table in docs/dashboard.png, so the
documentation and the tested behavior are provably the same thing.
"""

from __future__ import annotations

import pytest

from app.engine.compliance import InvalidCovenantError, detect_trend, evaluate_covenant


def test_leverage_covenant_compliant_with_headroom():
    # Net Debt / EBITDA <= 3.00x, actual 2.41x — whitepaper §5 example 1.
    result = evaluate_covenant("lte", threshold=3.00, actual_value=2.41)
    assert result.status == "compliant"
    assert result.headroom_pct == pytest.approx(19.6667, rel=1e-3)


def test_liquidity_covenant_is_early_warning_not_yet_a_breach():
    # Min. Liquidity >= R$2.0M, actual R$2.18M — whitepaper §5 example 2:
    # technically compliant, but inside the warning band.
    result = evaluate_covenant("gte", threshold=2_000_000.0, actual_value=2_180_000.0)
    assert result.status == "warning"
    assert result.headroom_pct == pytest.approx(9.0)


def test_dscr_covenant_breach_matches_dashboard_example():
    # DSCR >= 1.20x, actual 1.09x — the "Aurora Indústria Ltda" row in
    # docs/dashboard.png (Breach, headroom -9%).
    result = evaluate_covenant("gte", threshold=1.20, actual_value=1.09)
    assert result.status == "breach"
    assert result.headroom_pct == pytest.approx(-9.1667, rel=1e-3)


def test_lte_breach_when_actual_exceeds_threshold():
    result = evaluate_covenant("lte", threshold=3.0, actual_value=3.3)
    assert result.status == "breach"
    assert result.headroom_pct < 0


def test_custom_warning_band_widens_what_counts_as_warning():
    # 10% headroom is "compliant" under the 10% default, but "warning" under
    # a stricter, explicitly-passed 15% band.
    default = evaluate_covenant("lte", threshold=3.0, actual_value=2.70)
    stricter = evaluate_covenant("lte", threshold=3.0, actual_value=2.70, warning_headroom_pct=15.0)
    assert default.status == "compliant"
    assert stricter.status == "warning"


def test_zero_threshold_lte_falls_back_to_binary_reading():
    compliant = evaluate_covenant("lte", threshold=0.0, actual_value=-5.0)
    breached = evaluate_covenant("lte", threshold=0.0, actual_value=5.0)
    assert (compliant.status, compliant.headroom_pct) == ("compliant", 100.0)
    assert (breached.status, breached.headroom_pct) == ("breach", -100.0)


def test_zero_threshold_gte_falls_back_to_binary_reading():
    compliant = evaluate_covenant("gte", threshold=0.0, actual_value=1.0)
    breached = evaluate_covenant("gte", threshold=0.0, actual_value=-1.0)
    assert compliant.status == "compliant"
    assert breached.status == "breach"


def test_invalid_operator_raises():
    with pytest.raises(InvalidCovenantError):
        evaluate_covenant("eq", threshold=1.0, actual_value=1.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("history", [[], [12.5]])
def test_detect_trend_needs_at_least_two_points(history):
    assert detect_trend(history) is None


def test_detect_trend_shrinking_matches_bellwood_example():
    # docs/dashboard.png's "Headroom trend — Bellwood Logística" chart:
    # six quarters of steadily shrinking headroom.
    history = [28.0, 22.0, 14.0, 6.0, 3.0, -9.0]
    assert detect_trend(history) == "shrinking"


def test_detect_trend_improving():
    assert detect_trend([5.0, 12.0, 20.0]) == "improving"


def test_detect_trend_stable_when_direction_is_mixed():
    assert detect_trend([10.0, 15.0, 12.0]) == "stable"


def test_detect_trend_only_looks_at_the_trailing_window():
    history = [30.0, 5.0, 10.0, 20.0]  # not monotonic overall
    assert detect_trend(history, window=2) == "improving"  # last two: 10 -> 20
    assert detect_trend(history, window=4) == "stable"
