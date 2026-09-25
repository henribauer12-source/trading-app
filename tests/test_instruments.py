"""Tests of the instrument master data (investment spec A5.1).

**All ISINs, URLs and numbers here are placeholders.** The ISINs start with
``XX`` (no country code) and otherwise consist of zeros; their check digits
were computed by hand according to ISO 6166. The URLs end in ``.invalid``
(RFC 2606). No number in this file is researched.

The most important block is ``TestLeakage``, following the pattern of
``tests/test_bitemporal.py``.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trading_app.instruments import (
    FIELDS,
    SOURCE_PRECEDENCE,
    Distribution,
    FieldValue,
    FieldValueValidationError,
    FxRate,
    FxRateGapError,
    InstrumentStore,
    Replication,
    SourceType,
    VerificationStatus,
    load_source_file,
)

UTC = dt.timezone.utc

# Placeholder ISINs, check digit computed by hand.
ISIN_A = "XX0000000002"
ISIN_B = "XX0000000010"
URL_KID = "https://issuer.invalid/kid.pdf"
URL_FACTSHEET = "https://issuer.invalid/factsheet.pdf"


def ts(year: int, month: int, day: int, hour: int = 12) -> dt.datetime:
    return dt.datetime(year, month, day, hour, tzinfo=UTC)


def make_value(
    field: str = "ter",
    value: object = Decimal("0.1234"),
    *,
    isin: str = ISIN_A,
    as_of: dt.date = dt.date(2026, 2, 15),
    retrieved_at: dt.datetime | None = None,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    source_type: SourceType = SourceType.KID,
    source_url: str = URL_KID,
    period: str = "",
    unit: str | None = None,
) -> FieldValue:
    """Builds a valid FieldValue; by default it is retrieved on the as-of date.

    A fund size must name its currency; without ``unit`` it is EUR here, in
    the helper only — ``FieldValue`` itself defaults nothing.
    """
    if unit is None and field == "fund_size":
        unit = "EUR"
    return FieldValue(
        isin=isin,
        field=field,
        value=value,
        source_url=source_url,
        source_type=source_type,
        status=status,
        as_of=as_of,
        retrieved_at=retrieved_at or ts(as_of.year, as_of.month, as_of.day),
        period=period,
        unit=unit,
    )


URL_ECB = "https://ecb.invalid/eurofxref-hist.csv"


def make_rate(
    rate: object = Decimal("1.0843"),
    as_of: dt.date = dt.date(2026, 8, 28),
    *,
    retrieved_at: dt.datetime | None = None,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    currency: str = "USD",
) -> FxRate:
    """A placeholder ECB rate, by default retrieved on its reference date."""
    return FxRate(
        currency=currency,
        rate=rate,
        source_url=URL_ECB,
        status=status,
        as_of=as_of,
        retrieved_at=retrieved_at or ts(as_of.year, as_of.month, as_of.day, 16),
    )


@pytest.fixture
def store():
    with InstrumentStore(":memory:") as s:
        yield s


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestFieldValueValidation:
    def test_valid_value_is_accepted(self) -> None:
        value = make_value("ter", Decimal("0.1234"))
        assert value.value == Decimal("0.1234")
        assert isinstance(value.value, Decimal)
        assert value.unit == "% p. a."  # set from FIELDS

    def test_float_is_rejected(self) -> None:
        """CLAUDE.md: money amounts and costs in Decimal, never float."""
        with pytest.raises(FieldValueValidationError, match="float is forbidden"):
            make_value("ter", 0.1234)

    def test_bool_is_not_a_number(self) -> None:
        """True is 1 in Python — as a TER that would be a silent typo."""
        with pytest.raises(FieldValueValidationError, match="ter"):
            make_value("ter", True)

    def test_comma_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="no comma"):
            make_value("ter", "0,1234")

    def test_nan_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="finite"):
            make_value("ter", Decimal("NaN"))

    def test_text_and_int_become_decimal(self) -> None:
        assert make_value("ter", "0.1234").value == Decimal("0.1234")
        assert make_value("fund_size", 123_456_789).value == Decimal(123_456_789)

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="unknown field"):
            make_value("price", Decimal("1"))

    def test_isin_with_wrong_check_digit_is_rejected(self) -> None:
        """A transposed digit in a hand-maintained list."""
        with pytest.raises(FieldValueValidationError, match="check digit"):
            make_value(isin="XX0000000003")

    @pytest.mark.parametrize("isin", ["XX000000002", "xx0000000002", "XX000000000A", "", None])
    def test_isin_in_wrong_format_is_rejected(self, isin) -> None:
        with pytest.raises(FieldValueValidationError, match="format"):
            make_value(isin=isin)

    def test_naive_retrieved_at_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="timezone-naive"):
            make_value(retrieved_at=dt.datetime(2026, 3, 1, 10))

    def test_retrieved_at_is_normalised_to_utc(self) -> None:
        berlin = dt.timezone(dt.timedelta(hours=1))
        value = make_value(retrieved_at=dt.datetime(2026, 3, 1, 10, tzinfo=berlin))
        assert value.retrieved_at.utcoffset() == dt.timedelta(0)
        assert value.retrieved_at.hour == 9

    def test_retrieval_before_as_of_is_rejected(self) -> None:
        """Like available_at >= event_time (K2): no retrieval before the document."""
        with pytest.raises(FieldValueValidationError, match="K2"):
            make_value(as_of=dt.date(2026, 8, 31), retrieved_at=ts(2026, 8, 30))

    def test_retrieval_on_as_of_date_is_allowed(self) -> None:
        value = make_value(as_of=dt.date(2026, 8, 31), retrieved_at=ts(2026, 8, 31, 0))
        assert value.as_of == dt.date(2026, 8, 31)

    def test_second_hand_cannot_be_verified(self) -> None:
        with pytest.raises(FieldValueValidationError, match="second-hand"):
            make_value(source_type=SourceType.SECONDARY, status=VerificationStatus.VERIFIED)

    def test_second_hand_as_unverified_is_allowed(self) -> None:
        """Second-hand values may be stored — labelled."""
        value = make_value(source_type=SourceType.SECONDARY, status=VerificationStatus.UNVERIFIED)
        assert value.status is VerificationStatus.UNVERIFIED

    def test_status_and_source_as_text(self) -> None:
        """That is how they come out of the source file."""
        value = make_value(source_type="factsheet", status="UNVERIFIED")
        assert value.source_type is SourceType.FACTSHEET
        assert value.status is VerificationStatus.UNVERIFIED

    @pytest.mark.parametrize("status", ["verified", "CHECKED", ""])
    def test_unknown_status_is_rejected(self, status) -> None:
        with pytest.raises(FieldValueValidationError, match="not allowed"):
            make_value(status=status)

    def test_wrong_unit_is_rejected(self) -> None:
        """A TER in basis points next to one in percent would be a factor of 100."""
        with pytest.raises(FieldValueValidationError, match="is stored in"):
            make_value("ter", Decimal("12"), unit="basis points")

    @pytest.mark.parametrize("url", ["", "kid.pdf", "ftp://issuer.invalid/kid.pdf", None])
    def test_source_is_mandatory(self, url) -> None:
        with pytest.raises(FieldValueValidationError, match="source_url"):
            make_value(source_url=url)

    def test_annual_value_needs_a_year(self) -> None:
        with pytest.raises(FieldValueValidationError, match="calendar year"):
            make_value("tracking_difference", Decimal("-0.0123"))

    def test_annual_value_is_final_only_at_year_end(self) -> None:
        """A TD for 2026 cannot be in a factsheet from August 2026."""
        with pytest.raises(FieldValueValidationError, match="year end"):
            make_value(
                "tracking_difference", Decimal("-0.0123"),
                period="2026", as_of=dt.date(2026, 8, 31),
            )

    def test_annual_value_on_31_december_is_allowed(self) -> None:
        value = make_value(
            "tracking_difference", Decimal("-0.0123"),
            period="2025", as_of=dt.date(2025, 12, 31),
        )
        assert value.period == "2025"

    def test_period_on_ordinary_field_is_forbidden(self) -> None:
        with pytest.raises(FieldValueValidationError, match="no periods"):
            make_value("ter", Decimal("0.1234"), period="2025")

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("ucits", "yes"),
            ("ucits", 1),
            ("domicile", "ie"),
            ("domicile", "IRL"),
            ("replication_method", "synthetic"),
            ("distribution_type", "monthly"),
            ("inception_date", dt.datetime(2015, 6, 1, tzinfo=UTC)),
            ("inception_date", "01.06.2015"),
            ("index_name", "   "),
        ],
    )
    def test_wrong_type_per_field_is_rejected(self, field, value) -> None:
        with pytest.raises(FieldValueValidationError, match=field):
            make_value(field, value)

    def test_field_value_is_immutable(self) -> None:
        value = make_value()
        with pytest.raises(AttributeError):
            value.value = Decimal("9")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Decimal and types through the database
# ---------------------------------------------------------------------------


class TestDatabaseRoundTrip:
    def test_decimal_comes_back_exactly(self, store) -> None:
        """More digits than a float can hold: a detour via float would show here."""
        exact = Decimal("0.1234567890123456789")
        store.append([make_value("ter", exact)])
        back = store.view(ts(2026, 9, 1)).field(ISIN_A, "ter").value
        assert isinstance(back, Decimal)
        assert back == exact
        assert str(back) == "0.1234567890123456789"

    def test_trailing_zeros_stay_as_published(self, store) -> None:
        store.append([make_value("ter", Decimal("0.1230"))])
        assert str(store.view(ts(2026, 9, 1)).field(ISIN_A, "ter").value) == "0.1230"

    def test_td_is_not_rounded(self, store) -> None:
        """The materiality threshold of 0.05 pp is a matter for scoring, not for storage."""
        store.append([
            make_value("tracking_difference", Decimal("-0.0123"),
                       period="2025", as_of=dt.date(2026, 1, 31)),
        ])
        td = store.view(ts(2026, 9, 1)).series(ISIN_A, "tracking_difference")["2025"]
        assert td.value == Decimal("-0.0123")

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("fund_size", Decimal("123456789012.34")),
            ("xlm", Decimal("7.5")),
            ("transaction_costs_kid", Decimal("-0.0100")),  # the sign is kept
            ("ucits", True),
            ("xetra_tradable", False),
            ("inception_date", dt.date(2015, 6, 1)),
            ("domicile", "XX"),
            ("index_name", "Placeholder index"),
            ("replication_method", Replication.SYNTHETIC_MULTIPLE_COUNTERPARTIES),
            ("distribution_type", Distribution.ACCUMULATING),
        ],
    )
    def test_every_type_survives_the_database(self, store, field, value) -> None:
        store.append([make_value(field, value)])
        back = store.view(ts(2026, 9, 1)).field(ISIN_A, field).value
        assert back == value
        assert type(back) is type(value)

    def test_every_field_in_fields_has_a_type(self) -> None:
        """The mandatory fields from A5.2/A5.3 are all registered."""
        required = {
            "ter", "tracking_difference", "fund_size", "replication_method", "domicile",
            "inception_date", "index_name", "distribution_type", "ucits", "kid_language_de",
            "xetra_tradable", "transaction_costs_kid", "xlm", "equity_fund_invstg",
            "currency_hedged", "holding_costs",
        }
        assert required <= set(FIELDS)
        assert [f for f, typ in FIELDS.items() if typ.per_year] == ["tracking_difference"]


# ---------------------------------------------------------------------------
# Point-in-time
# ---------------------------------------------------------------------------


class TestPointInTime:
    def test_empty_view_is_not_an_error(self, store) -> None:
        view = store.view(ts(2026, 9, 1))
        assert view.field(ISIN_A, "ter") is None
        assert view.series(ISIN_A, "tracking_difference") == {}
        assert view.isins() == []

    def test_august_factsheet_is_missing_as_of_june(self, store) -> None:
        """The example from the brief: as-of date 31 Aug, view as of 30 Jun."""
        store.append([
            make_value("fund_size", Decimal("123456789"), source_type=SourceType.FACTSHEET,
                       source_url=URL_FACTSHEET, as_of=dt.date(2026, 8, 31),
                       retrieved_at=ts(2026, 9, 3)),
        ])
        assert store.view(ts(2026, 6, 30)).field(ISIN_A, "fund_size") is None
        assert store.view(ts(2026, 9, 4)).field(ISIN_A, "fund_size") is not None

    def test_counts_from_retrieval_not_from_as_of(self, store) -> None:
        """Between as-of date and retrieval the app did not know the value yet."""
        store.append([make_value(as_of=dt.date(2026, 2, 15), retrieved_at=ts(2026, 3, 1))])
        assert store.view(ts(2026, 2, 20)).field(ISIN_A, "ter") is None
        assert store.view(ts(2026, 3, 2)).field(ISIN_A, "ter") is not None

    def test_cutoff_is_inclusive(self, store) -> None:
        store.append([make_value(retrieved_at=ts(2026, 3, 1))])
        assert store.view(ts(2026, 3, 1)).field(ISIN_A, "ter") is not None

    def test_one_second_before_still_invisible(self, store) -> None:
        store.append([make_value(retrieved_at=ts(2026, 3, 1))])
        just_before = ts(2026, 3, 1) - dt.timedelta(seconds=1)
        assert store.view(just_before).field(ISIN_A, "ter") is None

    def test_correction_applies_only_from_its_retrieval(self, store) -> None:
        """A corrected TER is a new row with a later retrieved_at."""
        store.append([make_value(value=Decimal("0.1234"), retrieved_at=ts(2026, 3, 1))])
        store.append([make_value(value=Decimal("0.4321"), retrieved_at=ts(2026, 6, 1))])

        assert store.view(ts(2026, 4, 1)).field(ISIN_A, "ter").value == Decimal("0.1234")
        assert store.view(ts(2026, 7, 1)).field(ISIN_A, "ter").value == Decimal("0.4321")

    def test_newer_as_of_beats_older_document_recorded_later(self, store) -> None:
        """Whoever adds last year's KID afterwards does not displace the current one."""
        store.append([make_value(value=Decimal("0.1111"), as_of=dt.date(2026, 2, 15),
                                 retrieved_at=ts(2026, 3, 1))])
        store.append([make_value(value=Decimal("0.2222"), as_of=dt.date(2025, 2, 10),
                                 retrieved_at=ts(2026, 9, 1))])

        assert store.view(ts(2026, 9, 10)).field(ISIN_A, "ter").value == Decimal("0.1111")

    def test_every_field_has_its_own_provenance(self, store) -> None:
        """The core of A5.1: TER from the KID, fund size from the factsheet."""
        store.append([
            make_value("ter", Decimal("0.1234"), as_of=dt.date(2026, 2, 15),
                       retrieved_at=ts(2026, 3, 1)),
            make_value("fund_size", Decimal("123456789"), source_type=SourceType.FACTSHEET,
                       source_url=URL_FACTSHEET, as_of=dt.date(2026, 8, 31),
                       retrieved_at=ts(2026, 9, 3)),
        ])
        view = store.view(ts(2026, 9, 10))
        ter = view.field(ISIN_A, "ter")
        size = view.field(ISIN_A, "fund_size")

        assert (ter.source_url, ter.source_type, ter.as_of) == (
            URL_KID, SourceType.KID, dt.date(2026, 2, 15)
        )
        assert (size.source_url, size.source_type, size.as_of) == (
            URL_FACTSHEET, SourceType.FACTSHEET, dt.date(2026, 8, 31)
        )
        assert ter.retrieved_at == ts(2026, 3, 1)
        assert size.retrieved_at == ts(2026, 9, 3)

    def test_series_returns_all_years(self, store) -> None:
        store.append([
            make_value("tracking_difference", Decimal(value), period=year,
                       as_of=dt.date(2026, 1, 31), retrieved_at=ts(2026, 2, 5))
            for year, value in (("2025", "0.0300"), ("2023", "-0.0100"), ("2024", "0.0200"))
        ])
        series = store.view(ts(2026, 9, 1)).series(ISIN_A, "tracking_difference")
        assert list(series) == ["2023", "2024", "2025"]
        assert [v.value for v in series.values()] == [
            Decimal("-0.0100"), Decimal("0.0200"), Decimal("0.0300")
        ]

    def test_field_and_series_cannot_be_mixed_up(self, store) -> None:
        view = store.view(ts(2026, 9, 1))
        with pytest.raises(FieldValueValidationError, match=r"series\(\)"):
            view.field(ISIN_A, "tracking_difference")
        with pytest.raises(FieldValueValidationError, match=r"field\(\)"):
            view.series(ISIN_A, "ter")

    def test_instruments_stay_separate(self, store) -> None:
        store.append([
            make_value(isin=ISIN_A, value=Decimal("0.1111")),
            make_value(isin=ISIN_B, value=Decimal("0.2222")),
        ])
        view = store.view(ts(2026, 9, 1))
        assert view.field(ISIN_A, "ter").value == Decimal("0.1111")
        assert view.field(ISIN_B, "ter").value == Decimal("0.2222")
        assert view.isins() == [ISIN_A, ISIN_B]

    def test_isins_respect_the_cutoff(self, store) -> None:
        """Inclusive here too: retrieved exactly at the cut-off date is known."""
        store.append([make_value(isin=ISIN_B, retrieved_at=ts(2026, 5, 1))])
        assert store.view(ts(2026, 4, 1)).isins() == []
        assert store.view(ts(2026, 5, 1) - dt.timedelta(seconds=1)).isins() == []
        assert store.view(ts(2026, 5, 1)).isins() == [ISIN_B]

    def test_view_needs_tz_aware_cutoff(self, store) -> None:
        with pytest.raises(FieldValueValidationError, match="timezone-naive"):
            store.view(dt.datetime(2026, 9, 1))


