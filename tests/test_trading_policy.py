"""Trading Policy Statement — the rulebook the coach enforces (spec T1).

RED first. The interesting cases are not the happy path but the refusals:
the amendment that arrives while a position is open, and the one that
arrives in drawdown. Those are the moments the TPS exists for, because
they are the moments the user most wants their rules to be different.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from trading_app.trading_policy import (
    AccountState,
    AmendmentRefused,
    Direction,
    PolicyRegister,
    PolicyValidationError,
    StopPolicy,
    TradingPolicyStatement,
    classify_amendment,
)

BERLIN = dt.timezone(dt.timedelta(hours=2))


def _tps(**overrides: object) -> TradingPolicyStatement:
    """A valid baseline TPS; each test overrides only what it is about."""
    base: dict[str, object] = {
        "strategien": ("MOM_12_1",),
        "instrumente": ("aktie", "etf"),
        "handelsfenster": (("MOM_12_1", dt.time(15, 30), dt.time(17, 30)),),
        "risiko_je_trade": Decimal("0.005"),
        "max_parallele_positionen": 4,
        "tagesverlustgrenze": Decimal("0.03"),
        "stop_politik": StopPolicy.HART,
        "pausenbedingungen": ("Klausurphase",),
        "was_ich_bei_serienverlust_tue": "Fünf Tage Pause, dann Review.",
        "erstellt_am": dt.datetime(2026, 9, 1, 10, 0, tzinfo=BERLIN),
        "gueltig_ab": dt.datetime(2026, 9, 1, 10, 0, tzinfo=BERLIN),
        "lernstufe": 3,
    }
    base.update(overrides)
    return TradingPolicyStatement(**base)  # type: ignore[arg-type]


CALM = AccountState(has_open_position=False, drawdown=Decimal("0.00"))


# --- T1.1 the statement itself --------------------------------------------


def test_a_valid_statement_is_accepted() -> None:
    assert _tps().risiko_je_trade == Decimal("0.005")


def test_risk_above_the_module_ceiling_is_refused() -> None:
    """T1.1: the TPS may set risk lower than the risk module, never higher."""
    with pytest.raises(PolicyValidationError, match="risiko_je_trade"):
        _tps(risiko_je_trade=Decimal("0.02"))


def test_risk_below_the_ceiling_is_the_users_own_business() -> None:
    assert _tps(risiko_je_trade=Decimal("0.0025")).risiko_je_trade == Decimal("0.0025")


def test_an_instrument_above_the_learning_stage_is_refused() -> None:
    """T1.1/R4: leverage unlocks at stage 5, options at 6."""
    with pytest.raises(PolicyValidationError, match="hebel"):
        _tps(lernstufe=3, instrumente=("aktie", "hebel"))


def test_the_same_instrument_is_allowed_once_the_stage_is_reached() -> None:
    assert "hebel" in _tps(lernstufe=5, instrumente=("aktie", "hebel")).instrumente


def test_a_statement_without_a_loss_streak_commitment_is_refused() -> None:
    """The A11 commitment in the user's own words; an empty one is not one."""
    with pytest.raises(PolicyValidationError, match="serienverlust"):
        _tps(was_ich_bei_serienverlust_tue="   ")


def test_a_trading_window_for_an_unlisted_strategy_is_refused() -> None:
    with pytest.raises(PolicyValidationError, match="handelsfenster"):
        _tps(handelsfenster=(("NICHT_IM_PLAN", dt.time(9), dt.time(10)),))


def test_naive_timestamps_are_refused() -> None:
    """A waiting period measured against a naive clock is not a waiting period."""
    with pytest.raises(PolicyValidationError, match="zeitzone"):
        _tps(erstellt_am=dt.datetime(2026, 9, 1, 10, 0))


# --- T1.2 which direction does an amendment run ----------------------------


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("risiko_je_trade", Decimal("0.004"), Direction.TIGHTENS),
        ("risiko_je_trade", Decimal("0.01"), Direction.LOOSENS),
        ("max_parallele_positionen", 2, Direction.TIGHTENS),
        ("max_parallele_positionen", 8, Direction.LOOSENS),
        ("tagesverlustgrenze", Decimal("0.02"), Direction.TIGHTENS),
        ("tagesverlustgrenze", Decimal("0.05"), Direction.LOOSENS),
        ("instrumente", ("aktie",), Direction.TIGHTENS),
        ("instrumente", ("aktie", "etf", "etc"), Direction.LOOSENS),
        ("pausenbedingungen", ("Klausurphase", "Krankheit"), Direction.TIGHTENS),
        ("pausenbedingungen", (), Direction.LOOSENS),
    ],
)
def test_direction_of_a_single_field_change(
    field: str, value: object, expected: Direction
) -> None:
    assert classify_amendment(_tps(), _tps(**{field: value})) is expected


def test_a_time_based_stop_is_looser_than_a_hard_one() -> None:
    change = classify_amendment(_tps(), _tps(stop_politik=StopPolicy.ZEITBASIERT))
    assert change is Direction.LOOSENS


def test_a_mixed_amendment_counts_as_loosening() -> None:
    """One loosened field is enough. The conservative reading is the safe one:
    otherwise every loosening arrives wrapped in a token tightening.

    Genuinely mixed: risk tightened 0.005 -> 0.004, positions loosened 4 -> 9.
    """
    mixed = _tps(risiko_je_trade=Decimal("0.004"), max_parallele_positionen=9)
    assert classify_amendment(_tps(), mixed) is Direction.LOOSENS


