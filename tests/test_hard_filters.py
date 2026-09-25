"""Tests of the hard filters A5.2 (evaluation per investment spec v1.3).

**All ISINs, URLs and numbers here are placeholders** — see
``tests/test_instruments.py``. The fund sizes are the spec's thresholds
(100m €, 500m €) and numbers just next to them, not fund data.

The most important block is ``TestUnverified``: a second-hand value must not
let any filter pass silently.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from trading_app.hard_filters import (
    BuildingBlock,
    Verdict,
    check_hard_filters,
    full_calendar_years,
)
from trading_app.instruments import (
    FieldValue,
    FxRate,
    InstrumentStore,
    SourceType,
    VerificationStatus,
)

UTC = dt.timezone.utc
ISIN = "XX0000000002"  # placeholder, check digit computed by hand
URL = "https://issuer.invalid/kid.pdf"
URL_ECB = "https://ecb.invalid/eurofxref-hist.csv"
CUTOFF = dt.datetime(2026, 9, 25, 12, tzinfo=UTC)

INDEX = {
    BuildingBlock.K1: "MSCI ACWI",
    BuildingBlock.K2_MONEY_MARKET: "€STR",
}


def make_value(field: str, content: object, *, status=VerificationStatus.VERIFIED,
               source_type=SourceType.KID,
               retrieved_at=dt.datetime(2026, 3, 1, tzinfo=UTC),
               as_of=dt.date(2026, 2, 15), unit=None) -> FieldValue:
    # A fund size must name its currency; EUR unless a test says otherwise.
    if unit is None and field == "fund_size":
        unit = "EUR"
    return FieldValue(
        isin=ISIN, field=field, value=content, source_url=URL, source_type=source_type,
        status=status, as_of=as_of, retrieved_at=retrieved_at, unit=unit,
    )


def passing_values(block: BuildingBlock, **overrides: object) -> list[FieldValue]:
    """A verified set that passes all mechanical filters of the building block.

    ``overrides`` replaces single values; ``None`` leaves the field out.
    """
    contents: dict[str, object] = {
        "ucits": True,
        "gold_etc_delivery_claim": True,
        "xetra_tradable": True,
        "kid_language_de": True,
        "index_name": INDEX.get(block, "Placeholder index"),
        "fund_size": Decimal("500000000"),
        "inception_date": dt.date(2015, 6, 1),
        "equity_fund_invstg": True,
        "currency_hedged": True,
    }
    contents.update(overrides)
    return [make_value(field, content) for field, content in contents.items() if content is not None]


def evaluate(block: BuildingBlock, values: list[FieldValue], cutoff: dt.datetime = CUTOFF):
    with InstrumentStore(":memory:") as store:
        store.append(values)
        return check_hard_filters(store.view(cutoff), ISIN, block)


def verdict_of(result, number: int, name: str | None = None) -> Verdict:
    """The verdict of a single check."""
    hits = [
        c for c in result.checks if c.number == number and (name is None or c.name == name)
    ]
    assert len(hits) == 1, f"Check {number}/{name} not unique: {result.checks}"
    return hits[0].verdict


# ---------------------------------------------------------------------------
# Complete sets
# ---------------------------------------------------------------------------


class TestComplete:
    @pytest.mark.parametrize("block", [BuildingBlock.K1, BuildingBlock.K2_MONEY_MARKET])
    def test_blocks_with_concrete_index_are_eligible(self, block) -> None:
        r = evaluate(block, passing_values(block))
        assert r.eligible, r.checks
        assert r.verdict is Verdict.FULFILLED
        assert r.new is False

    @pytest.mark.parametrize(
        "block",
        [BuildingBlock.K2_EUR_GOVERNMENT_BONDS, BuildingBlock.K2_GLOBAL_BONDS,
         BuildingBlock.S_GOLD, BuildingBlock.S_FACTOR],
    )
    def test_index_family_stays_open(self, block) -> None:
        """A5.5 names only an index family here — do not guess, leave it open."""
        r = evaluate(block, passing_values(block))
        assert verdict_of(r, 2) is Verdict.OPEN
        assert r.verdict is Verdict.OPEN
        assert not r.eligible
        not_fulfilled = [c for c in r.checks if c.verdict is not Verdict.FULFILLED]
        assert [c.number for c in not_fulfilled] == [2]

    @pytest.mark.parametrize(
        ("block", "numbers"),
        [
            (BuildingBlock.K1, [1, 1, 1, 2, 3, 4, 5]),
            (BuildingBlock.K2_MONEY_MARKET, [1, 1, 1, 2, 3, 4]),
            (BuildingBlock.K2_EUR_GOVERNMENT_BONDS, [1, 1, 1, 2, 3, 4]),
            (BuildingBlock.K2_GLOBAL_BONDS, [1, 1, 1, 2, 3, 4, 6]),
            (BuildingBlock.S_GOLD, [1, 1, 1, 2, 3, 4]),
            (BuildingBlock.S_FACTOR, [1, 1, 1, 2, 3, 4, 5]),
        ],
    )
    def test_which_filters_run_per_block(self, block, numbers) -> None:
        r = evaluate(block, passing_values(block))
        assert [c.number for c in r.checks] == numbers

    def test_block_as_text(self) -> None:
        r = evaluate("K1 Global equities", passing_values(BuildingBlock.K1))
        assert r.building_block is BuildingBlock.K1

    def test_unknown_block_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            evaluate("K3", passing_values(BuildingBlock.K1))


# ---------------------------------------------------------------------------
# Filter 1: UCITS / gold ETC, trading venue, KID
# ---------------------------------------------------------------------------


class TestFilter1:
    def test_no_ucits_is_violated(self) -> None:
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, ucits=False))
        assert verdict_of(r, 1, "UCITS") is Verdict.VIOLATED
        assert r.verdict is Verdict.VIOLATED

    def test_no_german_kid_is_violated(self) -> None:
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, kid_language_de=False))
        assert verdict_of(r, 1, "KID in German") is Verdict.VIOLATED

    def test_not_on_xetra_is_open_not_violated(self) -> None:
        """A5.2 permits any German trading venue; the field knows only Xetra."""
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, xetra_tradable=False))
        assert verdict_of(r, 1, "Xetra") is Verdict.OPEN
        assert not r.eligible

    def test_gold_needs_delivery_claim_instead_of_ucits(self) -> None:
        """A gold ETC is not a UCITS fund; for S-Gold the delivery claim counts."""
        r = evaluate(BuildingBlock.S_GOLD, passing_values(BuildingBlock.S_GOLD, ucits=False))
        assert verdict_of(r, 1, "ETC with delivery claim") is Verdict.FULFILLED

        without = evaluate(
            BuildingBlock.S_GOLD,
            passing_values(BuildingBlock.S_GOLD, gold_etc_delivery_claim=False),
        )
        assert verdict_of(without, 1, "ETC with delivery claim") is Verdict.VIOLATED


# ---------------------------------------------------------------------------
# Filter 2: index
# ---------------------------------------------------------------------------


class TestFilter2:
    @pytest.mark.parametrize("index", ["MSCI ACWI", "MSCI ACWI IMI", "FTSE All-World"])
    def test_k1_indices_from_a5_5(self, index) -> None:
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, index_name=index))
        assert verdict_of(r, 2) is Verdict.FULFILLED

    @pytest.mark.parametrize("index", ["MSCI World", "MSCI ACWI ex USA", "€STR"])
    def test_other_index_is_violated_for_k1(self, index) -> None:
        """World + EM is a combination at the user's request (A5.4), not a single fund for K1."""
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, index_name=index))
        assert verdict_of(r, 2) is Verdict.VIOLATED

    def test_money_market_needs_estr(self) -> None:
        r = evaluate(BuildingBlock.K2_MONEY_MARKET,
                     passing_values(BuildingBlock.K2_MONEY_MARKET, index_name="MSCI ACWI"))
        assert verdict_of(r, 2) is Verdict.VIOLATED


