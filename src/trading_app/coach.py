"""The coach's response assembly (spec T2, T3, T4, T7).

The engine computes; the coach speaks. That division is enforced here by
construction rather than by instruction: this module receives
``EngineFacts`` and owns no model, no price series and no estimator, so
there is nothing for a forecast to be made *from*. Plan v9 §2 forbids
return forecasts, and the cheapest way to obey a ban is to make the
forbidden thing unrepresentable.

What the coach adds is ordering and register. Attribution runs first (T4),
because a loss inside the modelled envelope is not a mistake and coaching
it as one teaches the user to abandon strategies that are working. Then
the rule check, flat and absolute, because a breach is observed rather
than inferred. Then — only if a rule was actually broken — the behavioural
read, hedged and carrying its sample size, because a tendency is a
statistical claim and T3 sets a high bar for making one.

Every response ends by naming its own limits. The flat register on
breaches is credible precisely because the honesty elsewhere is visible.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum, auto
from typing import Final

__all__ = [
    "Attribution",
    "BehaviouralSample",
    "Breach",
    "CoachRefusal",
    "EngineFacts",
    "Finding",
    "Register",
    "Response",
    "Section",
    "SectionText",
    "UncomputedFigure",
    "assemble",
    "attribute",
    "behavioural_finding",
    "register_for",
]


class CoachRefusal(Exception):
    """The coach declines. Raised rather than returned: a refusal is not a
    response with empty content, it is the absence of one."""


class UncomputedFigure(LookupError):
    """A figure the engine did not compute was required for a judgement.

    Distinct from a missing key: the point is that the coach must not
    substitute an estimate of its own.
    """


class Attribution(StrEnum):
    EDGE_VARIANCE = auto()
    EXECUTION_ERROR = auto()
    POSSIBLE_EDGE_DECAY = auto()
    BOTH = auto()


class Register(StrEnum):
    """T2.1. The coach's confidence may never exceed its evidence grade."""

    ABSOLUTE = auto()
    CALIBRATED = auto()
    SILENT = auto()


class Section(StrEnum):
    ATTRIBUTION = auto()
    RULE_CHECK = auto()
    BEHAVIOURAL = auto()
    DIRECTIVE = auto()
    LIMITS = auto()


@dataclass(frozen=True, slots=True)
class Breach:
    """An observed rule violation. Sample of one by nature (T3.3)."""

    rule: str
    observed: str
    limit: str


@dataclass(frozen=True, slots=True)
class BehaviouralSample:
    """A candidate behavioural pattern with the sample behind it.

    ``effect`` is the difference in proportions (e.g. PGR − PLR), already
    computed by the engine.
    """

    pattern: str
    n_per_arm: int
    effect: Decimal


@dataclass(frozen=True, slots=True)
class EngineFacts:
    """Everything the coach is allowed to know, all of it pre-computed.

    ``drawdown_percentile`` is ``None`` when the backtest engine has not
    produced an envelope for this strategy. That is a gap to be reported,
    never one for the coach to fill.
    """

    as_of: dt.datetime
    strategie: str
    drawdown: Decimal
    envelope_p95: Decimal | None
    drawdown_percentile: Decimal | None
    breaches: tuple[Breach, ...]
    has_policy: bool
    samples: tuple[BehaviouralSample, ...]
    active_sharpe: Decimal | None
    active_months: int
    cumulative_shortfall: Decimal | None


@dataclass(frozen=True, slots=True)
class SectionText:
    kind: Section
    text: str
    register: Register


@dataclass(frozen=True, slots=True)
class Finding:
    """A behavioural read. ``is_diagnosis`` false means the counts are shown
    and the label withheld (T3.2)."""

    pattern: str
    is_diagnosis: bool
    text: str
    register: Register
    n_per_arm: int


@dataclass(frozen=True, slots=True)
class Response:
    sections: tuple[SectionText, ...]

    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self.sections)


# T3.2, reproduced from the specification. Per-pattern because the
# statistic differs per pattern; a single round number across all four
# would be the spurious precision the quality standards forbid.
_MIN_N: Final[dict[str, int]] = {
    "disposition": 45,
    "overtrading": 3,  # months of history
    "revenge": 20,  # post-loss entries
    "performance_chasing": 10,  # streak events
}

