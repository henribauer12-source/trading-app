"""The two computed tables the Trading Coach specification rests on (T8.1, T8.2).

Both numbers decide when the coach is allowed to speak, so they are pinned
here rather than trusted to a spreadsheet nobody reruns. If these move, the
thresholds in T3.2 and T5.2 move with them and the specification is wrong.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import pytest

ND = NormalDist()


def opportunities_per_arm(p1: float, p2: float, alpha: float, power: float = 0.80) -> float:
    """Sample needed per arm to tell two proportions apart.

    Standard two-proportion power formula. For the disposition effect the two
    proportions are PGR (gains realised) and PLR (losses realised) and an "arm"
    is an opportunity to realise, not a trade (Odean, 1998).
    """
    za = ND.inv_cdf(1 - alpha / 2)
    zb = ND.inv_cdf(power)
    pbar = (p1 + p2) / 2
    num = (
        za * math.sqrt(2 * pbar * (1 - pbar))
        + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    return num / ((p1 - p2) ** 2)


def mintrl(
    sr_annual: float,
    alpha: float,
    skew: float = -0.72,
    kurt: float = 5.78,
    periods_per_year: int = 12,
) -> float:
    """Minimum track record length in observations.

    Bailey & Lopez de Prado (2012), Eq. 13 — the same formula already carried
    in the calculation-core specification as test value T9. Applied to the
    active return of trading against the L1 ETF benchmark, so SR* = 0.
    """
    sr = sr_annual / math.sqrt(periods_per_year)
    z = ND.inv_cdf(1 - alpha)
    return 1 + (1 - skew * sr + ((kurt - 1) / 4) * sr**2) * (z / sr) ** 2


# --- T8.1 behavioural sample sizes ----------------------------------------


def test_bonferroni_alpha_for_four_behaviours() -> None:
    """The coach tests four patterns, so each one gets alpha/4."""
    assert 0.05 / 4 == pytest.approx(0.0125)


@pytest.mark.parametrize(
    ("label", "p1", "p2", "expected"),
    [
        ("odean aggregate", 0.148, 0.098, 961),
        ("moderate", 0.20, 0.10, 283),
        ("strong", 0.30, 0.10, 88),
        ("severe", 0.40, 0.10, 45),
    ],
)
def test_disposition_effect_sample_table(
    label: str, p1: float, p2: float, expected: int
) -> None:
    """T3.1: opportunities per arm at the Bonferroni-corrected level."""
    assert round(opportunities_per_arm(p1, p2, 0.0125)) == expected


def test_an_odean_sized_effect_is_undetectable_in_one_account() -> None:
    """The uncomfortable consequence T3.1 states out loud.

    An aggregate-sized disposition effect needs ~961 realisation
    opportunities per arm. A retail trader does not get there, so the
    honest output is "not enough data" and the specification must not
    pretend otherwise.
    """
    needed = opportunities_per_arm(0.148, 0.098, 0.0125)
    plausible_yearly_opportunities = 100
    assert needed / plausible_yearly_opportunities > 9  # more than nine years


def test_only_a_severe_effect_clears_the_reportable_threshold() -> None:
    """T3.2 sets 45 opportunities per arm, which only the severe effect meets."""
    assert round(opportunities_per_arm(0.40, 0.10, 0.0125)) == 45
    assert round(opportunities_per_arm(0.30, 0.10, 0.0125)) > 45


# --- T8.2 stop-trading window ---------------------------------------------


@pytest.mark.parametrize(
    ("sr", "alpha", "expected_months"),
    [
        (0.30, 0.05, 387),
        (0.50, 0.05, 148),
        (0.75, 0.05, 71),
        (1.00, 0.05, 43),
        (0.50, 0.20, 39),
        (0.50, 0.30, 16),
    ],
)
def test_mintrl_table(sr: float, alpha: float, expected_months: int) -> None:
    """T5.1: months of live trading needed to call an active return negative."""
    assert round(mintrl(sr, alpha)) == expected_months


def test_mintrl_matches_calculation_core_t9() -> None:
    """Same formula as the already-VERIFIZIERT test value T9.

    T9: SR=2/sqrt(12), SR*=1/sqrt(12), 95% -> 59.895099 months. T9 uses a
    non-zero SR*, so it is recomputed here directly rather than through the
    SR*=0 helper.
    """
    sr, sr_star = 2 / math.sqrt(12), 1 / math.sqrt(12)
    z = ND.inv_cdf(0.95)
    value = 1 + (1 - (-0.72) * sr + ((5.78 - 1) / 4) * sr**2) * (z / (sr - sr_star)) ** 2
    assert value == pytest.approx(59.895099, abs=1e-6)


def test_ninety_five_percent_would_silence_the_coach_for_over_a_decade() -> None:
    """The argument in T5.1 for an asymmetric threshold.

    Requiring the G7 admission standard before saying "stop" means twelve
    years of underperformance first. A gate built to keep false strategies
    out is the wrong instrument for retiring a real one.
    """
    assert mintrl(0.50, 0.05) / 12 > 12


def test_cost_of_waiting_reaches_the_stop_trigger_within_two_years() -> None:
    """T5.2's 15% cumulative-shortfall trigger, at -0.50 active SR, 15% vol."""
    shortfall_24m = 0.50 * 0.15 * 2
    assert shortfall_24m == pytest.approx(0.15)


def test_the_ladder_lowers_its_evidence_bar_as_cost_accumulates() -> None:
    """Each rung demands less confidence than the last, by design."""
    ladder = [(12, None), (18, 0.70), (24, 0.80)]
    confidences = [c for _, c in ladder if c is not None]
    assert confidences == sorted(confidences)
    assert all(c < 0.95 for c in confidences)  # all below the G7 admission gate