# ---------------------------------------------------------------------------
# Filter 3: fund size
# ---------------------------------------------------------------------------


class TestFilter3:
    @pytest.mark.parametrize(
        ("block", "size", "expected"),
        [
            (BuildingBlock.K2_EUR_GOVERNMENT_BONDS, "100000000", Verdict.FULFILLED),  # ≥, limit counts
            (BuildingBlock.K2_EUR_GOVERNMENT_BONDS, "99999999.99", Verdict.VIOLATED),
            (BuildingBlock.K2_EUR_GOVERNMENT_BONDS, "50000000", Verdict.VIOLATED),
            (BuildingBlock.K2_EUR_GOVERNMENT_BONDS, "10000000", Verdict.VIOLATED),
            (BuildingBlock.S_FACTOR, "100000000", Verdict.FULFILLED),
            (BuildingBlock.S_GOLD, "99999999.99", Verdict.VIOLATED),
            (BuildingBlock.K2_GLOBAL_BONDS, "100000000", Verdict.FULFILLED),
            (BuildingBlock.K1, "500000000", Verdict.FULFILLED),
            (BuildingBlock.K1, "499999999.99", Verdict.VIOLATED),
            (BuildingBlock.K1, "100000000", Verdict.VIOLATED),
            (BuildingBlock.K2_MONEY_MARKET, "500000000", Verdict.FULFILLED),
            (BuildingBlock.K2_MONEY_MARKET, "499999999.99", Verdict.VIOLATED),
        ],
    )
    def test_thresholds(self, block, size, expected) -> None:
        r = evaluate(block, passing_values(block, fund_size=Decimal(size)))
        assert verdict_of(r, 3) is expected