# ---------------------------------------------------------------------------
# KID precedence (A5.1, v1.4)
# ---------------------------------------------------------------------------


def factsheet_value(field: str = "ter", value: object = Decimal("0.2222"), **kwargs) -> FieldValue:
    kwargs.setdefault("as_of", dt.date(2026, 8, 31))
    kwargs.setdefault("retrieved_at", ts(2026, 9, 3))
    return make_value(field, value, source_type=SourceType.FACTSHEET,
                      source_url=URL_FACTSHEET, **kwargs)


def ranked_value(source_type: SourceType, value: Decimal, as_of: dt.date) -> FieldValue:
    """A TER from any document class, retrieved three days after its as-of date.

    A second-hand value can only be UNVERIFIED; every other one is VERIFIED.
    """
    status = (VerificationStatus.UNVERIFIED if source_type is SourceType.SECONDARY
              else VerificationStatus.VERIFIED)
    return make_value(value=value, source_type=source_type, status=status, as_of=as_of,
                      retrieved_at=ts(as_of.year, as_of.month, as_of.day) + dt.timedelta(days=3))


class TestDocumentClassPrecedence:
    """The full order over document classes (A5.1, v1.6)."""

    def test_order_as_specified(self) -> None:
        assert SOURCE_PRECEDENCE == (
            SourceType.STATUTE,
            SourceType.KID,
            SourceType.ANNUAL_REPORT,
            SourceType.PROSPECTUS,
            SourceType.FACTSHEET,
            SourceType.ISSUER,
            SourceType.EXCHANGE,
            SourceType.SECONDARY,
        )

    def test_every_source_type_is_ranked_exactly_once(self) -> None:
        """A new source type must be placed deliberately, not silently sort last."""
        assert sorted(SOURCE_PRECEDENCE) == sorted(SourceType)

    @pytest.mark.parametrize(
        ("higher", "lower"), list(itertools.combinations(SOURCE_PRECEDENCE, 2))
    )
    def test_higher_class_beats_newer_lower_class(self, store, higher, lower) -> None:
        """Every pair of distinct classes is strictly ordered — a total order.

        The lower class has the later as-of date, the later retrieval and the
        later write, so every tiebreaker favours it: only the class can make
        the higher one win. Covers statute over KID and annual report over
        prospectus and factsheet among the 28 pairs.
        """
        store.append([
            ranked_value(higher, Decimal("0.1111"), dt.date(2025, 2, 15)),
            ranked_value(lower, Decimal("0.2222"), dt.date(2026, 8, 31)),
        ])
        winner = store.view(ts(2026, 9, 10)).field(ISIN_A, "ter")
        assert (winner.value, winner.source_type) == (Decimal("0.1111"), higher)

    def test_same_class_falls_back_to_the_latest_as_of(self, store) -> None:
        store.append([
            ranked_value(SourceType.ANNUAL_REPORT, Decimal("0.1111"), dt.date(2026, 8, 31)),
            ranked_value(SourceType.ANNUAL_REPORT, Decimal("0.2222"), dt.date(2025, 12, 31)),
        ])
        assert store.view(ts(2026, 9, 10)).field(ISIN_A, "ter").value == Decimal("0.1111")

    def test_verification_status_does_not_rank(self, store) -> None:
        """An UNVERIFIED KID still beats a VERIFIED factsheet: the check stays open."""
        store.append([
            make_value(value=Decimal("0.1111"), status=VerificationStatus.UNVERIFIED),
            factsheet_value(value=Decimal("0.2222")),
        ])
        ter = store.view(ts(2026, 9, 10)).field(ISIN_A, "ter")
        assert (ter.value, ter.status) == (Decimal("0.1111"), VerificationStatus.UNVERIFIED)


