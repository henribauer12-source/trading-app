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
import json
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trading_app.instruments import (
    FIELDS,
    Distribution,
    FieldValue,
    FieldValueValidationError,
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
    """Builds a valid FieldValue; by default it is retrieved on the as-of date."""
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
        assert public == {"cut_off", "field", "series", "isins"}

    @settings(max_examples=60, deadline=None)
    @given(
        rows=st.lists(
            st.tuples(
                st.sampled_from([ISIN_A, ISIN_B]),
                st.sampled_from(["ter", "fund_size", "tracking_difference"]),
                st.integers(min_value=0, max_value=500),  # as-of: days after 2024-01-01
                st.integers(min_value=0, max_value=90),  # retrieval: days after the as-of date
                st.integers(min_value=-9999, max_value=9999),  # value in ten-thousandths
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
        for isin, field, as_of_day, delay, ten_thousandths in rows:
            as_of = base + dt.timedelta(days=as_of_day)
            values.append(
                make_value(
                    field,
                    Decimal(ten_thousandths).scaleb(-4),
                    isin=isin,
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
        "fund_size": 123456789.01,
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

    def test_annual_value_without_year_is_reported(self, tmp_path) -> None:
        broken = {**FACTSHEET_DOCUMENT, "values": {"tracking_difference": 0.01}}
        with pytest.raises(FieldValueValidationError, match="annual value"):
            load_source_file(_write(tmp_path, [broken]))

    def test_wrong_top_level_shape_is_reported(self, tmp_path) -> None:
        path = tmp_path / "wrong.json"
        path.write_text(json.dumps([KID_DOCUMENT]), encoding="utf-8")
        with pytest.raises(FieldValueValidationError, match="documents"):
            load_source_file(path)
