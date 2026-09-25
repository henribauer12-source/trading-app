"""The benchmark question (spec T5, T6).

The module that can tell the user to stop. Its whole justification is the
asymmetry in T5.1: symmetric 95 % confidence at an active Sharpe of −0.50
needs 148 months, while the shortfall against simply holding the ETF
reaches −15 % inside 24. A gate built to keep false strategies *out* is
the wrong instrument for retiring one that is already running, because
here the cost of silence compounds.

So the ladder lowers its evidence bar as the accumulated cost rises, and
states the confidence level out loud every time. These tests pin the rungs,
and — more importantly — pin the two ways the directive could be quietly
defused: softening it after a good month, and letting it be avoided by
never asking.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_app.benchmark import (
    Confidence,
    Rung,
    ReviewDue,
    BenchmarkReview,
    review,
    mintrl_months,
    shortfall_after,
)


def _review(**overrides: object) -> BenchmarkReview:
    """A trading record that is losing, but not yet long enough to act on."""
    base: dict[str, object] = {
        "active_sharpe": Decimal("-0.50"),
        "months": 6,
        "cumulative_shortfall_pct": Decimal("-0.04"),
        "cumulative_shortfall_eur": Decimal("-400"),
        "trading_capital_eur": Decimal("10000"),
        "last_month_positive": False,
    }
    base.update(overrides)
    return BenchmarkReview(**base)  # type: ignore[arg-type]


# --- T5.1 the asymmetry that justifies the whole design -------------------


def test_mintrl_reproduces_the_specification_table() -> None:
    """T8.2. If this drifts, the ladder's justification drifts with it."""
    assert round(mintrl_months(-0.50, 0.05)) == 148
    assert round(mintrl_months(-0.30, 0.05)) == 387
    assert round(mintrl_months(-1.00, 0.05)) == 43


def test_ninety_five_percent_confidence_would_silence_the_coach_for_a_decade() -> None:
    assert mintrl_months(-0.50, 0.05) / 12 > 12


def test_the_shortfall_table_matches_the_specification() -> None:
    """15 % active volatility, the cost of waiting for certainty."""
    assert shortfall_after(12) == pytest.approx(-0.075, abs=1e-4)
    assert shortfall_after(24) == pytest.approx(-0.150, abs=1e-4)
    assert shortfall_after(60) == pytest.approx(-0.375, abs=1e-4)


def test_waiting_for_certainty_costs_more_than_the_stop_trigger() -> None:
    """The argument in one assertion: certainty arrives long after the money
    is gone."""
    months_to_certainty = mintrl_months(-0.50, 0.05)
    assert abs(shortfall_after(months_to_certainty)) > 0.15


# --- T5.2 the rungs -------------------------------------------------------


def test_from_month_one_the_result_is_reported_but_not_conclusive() -> None:
    result = review(_review(months=1))
    assert result.rung is Rung.REPORT
    assert "nicht schlüssig" in result.text.lower()


def test_a_losing_year_produces_a_warning_naming_the_shortfall_in_euros() -> None:
    result = review(
        _review(months=13, cumulative_shortfall_eur=Decimal("-820"))
    )
    assert result.rung is Rung.WARN
    assert "820" in result.text


def test_the_warning_forbids_increasing_size() -> None:
    result = review(_review(months=13))
    assert "keine" in result.directive.lower()
    assert "erhöh" in result.directive.lower()


def test_eighteen_losing_months_at_seventy_percent_halves_the_size() -> None:
    result = review(_review(months=18))
    assert result.rung is Rung.HALVE
    assert "halbier" in result.directive.lower()


def test_twenty_four_losing_months_at_eighty_percent_stops_trading() -> None:
    result = review(_review(months=24))
    assert result.rung is Rung.STOP


def test_a_fifteen_percent_shortfall_stops_trading_at_any_horizon() -> None:
    """The second, independent stop trigger. Three months is enough if the
    damage is that large."""
    result = review(
        _review(months=3, cumulative_shortfall_pct=Decimal("-0.16"))
    )
    assert result.rung is Rung.STOP