def test_an_amendment_that_changes_nothing_is_neutral() -> None:
    assert classify_amendment(_tps(), _tps()) is Direction.UNCHANGED


# --- T1.2 the amendment procedure, and T8.3 / T8.4 -------------------------


def test_an_amendment_while_a_position_is_open_is_refused_not_queued() -> None:
    """T8.3. Refused outright — a queued amendment is still an amendment made
    with a position on."""
    register = PolicyRegister(_tps())
    with pytest.raises(AmendmentRefused, match="offene position"):
        register.amend(
            _tps(max_parallele_positionen=9),
            now=dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN),
            account=AccountState(has_open_position=True, drawdown=Decimal("0")),
        )


def test_an_amendment_in_drawdown_is_refused() -> None:
    """The moment an amendment is most wanted is the moment it is least
    trustworthy.

    The loosening is explicit — more parallel positions — so the test does
    not depend on a side effect of the fixture.
    """
    register = PolicyRegister(_tps())
    with pytest.raises(AmendmentRefused, match="drawdown"):
        register.amend(
            _tps(max_parallele_positionen=9),
            now=dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN),
            account=AccountState(has_open_position=False, drawdown=Decimal("0.12")),
        )


def test_a_tightening_amendment_is_allowed_even_in_drawdown() -> None:
    """The waiting period protects against loosening, not against caution."""
    register = PolicyRegister(_tps())
    now = dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN)
    version = register.amend(
        _tps(risiko_je_trade=Decimal("0.004")),
        now=now,
        account=AccountState(has_open_position=False, drawdown=Decimal("0.12")),
    )
    assert version.effective_at == now


def test_a_loosening_amendment_waits_seventy_two_hours() -> None:
    register = PolicyRegister(_tps())
    now = dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN)
    version = register.amend(
        _tps(risiko_je_trade=Decimal("0.01")), now=now, account=CALM
    )
    assert version.effective_at == now + dt.timedelta(hours=72)


def test_a_tightening_amendment_takes_effect_at_once() -> None:
    """T8.4."""
    register = PolicyRegister(_tps())
    now = dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN)
    version = register.amend(
        _tps(instrumente=("aktie",)), now=now, account=CALM
    )
    assert version.effective_at == now


def test_an_amendment_must_state_a_reason() -> None:
    """The coach quotes these back at review."""
    register = PolicyRegister(_tps())
    with pytest.raises(AmendmentRefused, match="begründung"):
        register.amend(
            _tps(risiko_je_trade=Decimal("0.01")),
            now=dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN),
            account=CALM,
            reason="",
        )


# --- T1.2 the register is append-only, and reads point-in-time -------------


def test_the_loosened_rule_does_not_apply_before_it_is_effective() -> None:
    """The whole point of the waiting period, as a query."""
    register = PolicyRegister(_tps())
    now = dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN)
    register.amend(_tps(risiko_je_trade=Decimal("0.01")), now=now, account=CALM)

    before = register.in_force_at(now + dt.timedelta(hours=71))
    after = register.in_force_at(now + dt.timedelta(hours=73))
    assert before.risiko_je_trade == Decimal("0.005")  # the old limit still governs
    assert after.risiko_je_trade == Decimal("0.01")


def test_nothing_is_overwritten() -> None:
    """T1.1 aenderungshistorie: every version retained."""
    register = PolicyRegister(_tps())
    now = dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN)
    register.amend(_tps(risiko_je_trade=Decimal("0.004")), now=now, account=CALM)
    register.amend(
        _tps(risiko_je_trade=Decimal("0.003")),
        now=now + dt.timedelta(days=1),
        account=CALM,
    )
    assert len(register.history) == 3


def test_the_history_keeps_the_stated_reasons() -> None:
    register = PolicyRegister(_tps())
    register.amend(
        _tps(risiko_je_trade=Decimal("0.01")),
        now=dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN),
        account=CALM,
        reason="Strategie läuft gut, ich will mehr Risiko.",
    )
    assert "mehr Risiko" in register.history[-1].reason


def test_an_amendment_may_not_be_backdated() -> None:
    register = PolicyRegister(_tps())
    register.amend(
        _tps(risiko_je_trade=Decimal("0.004")),
        now=dt.datetime(2026, 9, 10, 12, 0, tzinfo=BERLIN),
        account=CALM,
    )
    with pytest.raises(AmendmentRefused, match="rückwirkend"):
        register.amend(
            _tps(risiko_je_trade=Decimal("0.003")),
            now=dt.datetime(2026, 9, 9, 12, 0, tzinfo=BERLIN),
            account=CALM,
        )


def test_a_query_before_the_first_statement_has_no_policy() -> None:
    """T1.3: no confirmed TPS, no signals. The caller must handle None."""
    register = PolicyRegister(_tps())
    assert register.in_force_at(dt.datetime(2026, 8, 1, tzinfo=BERLIN)) is None


# --- T1.3 no statement, no signals ----------------------------------------


def test_an_empty_register_is_not_in_force() -> None:
    """T8.11."""
    register = PolicyRegister()
    assert register.in_force_at(dt.datetime(2026, 9, 10, tzinfo=BERLIN)) is None
    assert not register.has_policy(dt.datetime(2026, 9, 10, tzinfo=BERLIN))
