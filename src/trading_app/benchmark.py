"""The benchmark question: measure trading against the ETF, and say so (T5, T6).

This module exists because of an asymmetry. Bailey & López de Prado's
MinTRL says that proving an active Sharpe of −0.50 at 95 % confidence takes
148 months; the shortfall against simply holding the ETF passes −15 % of
trading capital inside 24. The statistical gate the app uses to *admit* a
strategy (G7, 95 %) is calibrated so that false positives cost money on a
fiction. Retiring a live strategy runs the other way: the cost of waiting
is measured, real and compounding.

The ladder therefore lowers its evidence bar as the accumulated cost rises
— warn at 12 months, halve at 18 with 70 % confidence, stop at 24 with
80 % — and states the confidence level out loud at every rung, including
the fact that it is below 95 % and why.

Two properties matter as much as the thresholds. The directive is not
softened by a good final month inside a losing window, and the review runs
on a schedule rather than on request, because a warning you have to ask for
is one you can avoid by not asking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum, auto
from statistics import NormalDist
from typing import Final

__all__ = [
    "BenchmarkReview",
    "Confidence",
    "ReviewDue",
    "ReviewResult",
    "Rung",
    "mintrl_months",
    "review",
    "shortfall_after",
]

_ND: Final = NormalDist()

# Non-normality of monthly active returns, from the calculation-core
# specification (T9). Carried here rather than assumed normal: the fat
# tails lengthen the required track record, which strengthens the argument
# for not waiting for 95 %.
_SKEW: Final = -0.72
_KURT: Final = 5.78

# T5.1. Active volatility used for the cost-of-waiting table.
_ACTIVE_VOL: Final = 0.15

# T5.2, ENTSCHEIDUNG. The second stop trigger, independent of any window.
_SHORTFALL_STOP: Final = Decimal("-0.15")


class Rung(StrEnum):
    REPORT = auto()
    WARN = auto()
    HALVE = auto()
    STOP = auto()


class Confidence:
    """Confidence attached to each rung (T5.2).

    Not monotonic, and deliberately so. Halve asks 70 %, Stop asks 80 %: the
    bar *rises* with the severity of the directive, because stopping is the
    more drastic instruction. What falls as cost accumulates is the gap to
    the 95 % gate used to admit a strategy — every rung here sits below it.

    Warn carries no confidence level at all. It names a measured shortfall in
    euros and forbids adding size; that is an arithmetic fact about money
    already lost, not a statistical claim about the edge.
    """

    _LEVELS: Final[dict[Rung, Decimal | None]] = {
        Rung.REPORT: None,
        Rung.WARN: None,
        Rung.HALVE: Decimal("0.70"),
        Rung.STOP: Decimal("0.80"),
    }

    @classmethod
    def for_rung(cls, rung: Rung) -> Decimal | None:
        return cls._LEVELS[rung]


class ReviewDue:
    """T5.3. The schedule, not the user, decides when this runs."""

    @staticmethod
    def monthly(*, last_review_month: int, current_month: int) -> bool:
        return current_month > last_review_month


@dataclass(frozen=True, slots=True)
class BenchmarkReview:
    """Trading measured against L1, already net of costs and German tax (T6).

    ``cumulative_shortfall_pct`` is signed: negative means trading has cost
    money relative to holding the ETF.
    """

    active_sharpe: Decimal
    months: int
    cumulative_shortfall_pct: Decimal
    cumulative_shortfall_eur: Decimal
    trading_capital_eur: Decimal
    last_month_positive: bool


@dataclass(frozen=True, slots=True)
class ReviewResult:
    rung: Rung
    text: str
    directive: str
    confidence: Decimal | None


def mintrl_months(sr_annual: float, alpha: float) -> float:
    """Minimum track record length in months, Bailey & López de Prado (2012)
    Eq. 13, against SR* = 0.

    Takes the *magnitude* of the Sharpe ratio. The sign convention is a real
    choice, not a detail: feeding a negative Sharpe straight into the skew
    term mirrors the distribution and yields 121 months at −0.50 instead of
    148, because a left-tailed series makes a *negative* claim look easier to
    establish. The specification table (T5.1) and the calculation core's
    pinned T9 value both use the magnitude, which is also the conservative
    reading — fat tails should lengthen the record required before the coach
    tells the user to stop trading, not shorten it.

    Kept in ``src`` rather than in a test file because T5's whole argument
    rests on this number being large.
    """
    sr = abs(sr_annual) / math.sqrt(12)
    z = _ND.inv_cdf(1 - alpha)
    return 1 + (1 - _SKEW * sr + ((_KURT - 1) / 4) * sr**2) * (z / sr) ** 2


def shortfall_after(months: float) -> float:
    """Expected cumulative shortfall at an active Sharpe of −0.50 and 15 %
    active volatility — the cost of waiting for certainty."""
    return -0.50 * _ACTIVE_VOL * (months / 12)


def _rung_for(data: BenchmarkReview) -> Rung:
    """The ladder. Evaluated worst-first: a shortfall past the ENTSCHEIDUNG
    threshold stops trading at any horizon, however short."""
    if data.cumulative_shortfall_pct <= _SHORTFALL_STOP:
        return Rung.STOP
    if data.active_sharpe >= 0:
        return Rung.REPORT
    if data.months >= 24:
        return Rung.STOP
    if data.months >= 18:
        return Rung.HALVE
    if data.months >= 12:
        return Rung.WARN
    return Rung.REPORT


def _confidence_clause(rung: Rung) -> str:
    level = Confidence.for_rung(rung)
    if level is None:
        return ""
    pct = int(level * 100)
    return (
        f" Konfidenz {pct} %, bewusst unter den 95 %, die diese App zur "
        f"Aufnahme einer Strategie verlangt — die Asymmetrie ist gewollt: "
        f"Schweigen kostet hier gemessenes Geld, kein hypothetisches."
    )


def review(
    data: BenchmarkReview,
    *,
    net_of_costs_and_tax: bool = True,
) -> ReviewResult:
    """Run the monthly benchmark review and return the rung reached.

    Refuses gross figures: trading realises gains continuously while a
    buy-and-hold core defers them, so a gross comparison flatters trading
    by exactly the tax it has already paid (T6).
    """
    if not net_of_costs_and_tax:
        raise ValueError(
            "Vergleich nur netto — nach Kosten und nach Steuer (T6). "
            "Brutto schmeichelt dem Handel, weil der Kern seine Gewinne "
            "aufschiebt."
        )

    rung = _rung_for(data)
    confidence = Confidence.for_rung(rung)
    eur = data.cumulative_shortfall_eur
    pct = data.cumulative_shortfall_pct

    if rung is Rung.REPORT:
        text = (
            f"Aktive Rendite gegen L1 nach Kosten und Steuer über "
            f"{data.months} Monate: {eur} EUR ({pct}). "
            f"Das Ergebnis ist noch nicht schlüssig — die Stichprobe ist zu "
            f"kurz für eine Aussage über den Edge."
        )
        directive = "Weiter nach Plan, Ergebnis wird monatlich berichtet."

    elif rung is Rung.WARN:
        text = (
            f"Der Handel liegt seit {data.months} Monaten hinter L1: "
            f"{eur} EUR entgangen ({pct} des Handelskapitals)."
            + _confidence_clause(rung)
        )
        directive = (
            "Keine Erhöhung der Positionsgröße und keine Erhöhung des "
            "Handelskapitals, solange die Zahl negativ bleibt."
        )

    elif rung is Rung.HALVE:
        text = (
            f"Seit {data.months} Monaten negative aktive Sharpe. "
            f"Kumulierter Rückstand {eur} EUR ({pct})."
            + _confidence_clause(rung)
        )
        directive = (
            "Positionsgröße halbieren oder das dem Handel zugeteilte "
            "Kapital halbieren."
        )

    else:
        trigger = (
            f"der kumulierte Rückstand {pct} erreicht die 15-%-Schwelle"
            if pct <= _SHORTFALL_STOP
            else f"seit {data.months} Monaten negative aktive Sharpe"
        )
        text = (
            f"Stopp-Empfehlung: {trigger}. Rückstand {eur} EUR gegenüber "
            f"dem einfachen Halten des ETF."
            + _confidence_clause(rung)
            + " Diese Empfehlung wird nicht zurückgehalten, weil sie "
            "unwillkommen ist, und nicht abgeschwächt, weil der letzte "
            "Monat gut war. Umkehrbar nur über ein neues TPS nach "
            "vollständiger Überprüfung."
        )
        directive = (
            "Diskretionären Handel einstellen, Kapital in den Kern "
            "überführen."
        )

    return ReviewResult(
        rung=rung, text=text, directive=directive, confidence=confidence
    )