def test_a_recent_positive_sharpe_does_not_cancel_a_fifteen_percent_shortfall() -> None:
    """The most seductive case, and the one the trigger exists for.

    A strategy that has just turned positive after losing 16 % of trading
    capital offers a recovery narrative: it works now, the loss is behind
    us. The money is still gone, and the shortfall trigger is deliberately
    independent of the Sharpe window so that story cannot defer the stop.
    """
    result = review(
        _review(
            months=30,
            active_sharpe=Decimal("0.35"),
            cumulative_shortfall_pct=Decimal("-0.16"),
        )
    )
    assert result.rung is Rung.STOP


def test_the_ladder_never_skips_a_rung_it_has_not_earned() -> None:
    """A positive Sharpe returns to reporting regardless of elapsed months."""
    result = review(_review(months=30, active_sharpe=Decimal("0.20")))
    assert result.rung is Rung.REPORT


def test_the_confidence_bar_rises_with_the_severity_of_the_directive() -> None:
    """Stopping is more drastic than halving and asks for more evidence.

    The ladder's "lower bar" is relative to the 95 % admission gate, not a
    monotonic decline across rungs.
    """
    assert Confidence.for_rung(Rung.HALVE) == Decimal("0.70")
    assert Confidence.for_rung(Rung.STOP) == Decimal("0.80")
    assert Confidence.for_rung(Rung.HALVE) < Confidence.for_rung(Rung.STOP)


def test_the_warning_makes_no_statistical_claim() -> None:
    """It reports money already lost, which needs no confidence level."""
    assert Confidence.for_rung(Rung.WARN) is None


def test_every_confidence_level_stays_below_the_admission_gate() -> None:
    """95 % admits a strategy. Retiring one deliberately asks for less."""
    for rung in (Rung.WARN, Rung.HALVE, Rung.STOP):
        level = Confidence.for_rung(rung)
        if level is not None:
            assert level < Decimal("0.95")


# --- T5.2 confidence is stated, never hidden ------------------------------


def test_every_statistical_rung_states_its_confidence_out_loud() -> None:
    for months in (18, 24):
        result = review(_review(months=months))
        assert "%" in result.text


def test_the_warning_states_money_rather_than_confidence() -> None:
    result = review(_review(months=13, cumulative_shortfall_eur=Decimal("-820")))
    assert "820" in result.text
    assert result.confidence is None


def test_the_stop_directive_explains_why_it_asks_for_less_than_ninety_five() -> None:
    """Otherwise the lower bar reads as a weaker case rather than a
    deliberate asymmetry."""
    result = review(_review(months=24))
    assert "95" in result.text
    assert "asymmetr" in result.text.lower()


# --- T5.3 non-suppression -------------------------------------------------


def test_a_profitable_final_month_does_not_soften_the_stop(  # T8.9
) -> None:
    result = review(_review(months=24, last_month_positive=True))
    assert result.rung is Rung.STOP


def test_the_stop_text_is_not_hedged_when_the_last_month_was_good() -> None:
    hedged = review(_review(months=24, last_month_positive=True))
    plain = review(_review(months=24, last_month_positive=False))
    assert hedged.directive == plain.directive


def test_the_review_is_due_on_schedule_not_on_request() -> None:
    """T5.3: a review that must be asked for can be avoided by not asking."""
    assert ReviewDue.monthly(last_review_month=1, current_month=2) is True
    assert ReviewDue.monthly(last_review_month=2, current_month=2) is False


def test_a_stop_is_reversible_only_through_a_new_policy() -> None:
    result = review(_review(months=24))
    assert "tps" in result.text.lower()


# --- T6 after costs and after tax ----------------------------------------


def test_a_review_computed_on_gross_figures_is_refused() -> None:
    """T6: gross flatters trading, because the core defers its gains."""
    with pytest.raises(ValueError, match="(?i)netto|after tax"):
        review(_review(), net_of_costs_and_tax=False)
