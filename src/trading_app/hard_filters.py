"""Hard filters of product selection (investment spec A5.2, evaluation v1.3).

"Yes/no per building block" — with a third outcome. Every check ends as
``fulfilled``, ``violated`` or ``open``:

- **open** if the value is missing at the cut-off date or is UNVERIFIED. A
  second-hand value never lets a filter pass — not even if it *would* pass
  it. But it does not exclude for good either.
- A product is **eligible** only with no violated and no open check.

Why a result and not an exception: an exception would let a single
unchecked value abort the evaluation of all thirty candidates, and whoever
works around it with ``try/except`` lets through exactly what it was meant
to stop. Why not a mere warning: a warning next to a "passed" gets
overlooked, and then a product ends up in the recommendation on the basis of
a second-hand number. The ``open`` verdict is both at once: the product is
not eligible, and the reason says which value is to be checked against the
primary document.

Not here: scoring A5.3, index choice A5.4, product switch A5.6 and filter 7
(savings-plan-eligible at the broker — user data, not master data).

All values come from an ``InstrumentView``; its cut-off date is also the
cut-off date for the history (filter 4) and for the exchange rate that
converts a foreign-currency fund size (filter 3).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact
from enum import StrEnum
from typing import Any

from trading_app.instruments import FieldValue, InstrumentView, VerificationStatus

__all__ = [
    "BuildingBlock",
    "Check",
    "FilterResult",
    "Verdict",
    "check_hard_filters",
    "full_calendar_years",
]


class BuildingBlock(StrEnum):
    """The building blocks from A5.5."""

    K1 = "K1 Global equities"
    K2_MONEY_MARKET = "K2 Money market"
    K2_EUR_GOVERNMENT_BONDS = "K2 EUR government bonds"
    K2_GLOBAL_BONDS = "K2 Global bonds"
    S_GOLD = "S-Gold"
    S_FACTOR = "S-Factor"


class Verdict(StrEnum):
    FULFILLED = "fulfilled"
    VIOLATED = "violated"
    OPEN = "open"


# A5.2 no. 3: 100m € VERIFIZIERT (Lipper 2025); 500m € for K1 and money
# market ENTSCHEIDUNG (a fund closure realises gains).
MIN_FUND_SIZE = Decimal("100000000")
MIN_FUND_SIZE_LARGE = Decimal("500000000")
_LARGE_BLOCKS = frozenset({BuildingBlock.K1, BuildingBlock.K2_MONEY_MARKET})

# A5.2 no. 4.
MIN_CALENDAR_YEARS = 3

# A5.2 no. 2 per A5.5, only where A5.5 names concrete indices (v1.3). Spelling
# exactly as in A5.5 — this is how index_name must appear in the source file.
_INDICES_A5_5 = {
    BuildingBlock.K1: frozenset({"MSCI ACWI", "MSCI ACWI IMI", "FTSE All-World"}),
    BuildingBlock.K2_MONEY_MARKET: frozenset({"€STR"}),
}

_EQUITY_BLOCKS = frozenset({BuildingBlock.K1, BuildingBlock.S_FACTOR})  # no. 5
_FOREIGN_CURRENCY_BONDS = frozenset({BuildingBlock.K2_GLOBAL_BONDS})  # no. 6


@dataclass(frozen=True, slots=True)
class Check:
    """A single check; ``number`` is the number in A5.2."""

    number: int
    name: str
    verdict: Verdict
    reason: str


@dataclass(frozen=True, slots=True)
class FilterResult:
    """All checks of one instrument for one building block at one cut-off date.

    Attributes:
        new: Fewer than three full calendar years (filter 4). Not an
            exclusion but a label for scoring A5.3.
    """

    isin: str
    building_block: BuildingBlock
    cut_off: dt.datetime
    checks: tuple[Check, ...]
    new: bool

    @property
    def verdict(self) -> Verdict:
        """Violated before open before fulfilled."""
        verdicts = {check.verdict for check in self.checks}
        for worst in (Verdict.VIOLATED, Verdict.OPEN):
            if worst in verdicts:
                return worst
        return Verdict.FULFILLED

    @property
    def eligible(self) -> bool:
        return self.verdict is Verdict.FULFILLED


def full_calendar_years(inception_date: dt.date, cut_off: dt.date) -> int:
    """Calendar years lying entirely between inception and cut-off (A5.2 no. 4, v1.3).

    The current year never counts, the inception year only for an inception
    on 1 January. Calendar years, because A5.3 averages the tracking
    difference per calendar year: three full years means three annual values.
    """
    first = inception_date.year + (
        0 if (inception_date.month, inception_date.day) == (1, 1) else 1
    )
    return max(0, cut_off.year - first)


def check_hard_filters(view: InstrumentView, isin: str, block: BuildingBlock) -> FilterResult:
    """Checks A5.2 nos. 1–6 for an instrument as a candidate for a building block.

    Args:
        view: Master data at the cut-off date.
        isin: The instrument.
        block: The building block it is checked for — the filters depend on
            it (size threshold, index, equity fund, currency hedging).

    Returns:
        The result with every single check and its reason.
    """
    block = BuildingBlock(block)
    checks: list[Check] = []

    # No. 1
    if block is BuildingBlock.S_GOLD:
        checks.append(
            _check(view, isin, 1, "ETC with delivery claim", "gold_etc_delivery_claim", _yes)
        )
    else:
        checks.append(_check(view, isin, 1, "UCITS", "ucits", _yes))
    # Not on Xetra is no exclusion: A5.2 permits any German trading venue,
    # which however is not recorded as a field → check by hand.
    checks.append(
        _check(view, isin, 1, "Xetra", "xetra_tradable", _yes, otherwise=Verdict.OPEN)
    )
    checks.append(_check(view, isin, 1, "KID in German", "kid_language_de", _yes))

    # No. 2
    indices = _INDICES_A5_5.get(block)
    if indices is None:
        checks.append(
            Check(
                2,
                "Index",
                Verdict.OPEN,
                f"A5.5 names only an index family for {block}; check by hand "
                "until A5.5 names concrete indices",
            )
        )
    else:
        checks.append(
            _check(
                view, isin, 2, "Index", "index_name", indices.__contains__,
                rule=f"one of {sorted(indices)}",
            )
        )

    # No. 3
    checks.append(_check_fund_size(view, isin, block))

    # No. 4
    history, new = _check_history(view, isin)
    checks.append(history)

    # No. 5
    if block in _EQUITY_BLOCKS:
        checks.append(
            _check(view, isin, 5, "Equity fund (§ 2 Abs. 6 InvStG)", "equity_fund_invstg", _yes)
        )

    # No. 6
    if block in _FOREIGN_CURRENCY_BONDS:
        checks.append(_check(view, isin, 6, "EUR-hedged", "currency_hedged", _yes))

    return FilterResult(isin, block, view.cut_off, tuple(checks), new)


def _yes(value: Any) -> bool:
    return value is True


def _verified_value(
    view: InstrumentView, isin: str, number: int, name: str, field: str
) -> tuple[FieldValue | None, Check | None]:
    """The value, or an open check if it is missing or unverified."""
    value = view.field(isin, field)
    if value is None:
        return None, Check(
            number, name, Verdict.OPEN, f"{field}: no value known at the cut-off date"
        )
    if value.status is not VerificationStatus.VERIFIED:
        return None, Check(
            number,
            name,
            Verdict.OPEN,
            f"{field} = {value.value} is {value.status} ({value.source_type}, "
            f"{value.source_url}); counts only after reconciliation with the primary document",
        )
    return value, None


def _check(
    view: InstrumentView,
    isin: str,
    number: int,
    name: str,
    field: str,
    condition: Callable[[Any], bool],
    *,
    rule: str = "yes",
    otherwise: Verdict = Verdict.VIOLATED,
) -> Check:
    value, open_check = _verified_value(view, isin, number, name, field)
    if open_check is not None:
        return open_check
    verdict = Verdict.FULFILLED if condition(value.value) else otherwise
    return Check(
        number,
        name,
        verdict,
        f"{field} = {value.value}, required {rule} ({value.source_type}, as of {value.as_of})",
    )


def _check_fund_size(view: InstrumentView, isin: str, block: BuildingBlock) -> Check:
    """A5.2 no. 3: thresholds in EUR, a foreign fund size at its own as-of rate (A5.1).

    The ECB rate of the value's own as-of date, never today's — otherwise a
    stored fund size would change on every re-run. The threshold is converted
    rather than the fund size: for a positive rate, ``size / rate ≥ threshold``
    is ``size ≥ threshold × rate``, and the product is exact in ``Decimal``
    where the quotient would be rounded. The reason states value, rate and
    rate date, so the verdict can be recomputed by hand.
    """
    name = "Fund size"
    threshold = MIN_FUND_SIZE_LARGE if block in _LARGE_BLOCKS else MIN_FUND_SIZE
    value, open_check = _verified_value(view, isin, 3, name, "fund_size")
    if open_check is not None:
        return open_check
    size = f"fund_size = {value.value} {value.unit} ({value.source_type}, as of {value.as_of})"
    if value.unit == "EUR":
        verdict = Verdict.FULFILLED if value.value >= threshold else Verdict.VIOLATED
        return Check(3, name, verdict, f"{size}, required ≥ {threshold} EUR")

    try:
        rate = view.rate_for(value.unit, value.as_of)
    except LookupError as error:
        # A5.1: without a rate known at the cut-off date there is no EUR value.
        # A gap in the rates (FxRateGapError, v1.6) is a LookupError too: open,
        # never a pass or a fail. The message tells the two cases apart — "no
        # rate on or before" versus "gap of N TARGET business days before".
        return Check(3, name, Verdict.OPEN, f"{size} cannot be converted into EUR: {error}")
    used = f"ECB reference rate {rate.rate} {rate.currency} per EUR of {rate.as_of}"
    if rate.as_of != value.as_of:
        used += f", carried forward to {value.as_of} (G4)"
    used += f" ({rate.source_url})"
    if rate.status is not VerificationStatus.VERIFIED:
        return Check(
            3, name, Verdict.OPEN,
            f"{size}; the {used} is {rate.status}; counts only after reconciliation "
            "with the ECB publication",
        )
    required = Context(traps=[Inexact]).multiply(threshold, rate.rate)
    verdict = Verdict.FULFILLED if value.value >= required else Verdict.VIOLATED
    return Check(
        3, name, verdict,
        f"{size}, at the {used} required ≥ {threshold} EUR = {required} {value.unit}",
    )


def _check_history(view: InstrumentView, isin: str) -> tuple[Check, bool]:
    value, open_check = _verified_value(view, isin, 4, "History", "inception_date")
    if open_check is not None:
        return open_check, False
    years = full_calendar_years(value.value, view.cut_off.date())
    new = years < MIN_CALENDAR_YEARS
    reason = f"{years} full calendar years since inception on {value.value}"
    if new:
        reason += (
            f'; fewer than {MIN_CALENDAR_YEARS}: "new", net costs via the TER '
            "with a 5-point deduction (A5.3)"
        )
    return Check(4, "History", Verdict.FULFILLED, reason), new