class TestKidPrecedence:
    def test_older_kid_beats_newer_factsheet(self, store) -> None:
        """The KID value applies, whatever the as-of dates of other documents."""
        store.append([
            make_value(value=Decimal("0.1111"), as_of=dt.date(2026, 2, 15),
                       retrieved_at=ts(2026, 3, 1)),
            factsheet_value(value=Decimal("0.2222")),
        ])
        ter = store.view(ts(2026, 9, 10)).field(ISIN_A, "ter")
        assert (ter.value, ter.source_type) == (Decimal("0.1111"), SourceType.KID)

    def test_disagreement_stays_in_the_history(self, store) -> None:
        """Nothing is resolved silently: the losing factsheet value is still there."""
        store.append([make_value(value=Decimal("0.1111")), factsheet_value(value=Decimal("0.2222"))])
        assert list(store.history(ISIN_A, "ter")["value"]) == ["0.1111", "0.2222"]
        assert list(store.history(ISIN_A, "ter")["source_type"]) == ["kid", "factsheet"]

    @pytest.mark.parametrize(
        "other",
        [SourceType.FACTSHEET, SourceType.PROSPECTUS, SourceType.ISSUER, SourceType.EXCHANGE,
         SourceType.ANNUAL_REPORT, SourceType.SECONDARY],
    )
    def test_kid_beats_every_other_document(self, store, other) -> None:
        """Every document but the statute (A5.1, v1.6; ``TestDocumentClassPrecedence``)."""
        store.append([
            make_value(value=Decimal("0.1111"), as_of=dt.date(2025, 2, 15),
                       retrieved_at=ts(2025, 3, 1)),
            ranked_value(other, Decimal("0.2222"), dt.date(2026, 8, 31)),
        ])
        assert store.view(ts(2026, 9, 10)).field(ISIN_A, "ter").value == Decimal("0.1111")

    def test_among_kids_the_latest_as_of_applies(self, store) -> None:
        """The as-of rule decides among KID values; a newer factsheet does not interfere."""
        store.append([
            make_value(value=Decimal("0.1111"), as_of=dt.date(2026, 2, 15),
                       retrieved_at=ts(2026, 3, 1)),
            # Last year's KID, recorded afterwards.
            make_value(value=Decimal("0.3333"), as_of=dt.date(2025, 2, 10),
                       retrieved_at=ts(2026, 9, 1)),
            factsheet_value(value=Decimal("0.2222")),
        ])
        assert store.view(ts(2026, 9, 10)).field(ISIN_A, "ter").value == Decimal("0.1111")

    def test_without_a_kid_the_latest_as_of_applies(self, store) -> None:
        store.append([
            factsheet_value(value=Decimal("0.2222"), as_of=dt.date(2026, 8, 31),
                            retrieved_at=ts(2026, 9, 3)),
            factsheet_value(value=Decimal("0.4444"), as_of=dt.date(2026, 5, 31),
                            retrieved_at=ts(2026, 9, 5)),
        ])
        assert store.view(ts(2026, 9, 10)).field(ISIN_A, "ter").value == Decimal("0.2222")

    def test_kid_retrieved_after_the_cutoff_does_not_win(self, store) -> None:
        """Precedence ranks only what is known at the cut-off date.

        The KID's as-of date lies before the cut-off date, its retrieval after
        it. Ranking it first anyway would hand a backtest a value the app did
        not have yet — look-ahead that no plausibility check would notice.
        """
        store.append([
            factsheet_value(value=Decimal("0.2222"), as_of=dt.date(2026, 8, 31),
                            retrieved_at=ts(2026, 9, 3)),
            make_value(value=Decimal("0.1111"), as_of=dt.date(2026, 2, 15),
                       retrieved_at=ts(2026, 10, 1)),
        ])
        just_before = ts(2026, 10, 1) - dt.timedelta(seconds=1)
        assert store.view(ts(2026, 9, 25)).field(ISIN_A, "ter").value == Decimal("0.2222")
        assert store.view(just_before).field(ISIN_A, "ter").value == Decimal("0.2222")
        assert store.view(ts(2026, 10, 1)).field(ISIN_A, "ter").value == Decimal("0.1111")

    def test_annual_values_resolve_per_period(self, store) -> None:
        """A KID value for 2024 does not suppress the factsheet's value for 2025."""
        store.append([
            make_value("tracking_difference", Decimal("-0.0100"), period="2024",
                       as_of=dt.date(2025, 2, 15), retrieved_at=ts(2025, 3, 1)),
            factsheet_value("tracking_difference", Decimal("-0.0200"), period="2024"),
            factsheet_value("tracking_difference", Decimal("0.0300"), period="2025"),
        ])
        series = store.view(ts(2026, 9, 10)).series(ISIN_A, "tracking_difference")
        assert {year: (v.value, v.source_type) for year, v in series.items()} == {
            "2024": (Decimal("-0.0100"), SourceType.KID),
            "2025": (Decimal("0.0300"), SourceType.FACTSHEET),
        }