# Only a *severe* disposition effect is reportable at a reachable sample
# size. An Odean-sized effect needs 961 per arm and is therefore declared
# undetectable in a private account (T3.1) rather than diagnosed weakly.
_MIN_EFFECT: Final[dict[str, Decimal]] = {
    "disposition": Decimal("0.30"),
}

_FORECAST_TRIGGERS: Final[tuple[str, ...]] = (
    "wird",
    "funktionieren",
    "gutes setup",
    "gut?",
    "besser",
    "wahrscheinlich",
    "prognose",
    "vorhersage",
    "lohnt sich",
    "soll ich kaufen",
    "will it work",
    "good setup",
)


def register_for(domain: str) -> Register:
    """T2.1's table as a function. ``future_outcome`` is silence, not a
    hedged answer: hedging still implies a view."""
    return {
        "rule_breach": Register.ABSOLUTE,
        "behavioural_pattern": Register.CALIBRATED,
        "edge_performance": Register.CALIBRATED,
        "future_outcome": Register.SILENT,
    }.get(domain, Register.CALIBRATED)


def attribute(facts: EngineFacts) -> Attribution:
    """T4 step 3. Classify the loss before judging the trader.

    Refuses when the envelope percentile is unknown: without it there is no
    basis for calling a drawdown normal or abnormal, and guessing would
    make the most consequential judgement in the module the least grounded.
    """
    if facts.drawdown_percentile is None:
        raise UncomputedFigure(
            "drawdown_percentile nicht berechnet — ohne Envelope keine Attribution"
        )
    beyond = facts.drawdown_percentile > Decimal("0.95")
    breached = bool(facts.breaches)
    if beyond and breached:
        return Attribution.BOTH
    if beyond:
        return Attribution.POSSIBLE_EDGE_DECAY
    if breached:
        return Attribution.EXECUTION_ERROR
    return Attribution.EDGE_VARIANCE


def behavioural_finding(sample: BehaviouralSample) -> Finding:
    """T3.2. Above threshold: a finding, still calibrated. Below: the raw
    counts and no label.

    The sample size appears in the text either way — when it is too small
    that *is* the finding, and it is more useful to the user than silence.
    """
    min_n = _MIN_N.get(sample.pattern, 45)
    min_effect = _MIN_EFFECT.get(sample.pattern)
    big_enough = sample.n_per_arm >= min_n
    strong_enough = min_effect is None or sample.effect >= min_effect

    if big_enough and strong_enough:
        return Finding(
            pattern=sample.pattern,
            is_diagnosis=True,
            text=(
                f"{sample.pattern}: Effekt {sample.effect} bei "
                f"n = {sample.n_per_arm} je Arm (Schwelle {min_n}). "
                f"Das Muster ist belegt, nicht bewiesen — Konfidenz 87,5 %, "
                f"bewusst unter 95 %."
            ),
            register=Register.CALIBRATED,
            n_per_arm=sample.n_per_arm,
        )

    if not big_enough:
        reason = f"n = {sample.n_per_arm} je Arm, nötig sind {min_n}"
    else:
        reason = (
            f"Effekt {sample.effect} unter der Schwelle {min_effect}; "
            f"ein Odean-großer Effekt bräuchte 961 je Arm und ist in einem "
            f"Privatkonto nicht nachweisbar"
        )
    return Finding(
        pattern=sample.pattern,
        is_diagnosis=False,
        text=(
            f"{sample.pattern}: keine Diagnose — {reason}. "
            f"Rohwerte werden gezeigt, das Label nicht vergeben."
        ),
        register=Register.CALIBRATED,
        n_per_arm=sample.n_per_arm,
    )


def _looks_like_a_forecast_request(question: str) -> bool:
    lowered = question.lower()
    return any(trigger in lowered for trigger in _FORECAST_TRIGGERS)


def _attribution_section(facts: EngineFacts) -> SectionText:
    if facts.drawdown_percentile is None:
        return SectionText(
            kind=Section.ATTRIBUTION,
            text=(
                "Attribution nicht möglich: Drawdown-Perzentil nicht berechnet. "
                "Der Backtest-Envelope für "
                f"{facts.strategie} fehlt. Kein Urteil über normal oder "
                "auffällig — die Zahl wird nicht geschätzt."
            ),
            register=Register.CALIBRATED,
        )

    verdict = attribute(facts)
    pct = facts.drawdown_percentile
    if verdict in (Attribution.EDGE_VARIANCE, Attribution.EXECUTION_ERROR):
        text = (
            f"Der Verlust liegt im modellierten Envelope von {facts.strategie} "
            f"(Perzentil {pct}). Das ist normal und kein Fehler."
        )
    else:
        text = (
            f"Der Drawdown liegt bei Perzentil {pct} und damit außerhalb des "
            f"modellierten Envelope von {facts.strategie}. Das ist kein Urteil "
            "über die Strategie, sondern der Anlass, sie zu prüfen."
        )
    return SectionText(
        kind=Section.ATTRIBUTION, text=text, register=Register.ABSOLUTE
    )