# Placeholder rates; 2026-08-28 is a Friday.
FRIDAY = dt.date(2026, 8, 28)
SUNDAY = dt.date(2026, 8, 30)
MONDAY = dt.date(2026, 8, 31)


def usd_size(amount: str, as_of: dt.date = FRIDAY) -> FieldValue:
    """A verified fund size in USD from a factsheet, retrieved within the cut-off date."""
    return make_value("fund_size", Decimal(amount), unit="USD", as_of=as_of,
                      source_type=SourceType.FACTSHEET,
                      retrieved_at=dt.datetime(2026, 9, 3, tzinfo=UTC))


def usd_rate(rate: str, as_of: dt.date = FRIDAY, *, retrieved_at=None,
             status=VerificationStatus.VERIFIED) -> FxRate:
    return FxRate(
        currency="USD", rate=Decimal(rate), source_url=URL_ECB, status=status, as_of=as_of,
        retrieved_at=retrieved_at or dt.datetime(as_of.year, as_of.month, as_of.day, 15,
                                                 tzinfo=UTC),
    )


def k1_with(*extra) -> list:
    """The passing K1 set, with the fund size (and its rates) given by the test."""
    return passing_values(BuildingBlock.K1, fund_size=None) + list(extra)


def reason_of(result, number: int) -> str:
    (reason,) = [c.reason for c in result.checks if c.number == number]
    return reason