# ---------------------------------------------------------------------------
# Fund size in its published currency (A5.1, v1.4)
# ---------------------------------------------------------------------------


class TestFundSizeCurrency:
    def test_usd_is_stored_as_published(self, store) -> None:
        store.append([factsheet_value("fund_size", Decimal("540000000"), unit="USD")])
        size = store.view(ts(2026, 9, 10)).field(ISIN_A, "fund_size")
        assert (size.value, size.unit) == (Decimal("540000000"), "USD")

    def test_same_number_in_two_currencies_are_two_rows(self, store) -> None:
        assert store.append([
            make_value("fund_size", Decimal("540000000"), unit="EUR"),
            make_value("fund_size", Decimal("540000000"), unit="USD"),
        ]) == 2

    @pytest.mark.parametrize("unit", ["", "GBP", "usd", "€"])
    def test_unknown_or_empty_currency_is_rejected(self, unit) -> None:
        with pytest.raises(FieldValueValidationError, match="must name its unit"):
            make_value("fund_size", Decimal("540000000"), unit=unit)

    def test_missing_currency_is_not_defaulted(self) -> None:
        """``FieldValue`` itself assumes no currency (the test helper does)."""
        with pytest.raises(FieldValueValidationError, match="must name its unit"):
            FieldValue(
                isin=ISIN_A, field="fund_size", value=Decimal("540000000"),
                source_url=URL_FACTSHEET, source_type=SourceType.FACTSHEET,
                status=VerificationStatus.VERIFIED, as_of=dt.date(2026, 8, 31),
                retrieved_at=ts(2026, 9, 3),
            )


