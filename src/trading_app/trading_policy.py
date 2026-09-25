"""The Trading Policy Statement: rules written when calm (spec T1).

The trading module's counterpart to the IPS (investment spec A11), and the
object the Trading Coach enforces. Without it, "your rules" means whatever
the user says at the moment they are asked — which is exactly the emotional
override the coach exists to prevent.

**Design: an append-only register, read point-in-time.**

The same shape as the rest of the data layer (``bitemporal``), for the same
reason. A TPS amendment is not an edit; it is a new version with a moment
from which it applies. What the rules *were* when a trade was placed must
stay reconstructable, because the coach's judgements are made against the
rules in force at the time, not the rules in force today. A mutable policy
object would quietly rewrite the past every time the user changed their
mind, and every past breach would disappear with it.

Two timestamps per version:

| Field           | Meaning                                              |
|-----------------|------------------------------------------------------|
| `confirmed_at`  | when the user confirmed the amendment                |
| `effective_at`  | from when it governs — `confirmed_at` + waiting time |

The gap between them is the whole mechanism. ``in_force_at`` compares against
``effective_at``, so a loosening confirmed today does not govern today.

**The asymmetry.** The waiting period (T1.2, 72 hours, the same figure as
the behavioural guardrails A12) applies only to amendments that *loosen* a
rule. Tightening takes effect at once. A waiting period is protection
against the decision made in the heat of a drawdown, not against caution —
delaying a user who wants to take less risk would be protecting them from
the wrong thing.

**Refusals, not queues.** An amendment arriving while a position is open, or
while the account is in drawdown, is refused outright rather than accepted
and delayed. A queued amendment is still an amendment made under pressure;
it would simply arrive later wearing a calmer timestamp. The user may
re-submit when flat, which is the point.

A mixed amendment — one field tightened, another loosened — counts as
loosening. Otherwise every loosening would arrive wrapped in a token
tightening.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum

__all__ = [
    "AccountState",
    "AmendmentRefused",
    "Direction",
    "PolicyRegister",
    "PolicyValidationError",
    "PolicyVersion",
    "StopPolicy",
    "TradingPolicyStatement",
    "classify_amendment",
]

#: T1.2 — the same waiting period as the behavioural guardrails (A12).
#: ENTSCHEIDUNG, no direct evidence: long enough to outlast the impulse,
#: short enough that a genuine change of plan is not punished.
WAITING_PERIOD = dt.timedelta(hours=72)

#: Read from the risk module (plan v9 §4.9). The TPS may go below these,
#: never above. Hard-coded here until the risk module exists; when it does,
#: this becomes a lookup and the tests stay as they are.
RISK_CEILING_PER_TRADE = Decimal("0.01")

#: R4 learning-stage gates (plan v9 §2). Instruments not listed need no stage.
STAGE_REQUIRED: dict[str, int] = {
    "swing": 3,
    "hebel": 5,
    "zertifikat": 5,
    "option": 6,
    "optionsschein": 6,
}


class PolicyValidationError(ValueError):
    """A statement that contradicts the app's own limits."""


class AmendmentRefused(PermissionError):
    """An amendment that is not refused on its content but on its timing."""


class StopPolicy(Enum):
    """How a stop is set. A stop may only ever be moved toward less risk."""

    HART = "hart"
    ZEITBASIERT = "zeitbasiert"


class Direction(Enum):
    """Which way an amendment moves the constraints."""

    TIGHTENS = "tightens"
    LOOSENS = "loosens"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class AccountState:
    """What the account looks like at the moment an amendment arrives.

    Only the two facts that decide whether an amendment may be considered
    at all. Supplied by the caller rather than read here, so that this
    module stays free of a dependency on live position data.
    """

    has_open_position: bool
    drawdown: Decimal


@dataclass(frozen=True, slots=True)
class TradingPolicyStatement:
    """The rules themselves (T1.1).

    Frozen: a statement is a value, and amending it means producing a new
    one. ``handelsfenster`` is a tuple of ``(strategie, von, bis)`` rather
    than a mapping so the whole statement stays hashable and comparable.
    """

    strategien: tuple[str, ...]
    instrumente: tuple[str, ...]
    handelsfenster: tuple[tuple[str, dt.time, dt.time], ...]
    risiko_je_trade: Decimal
    max_parallele_positionen: int
    tagesverlustgrenze: Decimal
    stop_politik: StopPolicy
    pausenbedingungen: tuple[str, ...]
    was_ich_bei_serienverlust_tue: str
    erstellt_am: dt.datetime
    gueltig_ab: dt.datetime
    lernstufe: int

    def __post_init__(self) -> None:
        if self.risiko_je_trade > RISK_CEILING_PER_TRADE:
            raise PolicyValidationError(
                f"risiko_je_trade {self.risiko_je_trade} exceeds the risk "
                f"module ceiling {RISK_CEILING_PER_TRADE}. The statement may "
                f"set a lower limit, never a higher one."
            )
        if self.risiko_je_trade <= 0:
            raise PolicyValidationError("risiko_je_trade must be positive.")
        if self.tagesverlustgrenze <= 0:
            raise PolicyValidationError("tagesverlustgrenze must be positive.")
        if self.max_parallele_positionen < 1:
            raise PolicyValidationError("max_parallele_positionen must be at least 1.")

        for instrument in self.instrumente:
            required = STAGE_REQUIRED.get(instrument)
            if required is not None and self.lernstufe < required:
                raise PolicyValidationError(
                    f"instrument {instrument!r} unlocks at learning stage "
                    f"{required}; the statement is at stage {self.lernstufe}."
                )

        if not self.was_ich_bei_serienverlust_tue.strip():
            raise PolicyValidationError(
                "was_ich_bei_serienverlust_tue must be filled in the user's "
                "own words. A commitment written when calm is the point."
            )

        for strategie, von, bis in self.handelsfenster:
            if strategie not in self.strategien:
                raise PolicyValidationError(
                    f"handelsfenster names strategy {strategie!r}, which is "
                    f"not in strategien."
                )
            if von >= bis:
                raise PolicyValidationError(
                    f"handelsfenster for {strategie!r} ends before it starts."
                )

        for name in ("erstellt_am", "gueltig_ab"):
            value: dt.datetime = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise PolicyValidationError(
                    f"{name} needs a zeitzone. A waiting period measured "
                    f"against a naive clock is not a waiting period."
                )


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    """One entry in the register: a statement, and when it governs."""

    statement: TradingPolicyStatement
    confirmed_at: dt.datetime
    effective_at: dt.datetime
    direction: Direction
    reason: str