class TestFilter3Currency:
    """A5.2 no. 3 with a fund size in USD: the thresholds are EUR (A5.1, v1.4)."""

    def test_above_threshold_in_usd_but_below_in_eur_is_violated(self) -> None:
        # 520m ≥ 500m in USD — at 1.0843 USD per EUR only 479.6m EUR.
        r = evaluate(BuildingBlock.K1, k1_with(usd_size("520000000"), usd_rate("1.0843")))
        assert verdict_of(r, 3) is Verdict.VIOLATED

    def test_below_threshold_in_usd_but_above_in_eur_is_fulfilled(self) -> None:
        # 480m < 500m in USD — at 0.9500 USD per EUR 505.3m EUR.
        r = evaluate(BuildingBlock.K1, k1_with(usd_size("480000000"), usd_rate("0.9500")))
        assert verdict_of(r, 3) is Verdict.FULFILLED
        assert r.eligible

    @pytest.mark.parametrize(
        ("amount", "expected"),
        [("542150000", Verdict.FULFILLED), ("542149999.99", Verdict.VIOLATED)],
    )
    def test_limit_counts_after_conversion(self, amount, expected) -> None:
        """500m EUR × 1.0843 = 542.15m USD exactly; ≥, so the limit counts."""
        r = evaluate(BuildingBlock.K1, k1_with(usd_size(amount), usd_rate("1.0843")))
        assert verdict_of(r, 3) is expected

    def test_rate_of_its_own_as_of_date_not_the_latest(self) -> None:
        """A later rate — today's, on a re-run — must not move a stored fund size."""
        r = evaluate(BuildingBlock.K1, k1_with(
            usd_size("520000000"), usd_rate("1.0843"), usd_rate("0.9500", dt.date(2026, 9, 24)),
        ))
        assert verdict_of(r, 3) is Verdict.VIOLATED
        assert "of 2026-08-28" in reason_of(r, 3)

    def test_weekend_carries_fridays_rate_forward(self) -> None:
        """No ECB rate on a Sunday: Friday's applies (v1.5, as in G4), never Monday's."""
        assert (FRIDAY.weekday(), SUNDAY.weekday()) == (4, 6)
        r = evaluate(BuildingBlock.K1, k1_with(
            usd_size("520000000", SUNDAY), usd_rate("1.0843", FRIDAY), usd_rate("0.9500", MONDAY),
        ))
        assert verdict_of(r, 3) is Verdict.VIOLATED  # Monday's rate would have let it pass
        reason = reason_of(r, 3)
        assert "1.0843 USD per EUR of 2026-08-28, carried forward to 2026-08-30" in reason
        assert "0.9500" not in reason

    def test_no_rate_on_or_before_the_as_of_date_is_open(self) -> None:
        """Only a later rate is known: nothing to carry forward, nothing guessed backwards."""
        r = evaluate(BuildingBlock.K1, k1_with(usd_size("900000000"), usd_rate("1.0843", MONDAY)))
        assert verdict_of(r, 3) is Verdict.OPEN
        assert "no USD reference rate on or before 2026-08-28" in reason_of(r, 3)
        assert not r.eligible

    def test_rate_retrieved_after_the_cutoff_does_not_count(self) -> None:
        """A5.1: a converted fund size exists only if the rate, too, was retrieved by then."""
        late = dt.datetime(2026, 10, 1, tzinfo=UTC)
        values = k1_with(usd_size("900000000"), usd_rate("1.0843", retrieved_at=late))
        assert verdict_of(evaluate(BuildingBlock.K1, values, CUTOFF), 3) is Verdict.OPEN
        assert verdict_of(evaluate(BuildingBlock.K1, values, late), 3) is Verdict.FULFILLED

    def test_unverified_rate_is_open(self) -> None:
        r = evaluate(BuildingBlock.K1, k1_with(
            usd_size("900000000"), usd_rate("1.0843", status=VerificationStatus.UNVERIFIED),
        ))
        assert verdict_of(r, 3) is Verdict.OPEN
        assert "UNVERIFIED" in reason_of(r, 3)

    def test_eur_value_needs_no_rate(self) -> None:
        """Not a single rate in the store: a EUR fund size is decided nonetheless."""
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1))
        assert verdict_of(r, 3) is Verdict.FULFILLED
        assert "fund_size = 500000000 EUR" in reason_of(r, 3)

    def test_reason_names_value_rate_and_its_date(self) -> None:
        """Enough to recompute the verdict by hand."""
        r = evaluate(BuildingBlock.K1, k1_with(usd_size("520000000"), usd_rate("1.0843")))
        reason = reason_of(r, 3)
        for part in (
            "fund_size = 520000000 USD (factsheet, as of 2026-08-28)",
            "ECB reference rate 1.0843 USD per EUR of 2026-08-28",
            URL_ECB,
            "required ≥ 500000000 EUR = 542150000.0000 USD",
        ):
            assert part in reason
        assert "carried forward" not in reason