# ---------------------------------------------------------------------------
# ECB reference rates (A5.1, v1.4; carry-forward v1.5)
# ---------------------------------------------------------------------------

FRIDAY = dt.date(2026, 8, 28)
SUNDAY = dt.date(2026, 8, 30)
MONDAY = dt.date(2026, 8, 31)


class TestFxRate:
    def test_rate_comes_back_exactly(self, store) -> None:
        store.append([make_rate(Decimal("1.08430"))])
        rate = store.view(ts(2026, 9, 1)).rate_for("USD", FRIDAY)
        assert isinstance(rate.rate, Decimal)
        assert str(rate.rate) == "1.08430"
        assert (rate.as_of, rate.source_url, rate.status) == (
            FRIDAY, URL_ECB, VerificationStatus.VERIFIED
        )

    def test_float_rate_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="float is forbidden"):
            make_rate(1.0843)

    @pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1.0843")])
    def test_rate_must_be_positive(self, rate) -> None:
        with pytest.raises(FieldValueValidationError, match="not positive"):
            make_rate(rate)

    @pytest.mark.parametrize("currency", ["EUR", "GBP", "usd", ""])
    def test_only_foreign_fund_size_currencies(self, currency) -> None:
        with pytest.raises(FieldValueValidationError, match="expected one of USD"):
            make_rate(currency=currency)

    def test_retrieval_before_the_reference_date_is_rejected(self) -> None:
        with pytest.raises(FieldValueValidationError, match="before the as-of date"):
            make_rate(as_of=FRIDAY, retrieved_at=ts(2026, 8, 27))

    def test_source_is_mandatory(self) -> None:
        with pytest.raises(FieldValueValidationError, match="source_url"):
            FxRate(currency="USD", rate=Decimal("1.0843"), source_url="ecb",
                   status=VerificationStatus.VERIFIED, as_of=FRIDAY, retrieved_at=ts(2026, 8, 28))

    def test_weekend_carries_fridays_rate_forward(self, store) -> None:
        """Saturday and Sunday get Friday's rate — never Monday's, although it is known."""
        assert (FRIDAY.weekday(), SUNDAY.weekday()) == (4, 6)
        store.append([make_rate(Decimal("1.0843"), FRIDAY), make_rate(Decimal("1.2000"), MONDAY)])
        view = store.view(ts(2026, 9, 25))
        for day in (FRIDAY, FRIDAY + dt.timedelta(days=1), SUNDAY):
            assert view.rate_for("USD", day).as_of == FRIDAY
        assert view.rate_for("USD", MONDAY).rate == Decimal("1.2000")

    def test_before_the_earliest_rate_raises(self, store) -> None:
        """Nothing is extrapolated backwards."""
        store.append([make_rate(as_of=FRIDAY)])
        with pytest.raises(LookupError, match="nothing to carry forward"):
            store.view(ts(2026, 9, 25)).rate_for("USD", FRIDAY - dt.timedelta(days=1))

    def test_empty_store_raises(self, store) -> None:
        with pytest.raises(LookupError, match="no USD reference rate on or before 2026-08-28"):
            store.view(ts(2026, 9, 25)).rate_for("USD", FRIDAY)

    def test_rate_counts_from_its_retrieval(self, store) -> None:
        """Like every other value (A5.1): not from its reference date."""
        store.append([make_rate(as_of=FRIDAY, retrieved_at=ts(2026, 9, 10))])
        with pytest.raises(LookupError):
            store.view(ts(2026, 9, 10) - dt.timedelta(seconds=1)).rate_for("USD", FRIDAY)
        assert store.view(ts(2026, 9, 10)).rate_for("USD", FRIDAY).rate == Decimal("1.0843")

    def test_correction_applies_only_from_its_retrieval(self, store) -> None:
        store.append([make_rate(Decimal("1.0843"), retrieved_at=ts(2026, 8, 28, 16))])
        store.append([make_rate(Decimal("1.0844"), retrieved_at=ts(2026, 9, 1))])
        assert store.view(ts(2026, 8, 30)).rate_for("USD", FRIDAY).rate == Decimal("1.0843")
        assert store.view(ts(2026, 9, 2)).rate_for("USD", FRIDAY).rate == Decimal("1.0844")
        # Nothing overwritten.
        rows = store._conn.execute("SELECT rate FROM fx_rates ORDER BY row_id").fetchall()
        assert rows == [("1.0843",), ("1.0844",)]

    def test_reloading_rates_is_idempotent(self, store) -> None:
        rates = [make_rate(), make_value()]
        assert store.append(rates) == 2
        assert store.append(rates) == 0

    def test_rates_survive_closing(self, tmp_path) -> None:
        path = tmp_path / "instruments.duckdb"
        with InstrumentStore(path) as s:
            s.append([make_rate(Decimal("1.0843"))])
        with InstrumentStore(path) as s:
            assert s.view(ts(2026, 9, 1)).rate_for("USD", SUNDAY).rate == Decimal("1.0843")

    def test_table_checks_rates_itself(self, store) -> None:
        """K2 against raw SQL too: no retrieval before the reference date."""
        import duckdb

        with pytest.raises(duckdb.ConstraintException):
            store._conn.execute(
                """
                INSERT INTO fx_rates (currency, rate, source_url, status, as_of,
                    retrieved_at, ingested_at)
                VALUES ('USD', '1.0843', 'https://ecb.invalid/a.csv', 'VERIFIED',
                        DATE '2026-08-28', TIMESTAMPTZ '2026-08-27 12:00:00+00', now())
                """
            )