def _rule_check_section(facts: EngineFacts) -> SectionText:
    if not facts.breaches:
        return SectionText(
            kind=Section.RULE_CHECK,
            text="Regelprüfung: kein Verstoß.",
            register=Register.ABSOLUTE,
        )
    lines = [
        f"{b.rule}: {b.observed} — Limit {b.limit}." for b in facts.breaches
    ]
    return SectionText(
        kind=Section.RULE_CHECK,
        text="Regelprüfung: " + " ".join(lines),
        register=Register.ABSOLUTE,
    )


def _directive_section(facts: EngineFacts, verdict: Attribution | None) -> SectionText:
    if facts.breaches:
        first = facts.breaches[0]
        text = f"Nächster Trade: {first.rule} einhalten, {first.limit}."
    elif verdict is Attribution.POSSIBLE_EDGE_DECAY:
        text = "Strategie gegen den Benchmark prüfen, Position vorerst nicht erhöhen."
    else:
        text = "Nichts zu ändern, Regeln weiter einhalten."
    return SectionText(
        kind=Section.DIRECTIVE, text=text, register=Register.ABSOLUTE
    )


def _limits_section(facts: EngineFacts, findings: tuple[Finding, ...]) -> SectionText:
    parts = ["Was hier nicht bekannt ist:"]
    if facts.drawdown_percentile is None:
        parts.append("das Drawdown-Perzentil ist nicht berechnet")
    for finding in findings:
        parts.append(
            f"{finding.pattern} beruht auf n = {finding.n_per_arm} je Arm"
        )
    if facts.active_months < 12:
        parts.append(
            f"die Strategie läuft erst {facts.active_months} Monate, "
            "für eine Aussage über den Edge zu kurz"
        )
    parts.append("über den Ausgang des nächsten Trades wird nichts gesagt")
    return SectionText(
        kind=Section.LIMITS,
        text=" ".join(parts[:1]) + " " + "; ".join(parts[1:]) + ".",
        register=Register.CALIBRATED,
    )


def assemble(
    facts: EngineFacts,
    *,
    now: dt.datetime,
    question: str | None = None,
) -> Response:
    """Build the response in the fixed T4 order.

    Refuses outright on two conditions: no confirmed policy (T1.3 — without
    a rulebook there is nothing to enforce and "your rules" becomes whatever
    the user says when asked), and any question that asks for a forecast.
    """
    if not facts.has_policy:
        raise CoachRefusal(
            "Kein TPS bestätigt — kein Signal, keine Bewertung. "
            "Die Regeln müssen vor dem Trade feststehen, nicht danach."
        )
    if question is not None and _looks_like_a_forecast_request(question):
        raise CoachRefusal(
            "Keine Prognose. Ob ein Trade funktioniert, ist vorher nicht "
            "bekannt und wird hier nicht geschätzt (Plan v9 §2). "
            "Geprüft wird die Regelkonformität, nicht die Aussicht."
        )

    verdict: Attribution | None = None
    if facts.drawdown_percentile is not None:
        verdict = attribute(facts)

    sections: list[SectionText] = [_attribution_section(facts)]
    sections.append(_rule_check_section(facts))

    # T4: behavioural coaching only where a rule was actually broken.
    # Where the rules were followed, the loss is variance or decay, and
    # coaching behaviour would be a category error.
    findings: tuple[Finding, ...] = ()
    if facts.breaches and facts.samples:
        findings = tuple(behavioural_finding(s) for s in facts.samples)
        for finding in findings:
            sections.append(
                SectionText(
                    kind=Section.BEHAVIOURAL,
                    text=finding.text,
                    register=finding.register,
                )
            )

    sections.append(_directive_section(facts, verdict))
    sections.append(_limits_section(facts, findings))
    return Response(sections=tuple(sections))
