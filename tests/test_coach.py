"""The coach's response assembly (spec T2, T3.3, T4, T7).

The architectural claim under test: the coach cannot forecast, because it
has nothing to forecast *with*. Every number reaches it pre-computed in
``EngineFacts``; the module owns no model, no price series and no
estimator. A test that asks it to predict therefore does not check whether
it declines politely — it checks that declining is the only thing it can
do.

The ordering claim (T4) is the other half: attribution runs before rule
checks and before any behavioural read, so that a normal drawdown is never
coached as a mistake.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from trading_app.coach import (
    Attribution,
    BehaviouralSample,
    Breach,
    CoachRefusal,
    EngineFacts,
    Register,
    Section,
    UncomputedFigure,
    assemble,
    attribute,
    behavioural_finding,
    register_for,
)

BERLIN = dt.timezone(dt.timedelta(hours=2))
NOW = dt.datetime(2026, 9, 10, 17, 0, tzinfo=BERLIN)


def _facts(**overrides: object) -> EngineFacts:
    """A losing trade, inside the modelled envelope, no rules broken."""
    base: dict[str, object] = {
        "as_of": NOW,
        "strategie": "MOM_12_1",
        "drawdown": Decimal("0.06"),
        "envelope_p95": Decimal("0.14"),
        "drawdown_percentile": Decimal("0.42"),
        "breaches": (),
        "has_policy": True,
        "samples": (),
        "active_sharpe": None,
        "active_months": 0,
        "cumulative_shortfall": None,
    }
    base.update(overrides)
    return EngineFacts(**base)  # type: ignore[arg-type]


STOP_MOVED = Breach(
    rule="stop_politik",
    observed="Stop von 98.00 auf 95.50 verschoben",
    limit="Stop darf nur Richtung weniger Risiko bewegt werden",
)
OVERSIZED = Breach(
    rule="risiko_je_trade",
    observed="2.3 % Kapitalrisiko",
    limit="1.0 %",
)


# --- T4 attribution, and it runs first ------------------------------------


def test_a_loss_inside_the_envelope_with_rules_followed_is_edge_variance() -> None:
    assert attribute(_facts()) is Attribution.EDGE_VARIANCE


def test_a_loss_inside_the_envelope_with_a_breach_is_an_execution_error() -> None:
    assert attribute(_facts(breaches=(STOP_MOVED,))) is Attribution.EXECUTION_ERROR


def test_a_loss_beyond_the_envelope_with_rules_followed_is_possible_edge_decay() -> None:
    facts = _facts(drawdown=Decimal("0.19"), drawdown_percentile=Decimal("0.98"))
    assert attribute(facts) is Attribution.POSSIBLE_EDGE_DECAY


def test_a_loss_beyond_the_envelope_with_a_breach_is_both() -> None:
    facts = _facts(
        drawdown=Decimal("0.19"),
        drawdown_percentile=Decimal("0.98"),
        breaches=(STOP_MOVED,),
    )
    assert attribute(facts) is Attribution.BOTH


def test_attribution_is_the_first_section_of_every_response() -> None:
    """T4: before the rule check, always."""
    response = assemble(_facts(breaches=(STOP_MOVED,)), now=NOW)
    assert response.sections[0].kind is Section.ATTRIBUTION


def test_a_normal_drawdown_is_reassured_explicitly_not_coached() -> None:
    """T8.5. The default on a loss inside the envelope is to say so."""
    response = assemble(_facts(), now=NOW)
    attribution = response.sections[0]
    assert "normal" in attribution.text.lower()
    assert not any(s.kind is Section.BEHAVIOURAL for s in response.sections)


def test_a_breach_inside_the_envelope_is_coached_and_the_loss_still_called_normal() -> None:
    """T8.6. Both things are true and the response must say both."""
    response = assemble(_facts(breaches=(STOP_MOVED,)), now=NOW)
    text = response.text.lower()
    assert "stop" in text
    assert "normal" in text


def test_edge_decay_does_not_produce_behavioural_coaching() -> None:
    """Rules were followed. Coaching behaviour here would be a category error."""
    facts = _facts(
        drawdown=Decimal("0.19"),
        drawdown_percentile=Decimal("0.98"),
        samples=(
            BehaviouralSample(pattern="disposition", n_per_arm=60, effect=Decimal("0.35")),
        ),
    )
    response = assemble(facts, now=NOW)
    assert not any(s.kind is Section.BEHAVIOURAL for s in response.sections)


# --- T2.1 / T3.3 tone follows evidence ------------------------------------


def test_a_breach_is_stated_flatly_without_hedging() -> None:
    """A breach is observed, not inferred: sample of one, no hedging words."""
    response = assemble(_facts(breaches=(OVERSIZED,)), now=NOW)
    rule_check = next(s for s in response.sections if s.kind is Section.RULE_CHECK)
    assert rule_check.register is Register.ABSOLUTE
    hedges = ("vielleicht", "möglicherweise", "könnte", "scheint", "tendenziell")
    assert not any(h in rule_check.text.lower() for h in hedges)


def test_a_breach_names_the_number_and_the_limit() -> None:
    response = assemble(_facts(breaches=(OVERSIZED,)), now=NOW)
    rule_check = next(s for s in response.sections if s.kind is Section.RULE_CHECK)
    assert "2.3 %" in rule_check.text
    assert "1.0 %" in rule_check.text


def test_a_behavioural_finding_is_calibrated_never_absolute() -> None:
    sample = BehaviouralSample(
        pattern="disposition", n_per_arm=60, effect=Decimal("0.35")
    )
    facts = _facts(breaches=(STOP_MOVED,), samples=(sample,))
    response = assemble(facts, now=NOW)
    behavioural = next(s for s in response.sections if s.kind is Section.BEHAVIOURAL)
    assert behavioural.register is Register.CALIBRATED


# --- T3 the minimum sample ------------------------------------------------


def test_a_disposition_effect_below_the_threshold_yields_no_diagnosis() -> None:
    """T8.7. Twenty opportunities per arm is not a finding."""
    sample = BehaviouralSample(
        pattern="disposition", n_per_arm=20, effect=Decimal("0.35")
    )
    finding = behavioural_finding(sample)
    assert not finding.is_diagnosis
    assert "20" in finding.text


def test_a_severe_effect_above_the_threshold_is_reportable() -> None:
    sample = BehaviouralSample(
        pattern="disposition", n_per_arm=60, effect=Decimal("0.35")
    )
    assert behavioural_finding(sample).is_diagnosis


def test_an_odean_sized_effect_is_never_a_diagnosis_however_long_you_wait() -> None:
    """T3.1's uncomfortable consequence, enforced rather than merely written.

    A .05 effect needs ~961 per arm. Even at 400 the honest answer is that
    the data cannot carry the claim.
    """
    sample = BehaviouralSample(
        pattern="disposition", n_per_arm=400, effect=Decimal("0.05")
    )
    finding = behavioural_finding(sample)
    assert not finding.is_diagnosis


def test_a_sub_threshold_sample_still_shows_the_raw_counts() -> None:
    """T3.2: report the counts, withhold the label."""
    sample = BehaviouralSample(
        pattern="revenge", n_per_arm=6, effect=Decimal("0.40")
    )
    finding = behavioural_finding(sample)
    assert not finding.is_diagnosis
    assert "6" in finding.text


def test_each_pattern_carries_its_own_threshold() -> None:
    """Overtrading needs months, revenge trading needs post-loss entries."""
    assert behavioural_finding(
        BehaviouralSample(pattern="revenge", n_per_arm=25, effect=Decimal("0.4"))
    ).is_diagnosis
    assert not behavioural_finding(
        BehaviouralSample(pattern="revenge", n_per_arm=19, effect=Decimal("0.4"))
    ).is_diagnosis


# --- T2 what the coach may not do -----------------------------------------


def test_asking_whether_a_trade_will_work_is_refused() -> None:
    """T8.10."""
    with pytest.raises(CoachRefusal, match="(?i)prognose|forecast"):
        assemble(_facts(), now=NOW, question="Wird dieser Trade funktionieren?")


def test_asking_the_coach_to_rank_setup_quality_is_refused() -> None:
    with pytest.raises(CoachRefusal, match="(?i)prognose|forecast"):
        assemble(_facts(), now=NOW, question="Ist das ein gutes Setup?")


def test_an_uncomputed_figure_is_named_as_uncomputed_not_estimated() -> None:
    """If the engine did not compute it, the coach says so."""
    facts = _facts(drawdown_percentile=None)
    response = assemble(facts, now=NOW)
    assert "nicht berechnet" in response.text.lower()


def test_an_uncomputed_percentile_makes_attribution_refuse_to_classify() -> None:
    """Better an honest gap than a classification resting on a guess."""
    with pytest.raises(UncomputedFigure, match="drawdown_percentile"):
        attribute(_facts(drawdown_percentile=None))


def test_no_policy_means_no_response_at_all() -> None:
    """T8.11 / T1.3: no confirmed TPS, no signals."""
    with pytest.raises(CoachRefusal, match="(?i)kein tps|no policy"):
        assemble(_facts(has_policy=False), now=NOW)


# --- T2 every response states its own limits ------------------------------


def test_every_response_ends_with_what_it_does_not_know() -> None:
    response = assemble(_facts(), now=NOW)
    assert response.sections[-1].kind is Section.LIMITS


def test_the_limits_section_names_the_sample_size_when_one_was_used() -> None:
    sample = BehaviouralSample(
        pattern="disposition", n_per_arm=60, effect=Decimal("0.35")
    )
    response = assemble(_facts(breaches=(STOP_MOVED,), samples=(sample,)), now=NOW)
    assert "60" in response.sections[-1].text


def test_a_directive_is_always_present_and_is_a_single_instruction() -> None:
    response = assemble(_facts(breaches=(OVERSIZED,)), now=NOW)
    directive = next(s for s in response.sections if s.kind is Section.DIRECTIVE)
    assert directive.text.strip()
    assert directive.text.count(".") <= 2


# --- T2.1 the register of each section is explicit ------------------------


def test_attribution_of_a_normal_loss_is_absolute_because_it_is_computed() -> None:
    """The envelope is a computed fact, so the reassurance is not hedged."""
    section = assemble(_facts(), now=NOW).sections[0]
    assert section.register is Register.ABSOLUTE


def test_register_for_a_future_outcome_is_silence() -> None:
    assert register_for("future_outcome") is Register.SILENT