# ---------------------------------------------------------------------------
# Filter 4: history
# ---------------------------------------------------------------------------


class TestFilter4:
    @pytest.mark.parametrize(
        ("inception", "cutoff", "years"),
        [
            (dt.date(2023, 1, 2), dt.date(2026, 9, 25), 2),  # 2023 not full
            (dt.date(2023, 1, 1), dt.date(2026, 9, 25), 3),  # 2023 full
            (dt.date(2022, 12, 31), dt.date(2026, 9, 25), 3),  # 2023–2025
            (dt.date(2025, 6, 1), dt.date(2026, 1, 1), 0),
            (dt.date(2025, 1, 1), dt.date(2026, 1, 1), 1),
            (dt.date(2025, 1, 1), dt.date(2025, 12, 31), 0),  # the current year never counts
            (dt.date(2027, 1, 1), dt.date(2026, 9, 25), 0),  # inception after the cut-off date
        ],
    )
    def test_full_calendar_years(self, inception, cutoff, years) -> None:
        assert full_calendar_years(inception, cutoff) == years

    @pytest.mark.parametrize(
        ("inception", "new"),
        [
            (dt.date(2022, 6, 1), False),  # 2023, 2024, 2025
            (dt.date(2023, 6, 1), True),  # 2024, 2025
            (dt.date(2025, 6, 1), True),  # none
        ],
    )
    def test_younger_funds_are_new_but_not_excluded(self, inception, new) -> None:
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, inception_date=inception))
        assert r.new is new
        assert verdict_of(r, 4) is Verdict.FULFILLED
        assert r.eligible

    def test_cutoff_of_the_view_counts(self) -> None:
        """The same fund, two cut-off dates: new first, then no longer."""
        values = passing_values(BuildingBlock.K1, inception_date=dt.date(2023, 6, 1))
        assert evaluate(BuildingBlock.K1, values, dt.datetime(2026, 12, 31, tzinfo=UTC)).new is True
        assert evaluate(BuildingBlock.K1, values, dt.datetime(2027, 1, 1, tzinfo=UTC)).new is False


# ---------------------------------------------------------------------------
# Filters 5 and 6
# ---------------------------------------------------------------------------


class TestFilter5And6:
    @pytest.mark.parametrize("block", [BuildingBlock.K1, BuildingBlock.S_FACTOR])
    def test_equity_blocks_need_equity_fund(self, block) -> None:
        r = evaluate(block, passing_values(block, equity_fund_invstg=False))
        assert verdict_of(r, 5) is Verdict.VIOLATED

    def test_global_bonds_need_eur_hedging(self) -> None:
        r = evaluate(BuildingBlock.K2_GLOBAL_BONDS,
                     passing_values(BuildingBlock.K2_GLOBAL_BONDS, currency_hedged=False))
        assert verdict_of(r, 6) is Verdict.VIOLATED

    def test_euro_bonds_need_no_hedging(self) -> None:
        r = evaluate(BuildingBlock.K2_EUR_GOVERNMENT_BONDS,
                     passing_values(BuildingBlock.K2_EUR_GOVERNMENT_BONDS, currency_hedged=False))
        assert 6 not in [c.number for c in r.checks]


# ---------------------------------------------------------------------------
# Unverified and missing values — the most important block
# ---------------------------------------------------------------------------