class TestFxRateGap:
    """Carry forward over TARGET closing days only; a business day without a rate is a gap (v1.6)."""

    @pytest.mark.parametrize(
        ("rate_day", "wanted"),
        [
            (FRIDAY, FRIDAY + dt.timedelta(days=1)),  # Saturday
            (FRIDAY, SUNDAY),  # over Saturday, also closed
            (dt.date(2021, 12, 24), dt.date(2021, 12, 26)),  # Friday → Sunday
            (dt.date(2025, 12, 24), dt.date(2025, 12, 26)),  # Wednesday → 25 and 26 on weekdays
            (dt.date(2026, 4, 2), dt.date(2026, 4, 6)),  # Thursday → Good Friday … Easter Monday
            (dt.date(2026, 4, 30), dt.date(2026, 5, 1)),  # Labour Day, a Friday
            (dt.date(2025, 12, 31), dt.date(2026, 1, 1)),  # New Year's Day
        ],
    )
    def test_closing_days_carry_forward(self, store, rate_day, wanted) -> None:
        store.append([make_rate(as_of=rate_day)])
        assert store.view(ts(2026, 9, 25)).rate_for("USD", wanted).as_of == rate_day

    @pytest.mark.parametrize(
        ("rate_day", "wanted", "missing"),
        [
            (dt.date(2026, 8, 27), FRIDAY + dt.timedelta(days=1), 1),  # Friday has no rate
            (dt.date(2026, 4, 2), dt.date(2026, 4, 7), 1),  # the Tuesday after Easter is open
            (MONDAY, dt.date(2026, 9, 15), 11),  # 1–4, 7–11, 14–15 September
        ],
    )
    def test_business_day_without_rate_is_a_gap(self, store, rate_day, wanted, missing) -> None:
        store.append([make_rate(as_of=rate_day)])
        with pytest.raises(FxRateGapError) as raised:
            store.view(ts(2026, 9, 25)).rate_for("USD", wanted)
        message = str(raised.value)
        for part in (f"for {wanted}", f"is of {rate_day}",
                     f"gap of {missing} TARGET business day", f"before {wanted}"):
            assert part in message

    def test_gap_is_a_lookup_error(self) -> None:
        """Existing ``except LookupError`` callers keep treating it as "no rate"."""
        assert issubclass(FxRateGapError, LookupError)

    def test_before_the_earliest_rate_is_no_gap(self, store) -> None:
        """Nothing to carry forward is still the plain LookupError, unchanged."""
        store.append([make_rate(as_of=FRIDAY)])
        with pytest.raises(LookupError, match="nothing to carry forward") as raised:
            store.view(ts(2026, 9, 25)).rate_for("USD", FRIDAY - dt.timedelta(days=1))
        assert type(raised.value) is LookupError

    def test_rate_on_the_day_is_returned_whatever_came_before(self, store) -> None:
        """A hole before the rate's own date is not this date's problem."""
        store.append([make_rate(Decimal("1.0500"), dt.date(2026, 8, 3)),
                      make_rate(Decimal("1.0843"), MONDAY)])
        assert store.view(ts(2026, 9, 25)).rate_for("USD", MONDAY).rate == Decimal("1.0843")

    def test_gap_check_applies_to_the_newest_rate_known_at_the_cutoff(self, store) -> None:
        """Friday's rate retrieved after the cut-off is invisible — Thursday's is then checked."""
        store.append([
            make_rate(Decimal("1.0800"), dt.date(2026, 8, 27)),
            make_rate(Decimal("1.0843"), FRIDAY, retrieved_at=ts(2026, 9, 10)),
        ])
        saturday = FRIDAY + dt.timedelta(days=1)
        with pytest.raises(FxRateGapError, match="is of 2026-08-27"):
            store.view(ts(2026, 9, 10) - dt.timedelta(seconds=1)).rate_for("USD", saturday)
        assert store.view(ts(2026, 9, 10)).rate_for("USD", saturday).as_of == FRIDAY


# ---------------------------------------------------------------------------
# Append-only
# ---------------------------------------------------------------------------


class TestAppendOnly:
    def test_no_update_and_no_delete(self, store) -> None:
        for forbidden in ("update", "delete", "upsert", "remove", "truncate"):
            assert not hasattr(store, forbidden), f"{forbidden}() must not exist"

    def test_correction_does_not_delete_the_original(self, store) -> None:
        store.append([make_value(value=Decimal("0.1234"), retrieved_at=ts(2026, 3, 1))])
        store.append([make_value(value=Decimal("0.4321"), retrieved_at=ts(2026, 6, 1))])

        assert store.total_rows() == 2
        history = store.history(ISIN_A, "ter")
        assert list(history["value"]) == ["0.1234", "0.4321"]
        assert "ingested_at" in history.columns  # the audit trail shows everything

    def test_reloading_is_idempotent(self, store) -> None:
        """The same source file loaded twice: no duplicates."""
        values = [make_value(), make_value("fund_size", Decimal("123456789"))]
        assert store.append(values) == 2
        assert store.append(values) == 0
        assert store.total_rows() == 2

    def test_raw_dicts_are_rejected(self, store) -> None:
        with pytest.raises(FieldValueValidationError, match="Expected a FieldValue"):
            store.append([{"isin": ISIN_A, "field": "ter", "value": "0.1"}])  # type: ignore[list-item]

    def test_error_in_batch_writes_nothing(self, store) -> None:
        with pytest.raises(FieldValueValidationError):
            store.append([make_value(), "broken"])  # type: ignore[list-item]
        assert store.total_rows() == 0

    def test_empty_append_is_allowed(self, store) -> None:
        assert store.append([]) == 0

    def test_table_checks_itself(self, store) -> None:
        """Whoever writes via SQL, bypassing the API, fails on the CHECKs."""
        import duckdb

        with pytest.raises(duckdb.ConstraintException):
            store._conn.execute(
                """
                INSERT INTO instrument_fields (isin, field, period, value, unit, source_url,
                    source_type, status, as_of, retrieved_at, ingested_at)
                VALUES ('XX0000000002', 'ter', '', '0.1', '% p. a.', 'https://x.invalid/a.pdf',
                        'secondary', 'VERIFIED', DATE '2026-02-15',
                        TIMESTAMPTZ '2026-03-01 00:00:00+00', now())
                """
            )

    @pytest.mark.parametrize(
        ("retrieved_at", "allowed"),
        [
            ("2026-08-30 23:59:59+00", False),
            # 31 Aug 01:00 in Berlin is 30 Aug 23:00 UTC: the comparison is in
            # UTC, independent of the machine's zone.
            ("2026-08-31 01:00:00+02", False),
            ("2026-08-31 00:00:00+00", True),
        ],
    )
    def test_table_checks_retrieval_after_as_of(self, store, retrieved_at, allowed) -> None:
        """K2 against raw SQL too: no retrieval before the as-of date."""
        import duckdb

        sql = f"""
            INSERT INTO instrument_fields (isin, field, period, value, unit, source_url,
                source_type, status, as_of, retrieved_at, ingested_at)
            VALUES ('XX0000000002', 'ter', '', '0.1', '% p. a.', 'https://x.invalid/a.pdf',
                    'kid', 'VERIFIED', DATE '2026-08-31',
                    TIMESTAMPTZ '{retrieved_at}', now())
        """
        if allowed:
            store._conn.execute(sql)
            assert store.total_rows() == 1
        else:
            with pytest.raises(duckdb.ConstraintException):
                store._conn.execute(sql)