def _loosens(old: TradingPolicyStatement, new: TradingPolicyStatement) -> bool:
    """Does any single field give the user more room than before?

    Deliberately an OR across fields, not a net score. A single loosened
    field makes the whole amendment a loosening.
    """
    if new.risiko_je_trade > old.risiko_je_trade:
        return True
    if new.max_parallele_positionen > old.max_parallele_positionen:
        return True
    if new.tagesverlustgrenze > old.tagesverlustgrenze:
        return True
    if set(new.instrumente) - set(old.instrumente):
        return True
    if set(new.strategien) - set(old.strategien):
        return True
    if set(old.pausenbedingungen) - set(new.pausenbedingungen):
        return True
    if old.stop_politik is StopPolicy.HART and new.stop_politik is StopPolicy.ZEITBASIERT:
        return True
    # A widened trading window is more room; a narrowed one is less.
    old_windows = {s: (v, b) for s, v, b in old.handelsfenster}
    for strategie, von, bis in new.handelsfenster:
        if strategie not in old_windows:
            return True
        old_von, old_bis = old_windows[strategie]
        if von < old_von or bis > old_bis:
            return True
    return False


def _tightens(old: TradingPolicyStatement, new: TradingPolicyStatement) -> bool:
    """The mirror image: does any field give the user less room?"""
    return _loosens(new, old)


def classify_amendment(
    old: TradingPolicyStatement, new: TradingPolicyStatement
) -> Direction:
    """Which way an amendment runs (T1.2).

    Loosening wins over tightening when both appear in one amendment.
    """
    if _loosens(old, new):
        return Direction.LOOSENS
    if _tightens(old, new):
        return Direction.TIGHTENS
    return Direction.UNCHANGED


class PolicyRegister:
    """Append-only history of statements, read point-in-time.

    Not a store in the ``bitemporal`` sense — it holds no market data and
    needs no database — but it follows the same two rules: nothing is
    overwritten, and a read is always "what governed at time T".
    """

    def __init__(self, initial: TradingPolicyStatement | None = None) -> None:
        self._history: list[PolicyVersion] = []
        if initial is not None:
            self._history.append(
                PolicyVersion(
                    statement=initial,
                    confirmed_at=initial.erstellt_am,
                    effective_at=initial.gueltig_ab,
                    direction=Direction.UNCHANGED,
                    reason="Erstfassung.",
                )
            )

    @property
    def history(self) -> tuple[PolicyVersion, ...]:
        """Every version ever confirmed, oldest first. Nothing is removed."""
        return tuple(self._history)

    @property
    def current(self) -> TradingPolicyStatement | None:
        """The latest confirmed statement, whether or not it is yet in force."""
        return self._history[-1].statement if self._history else None

    def in_force_at(self, moment: dt.datetime) -> TradingPolicyStatement | None:
        """The statement governing at ``moment``.

        ``None`` means there is no policy — and by T1.3 that means the
        trading module shows no signals at all.
        """
        governing = [v for v in self._history if v.effective_at <= moment]
        return governing[-1].statement if governing else None

    def has_policy(self, moment: dt.datetime) -> bool:
        return self.in_force_at(moment) is not None

    def amend(
        self,
        proposed: TradingPolicyStatement,
        *,
        now: dt.datetime,
        account: AccountState,
        reason: str = "Keine Begründung angegeben.",
    ) -> PolicyVersion:
        """Confirm an amendment, or refuse it.

        Refusals come before direction, because they are about whether the
        user is in a state to be changing their rules at all — a question
        that does not depend on what the change says.
        """
        if not self._history:
            raise AmendmentRefused(
                "There is no statement to amend. Write an Erstfassung first."
            )
        if reason is not None and not reason.strip():
            raise AmendmentRefused(
                "An amendment must state a begründung. The coach reads these "
                "back at review, and a reason written now is worth more than "
                "one reconstructed later."
            )

        last = self._history[-1]
        if now < last.confirmed_at:
            raise AmendmentRefused(
                f"An amendment may not be rückwirkend: {now.isoformat()} is "
                f"before the last confirmation at {last.confirmed_at.isoformat()}."
            )

        direction = classify_amendment(last.statement, proposed)

        if direction is Direction.LOOSENS:
            if account.has_open_position:
                raise AmendmentRefused(
                    "Refused: offene position. Rules are not loosened with a "
                    "trade on. Close the position and submit again."
                )
            if account.drawdown > 0:
                raise AmendmentRefused(
                    f"Refused: drawdown {account.drawdown}. The moment an "
                    f"amendment is most wanted is the moment it is least "
                    f"trustworthy."
                )

        effective_at = (
            now + WAITING_PERIOD if direction is Direction.LOOSENS else now
        )
        version = PolicyVersion(
            statement=proposed,
            confirmed_at=now,
            effective_at=effective_at,
            direction=direction,
            reason=reason,
        )
        self._history.append(version)
        return version