class TestUnverified:
    def test_unverified_value_never_passes(self) -> None:
        """A second-hand fund size far above the threshold: open nonetheless."""
        values = passing_values(BuildingBlock.K1, fund_size=None) + [
            make_value("fund_size", Decimal("99000000000"), status=VerificationStatus.UNVERIFIED,
                       source_type=SourceType.SECONDARY),
        ]
        r = evaluate(BuildingBlock.K1, values)
        assert verdict_of(r, 3) is Verdict.OPEN
        assert not r.eligible
        reason = next(c.reason for c in r.checks if c.number == 3)
        assert "UNVERIFIED" in reason
        assert "primary document" in reason

    def test_unverified_from_primary_document_does_not_pass_either(self) -> None:
        """Copied from the KID but not yet reconciled: open."""
        values = passing_values(BuildingBlock.K1, ucits=None) + [
            make_value("ucits", True, status=VerificationStatus.UNVERIFIED),
        ]
        assert verdict_of(evaluate(BuildingBlock.K1, values), 1, "UCITS") is Verdict.OPEN

    def test_unverified_violation_is_open_not_violated(self) -> None:
        """Second hand does not exclude for good either."""
        values = passing_values(BuildingBlock.K1, fund_size=None) + [
            make_value("fund_size", Decimal("1"), status=VerificationStatus.UNVERIFIED,
                       source_type=SourceType.SECONDARY),
        ]
        assert verdict_of(evaluate(BuildingBlock.K1, values), 3) is Verdict.OPEN

    @pytest.mark.parametrize(
        ("field", "number"),
        [("ucits", 1), ("index_name", 2), ("fund_size", 3), ("inception_date", 4),
         ("equity_fund_invstg", 5)],
    )
    def test_missing_value_is_open(self, field, number) -> None:
        r = evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1, **{field: None}))
        open_checks = [c for c in r.checks if c.verdict is Verdict.OPEN]
        assert [c.number for c in open_checks] == [number]
        assert "no value" in open_checks[0].reason
        assert not r.eligible

    def test_unverified_history_is_open_and_not_new(self) -> None:
        values = passing_values(BuildingBlock.K1, inception_date=None) + [
            make_value("inception_date", dt.date(2025, 6, 1),
                       status=VerificationStatus.UNVERIFIED),
        ]
        r = evaluate(BuildingBlock.K1, values)
        assert verdict_of(r, 4) is Verdict.OPEN
        assert r.new is False

    def test_violated_beats_open(self) -> None:
        """A verified violation excludes, whatever else is open."""
        r = evaluate(BuildingBlock.K1,
                     passing_values(BuildingBlock.K1, ucits=False, fund_size=None))
        assert verdict_of(r, 3) is Verdict.OPEN
        assert r.verdict is Verdict.VIOLATED


# ---------------------------------------------------------------------------
# Point-in-time in the filters
# ---------------------------------------------------------------------------


class TestCutoff:
    def test_value_after_the_cutoff_does_not_count(self) -> None:
        late = dt.datetime(2026, 10, 1, tzinfo=UTC)
        values = passing_values(BuildingBlock.K1, fund_size=None) + [
            make_value("fund_size", Decimal("600000000"), retrieved_at=late),
        ]
        assert verdict_of(evaluate(BuildingBlock.K1, values, CUTOFF), 3) is Verdict.OPEN
        assert verdict_of(evaluate(BuildingBlock.K1, values, late), 3) is Verdict.FULFILLED

    def test_later_correction_does_not_change_earlier_result(self) -> None:
        """Fund size drops below the threshold after the cut-off — the result as of then stays."""
        values = passing_values(BuildingBlock.K1) + [
            make_value("fund_size", Decimal("1"),
                       retrieved_at=dt.datetime(2026, 10, 1, tzinfo=UTC)),
        ]
        assert evaluate(BuildingBlock.K1, values, CUTOFF).eligible
        later = evaluate(BuildingBlock.K1, values, dt.datetime(2026, 10, 2, tzinfo=UTC))
        assert verdict_of(later, 3) is Verdict.VIOLATED

    def test_result_carries_the_cutoff(self) -> None:
        assert evaluate(BuildingBlock.K1, passing_values(BuildingBlock.K1)).cut_off == CUTOFF