# ---------------------------------------------------------------------------
# Persistent database
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_values_survive_closing(self, tmp_path) -> None:
        path = tmp_path / "instruments.duckdb"
        with InstrumentStore(path) as s:
            s.append([make_value("ter", Decimal("0.1234"))])
        with InstrumentStore(path) as s:
            value = s.view(ts(2026, 9, 1)).field(ISIN_A, "ter")
            assert value.value == Decimal("0.1234")
            assert value.retrieved_at.utcoffset() == dt.timedelta(0)


# ---------------------------------------------------------------------------
# Leakage tests (quality standards 3.3)
# ---------------------------------------------------------------------------


def _everything(view, isins=(ISIN_A, ISIN_B)) -> dict:
    """Every value a view returns for the test ISINs."""
    result = {}
    for isin in isins:
        for field, typ in FIELDS.items():
            result[isin, field] = view.series(isin, field) if typ.per_year else view.field(isin, field)
    return result


class TestLeakage:
    def test_truncation_test(self, store) -> None:
        """Test 1: the view at t stays the same, whatever is retrieved afterwards."""
        store.append([
            make_value("ter", Decimal("0.1234"), retrieved_at=ts(2026, 3, 1)),
            make_value("tracking_difference", Decimal("-0.0100"), period="2025",
                       as_of=dt.date(2026, 1, 31), retrieved_at=ts(2026, 2, 5)),
            make_value("fund_size", Decimal("123456789"), source_type=SourceType.FACTSHEET,
                       source_url=URL_FACTSHEET, as_of=dt.date(2026, 5, 31),
                       retrieved_at=ts(2026, 6, 3)),
        ])
        cutoff = ts(2026, 6, 30)
        before = _everything(store.view(cutoff))
        isins_before = store.view(cutoff).isins()

        # Retrieved later: correction of a visible value, new factsheet,
        # new year, new instrument.
        store.append([
            make_value("ter", Decimal("0.9999"), retrieved_at=ts(2026, 7, 1)),
            make_value("fund_size", Decimal("987654321"), source_type=SourceType.FACTSHEET,
                       source_url=URL_FACTSHEET, as_of=dt.date(2026, 8, 31),
                       retrieved_at=ts(2026, 9, 3)),
            make_value("tracking_difference", Decimal("0.0500"), period="2025",
                       as_of=dt.date(2026, 8, 31), retrieved_at=ts(2026, 9, 3)),
            make_value("tracking_difference", Decimal("0.0700"), period="2026",
                       as_of=dt.date(2026, 12, 31), retrieved_at=ts(2027, 1, 20)),
            make_value(isin=ISIN_B, retrieved_at=ts(2026, 7, 2)),
        ])

        assert _everything(store.view(cutoff)) == before
        assert store.view(cutoff).isins() == isins_before

    def test_future_perturbation_test(self, store) -> None:
        """Test 2: absurd values after t must not stir the view up to t."""
        store.append([
            make_value("ter", Decimal("0.1234"), retrieved_at=ts(2026, 3, 1)),
            make_value("fund_size", Decimal("123456789"), retrieved_at=ts(2026, 3, 1)),
        ])
        cutoff = ts(2026, 6, 30)
        before = _everything(store.view(cutoff))

        for day in range(1, 20):
            store.append([
                make_value("ter", Decimal(1000 + day), retrieved_at=ts(2026, 7, day)),
                make_value("fund_size", Decimal(-day), retrieved_at=ts(2026, 7, day)),
            ])

        assert _everything(store.view(cutoff)) == before

    def test_no_access_to_the_raw_table(self, store) -> None:
        view = store.view(ts(2026, 9, 1))
        public = {n for n in dir(view) if not n.startswith("_")}
        assert public == {"cut_off", "field", "series", "isins", "rate_for"}

    @settings(max_examples=60, deadline=None)
    @given(
        rows=st.lists(
            st.tuples(
                st.sampled_from([ISIN_A, ISIN_B]),
                st.sampled_from(["ter", "fund_size", "tracking_difference"]),
                st.integers(min_value=0, max_value=500),  # as-of: days after 2024-01-01
                st.integers(min_value=0, max_value=90),  # retrieval: days after the as-of date
                st.integers(min_value=-9999, max_value=9999),  # value in ten-thousandths
                # KID precedence ranks too: it must rank only what is known.
                st.sampled_from([SourceType.KID, SourceType.FACTSHEET]),
            ),
            min_size=1,
            max_size=25,
        ),
        cutoff_day=st.integers(min_value=0, max_value=620),
    )
    def test_truncation_changes_nothing(self, rows, cutoff_day) -> None:
        """Truncation test as a property: view of everything == view of what was known.

        Store A has every row, store B only those retrieved up to the cut-off
        date. Hypothesis searches for the data in which the two views differ
        — then the future would have changed the past.
        """
        base = dt.date(2024, 1, 1)
        cutoff = ts(2024, 1, 1) + dt.timedelta(days=cutoff_day)
        values = []
        for isin, field, as_of_day, delay, ten_thousandths, source_type in rows:
            as_of = base + dt.timedelta(days=as_of_day)
            values.append(
                make_value(
                    field,
                    Decimal(ten_thousandths).scaleb(-4),
                    isin=isin,
                    source_type=source_type,
                    as_of=as_of,
                    retrieved_at=ts(as_of.year, as_of.month, as_of.day)
                    + dt.timedelta(days=delay),
                    period=str(as_of.year - 1) if field == "tracking_difference" else "",
                )
            )

        with InstrumentStore(":memory:") as full, InstrumentStore(":memory:") as known:
            full.append(values)
            known.append([v for v in values if v.retrieved_at <= cutoff])

            view = full.view(cutoff)
            assert _everything(view) == _everything(known.view(cutoff))
            assert view.isins() == known.view(cutoff).isins()
            for value in _everything(view).values():
                for single in value.values() if isinstance(value, dict) else [value]:
                    if single is not None:
                        assert single.retrieved_at <= cutoff

    @settings(max_examples=60, deadline=None)
    @given(
        rates=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=60),  # reference date: days after 2026-01-01
                st.integers(min_value=0, max_value=30),  # retrieval: days after it
                st.integers(min_value=1, max_value=20000),  # rate in ten-thousandths
            ),
            max_size=15,
        ),
        query_day=st.integers(min_value=0, max_value=90),
        cutoff_day=st.integers(min_value=0, max_value=90),
    )
    def test_rate_truncation_changes_nothing(self, rates, query_day, cutoff_day) -> None:
        """The same property for the rates, with carry-forward in play.

        Neither a rate retrieved after the cut-off date nor one dated after
        the queried date may reach the result.
        """
        base = dt.date(2026, 1, 1)
        cutoff = ts(2026, 1, 1) + dt.timedelta(days=cutoff_day)
        query = base + dt.timedelta(days=query_day)
        values = [
            make_rate(Decimal(ten_thousandths).scaleb(-4), base + dt.timedelta(days=day),
                      retrieved_at=ts(2026, 1, 1, 16) + dt.timedelta(days=day + delay))
            for day, delay, ten_thousandths in rates
        ]

        def lookup(store: InstrumentStore) -> FxRate | None:
            try:
                return store.view(cutoff).rate_for("USD", query)
            except LookupError:
                return None

        with InstrumentStore(":memory:") as full, InstrumentStore(":memory:") as known:
            full.append(values)
            known.append([v for v in values if v.retrieved_at <= cutoff])
            result = lookup(full)
            assert result == lookup(known)
            if result is not None:
                assert result.retrieved_at <= cutoff
                assert result.as_of <= query


