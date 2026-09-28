"""The compliance engine: pure functions, no I/O, no LLM.

This is deliberately the most boring code in the repository — covenant
compliance math has one right answer, and the value of an LLM pipeline
upstream depends entirely on this part being trustworthy and exhaustively
tested (see tests/test_compliance_engine.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import settings

ComplianceStatus = Literal["compliant", "warning", "breach"]
Trend = Literal["improving", "stable", "shrinking"]


class InvalidCovenantError(ValueError):
    pass


@dataclass(frozen=True)
class ComplianceEvaluation:
    actual_value: float
    headroom_pct: float
    status: ComplianceStatus


def evaluate_covenant(
    operator: str,
    threshold: float,
    actual_value: float,
    warning_headroom_pct: float | None = None,
) -> ComplianceEvaluation:
    """Compute headroom and status for one covenant test.

    Headroom is signed and expressed as a percentage of the threshold, so
    it's comparable across covenants with completely different scales (a
    3.00x leverage cap and a R$2M liquidity floor both reduce to a plain
    percentage): positive means the actual value has that much room left
    before it would breach; negative means it has already breached by that
    magnitude.
    """
    if operator not in ("lte", "gte"):
        raise InvalidCovenantError(f"Unknown operator: {operator!r}")

    warning_pct = settings.early_warning_headroom_pct if warning_headroom_pct is None else warning_headroom_pct

    if threshold == 0:
        # A percentage-of-threshold headroom is undefined at zero. Fall back
        # to a binary reading — callers that need the exact magnitude for a
        # zero-threshold covenant should treat this as a known limitation,
        # not silently trust the number.
        is_compliant = actual_value <= 0 if operator == "lte" else actual_value >= 0
        headroom_pct = 100.0 if is_compliant else -100.0
    elif operator == "lte":
        headroom_pct = (threshold - actual_value) / abs(threshold) * 100.0
    else:  # gte
        headroom_pct = (actual_value - threshold) / abs(threshold) * 100.0

    # Round once, up front, and base the status decision on that same
    # rounded value. Deciding on the raw float first and rounding only for
    # display can make a value that *displays* as exactly the warning
    # boundary (e.g. 10.0) get classified using an unrounded neighbor like
    # 9.999999999999998 — a real float-precision trap on exact-boundary
    # inputs, not a hypothetical one.
    headroom_pct = round(headroom_pct, 4)

    if headroom_pct < 0:
        status: ComplianceStatus = "breach"
    elif headroom_pct < warning_pct:
        status = "warning"
    else:
        status = "compliant"

    return ComplianceEvaluation(actual_value=actual_value, headroom_pct=headroom_pct, status=status)


def detect_trend(headroom_history: list[float], window: int | None = None) -> Trend | None:
    """Classify the direction of the last `window` headroom readings
    (oldest first). Returns None when there isn't enough history yet to say
    anything — the engine should never report a trend it can't support.
    """
    w = settings.trend_window if window is None else window
    recent = headroom_history[-w:]
    if len(recent) < 2:
        return None

    diffs = [b - a for a, b in zip(recent, recent[1:])]
    if all(d < 0 for d in diffs):
        return "shrinking"
    if all(d > 0 for d in diffs):
        return "improving"
    return "stable"