# ---------------------------------------------------------------------------
# Source file
# ---------------------------------------------------------------------------


def _write(tmp_path, documents) -> str:
    path = tmp_path / "instruments.json"
    path.write_text(json.dumps({"documents": documents}), encoding="utf-8")
    return path


KID_DOCUMENT = {
    "isin": ISIN_A,
    "source_type": "kid",
    "source_url": URL_KID,
    "as_of": "2026-02-15",
    "retrieved_at": "2026-03-01T10:00:00+01:00",
    "status": "VERIFIED",
    "values": {"ter": 0.1234, "ucits": True, "domicile": "XX"},
}

FACTSHEET_DOCUMENT = {
    "isin": ISIN_A,
    "source_type": "factsheet",
    "source_url": URL_FACTSHEET,
    "as_of": "2026-08-31",
    "retrieved_at": "2026-09-03T08:00:00+00:00",
    "status": "UNVERIFIED",
    "values": {
        "fund_size": {"value": 123456789.01, "unit": "USD"},
        "tracking_difference": {"2024": -0.0123, "2025": 0.0456},
    },
}


class TestSourceFile:
    def test_every_document_passes_on_its_provenance(self, tmp_path) -> None:
        values = load_source_file(_write(tmp_path, [KID_DOCUMENT, FACTSHEET_DOCUMENT]))
        by_field = {(v.field, v.period): v for v in values}

        assert len(values) == 6  # 3 from the KID, 1 fund size + 2 annual values from the factsheet
        assert by_field["ter", ""].source_url == URL_KID
        assert by_field["ter", ""].as_of == dt.date(2026, 2, 15)
        assert by_field["ter", ""].retrieved_at == ts(2026, 3, 1, 9)
        assert by_field["fund_size", ""].source_type is SourceType.FACTSHEET
        assert by_field["fund_size", ""].status is VerificationStatus.UNVERIFIED
        assert by_field["tracking_difference", "2024"].as_of == dt.date(2026, 8, 31)

    def test_numbers_never_become_float(self, tmp_path) -> None:
        """JSON only knows float — the loader reads Decimal nonetheless."""
        values = load_source_file(_write(tmp_path, [KID_DOCUMENT, FACTSHEET_DOCUMENT]))
        by_field = {(v.field, v.period): v.value for v in values}
        assert by_field["ter", ""] == Decimal("0.1234")
        assert by_field["fund_size", ""] == Decimal("123456789.01")
        assert by_field["tracking_difference", "2024"] == Decimal("-0.0123")

    def test_file_ends_up_in_the_store(self, tmp_path, store) -> None:
        store.append(load_source_file(_write(tmp_path, [KID_DOCUMENT, FACTSHEET_DOCUMENT])))
        view = store.view(ts(2026, 9, 10))
        assert view.field(ISIN_A, "ucits").value is True
        assert list(view.series(ISIN_A, "tracking_difference")) == ["2024", "2025"]

    def test_naive_retrieval_names_the_document(self, tmp_path) -> None:
        broken = {**FACTSHEET_DOCUMENT, "retrieved_at": "2026-09-03T08:00:00"}
        with pytest.raises(FieldValueValidationError, match="Document 2.*timezone-naive"):
            load_source_file(_write(tmp_path, [KID_DOCUMENT, broken]))

    def test_mistyped_key_is_reported(self, tmp_path) -> None:
        broken = {k: v for k, v in KID_DOCUMENT.items() if k != "source_url"}
        broken["source_ulr"] = URL_KID
        with pytest.raises(FieldValueValidationError, match="source_ulr"):
            load_source_file(_write(tmp_path, [broken]))

    def test_unknown_field_is_reported(self, tmp_path) -> None:
        broken = {**KID_DOCUMENT, "values": {"terr": 0.1}}
        with pytest.raises(FieldValueValidationError, match="Document 1.*terr"):
            load_source_file(_write(tmp_path, [broken]))

    def test_fund_size_names_its_currency(self, tmp_path) -> None:
        values = load_source_file(_write(tmp_path, [FACTSHEET_DOCUMENT]))
        size = next(v for v in values if v.field == "fund_size")
        assert (size.value, size.unit) == (Decimal("123456789.01"), "USD")

    def test_fund_size_without_currency_is_reported(self, tmp_path) -> None:
        broken = {**FACTSHEET_DOCUMENT, "values": {"fund_size": 123456789.01}}
        with pytest.raises(FieldValueValidationError, match="Document 1.*must name its unit"):
            load_source_file(_write(tmp_path, [broken]))

    def test_unit_object_needs_value_and_unit(self, tmp_path) -> None:
        broken = {**FACTSHEET_DOCUMENT,
                  "values": {"fund_size": {"value": 123456789.01, "currency": "USD"}}}
        with pytest.raises(FieldValueValidationError, match="Document 1: expected a value or"):
            load_source_file(_write(tmp_path, [broken]))

    def test_annual_value_without_year_is_reported(self, tmp_path) -> None:
        broken = {**FACTSHEET_DOCUMENT, "values": {"tracking_difference": 0.01}}
        with pytest.raises(FieldValueValidationError, match="annual value"):
            load_source_file(_write(tmp_path, [broken]))

    def test_wrong_top_level_shape_is_reported(self, tmp_path) -> None:
        path = tmp_path / "wrong.json"
        path.write_text(json.dumps([KID_DOCUMENT]), encoding="utf-8")
        with pytest.raises(FieldValueValidationError, match="documents"):
            load_source_file(path)
