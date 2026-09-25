"""Tests of the bitemporal data layer.

The most important block is ``TestLeakage``: the truncation and perturbation
tests from section 3.3 of the quality standards. They check the one property
the whole layer hinges on — that a view with cut-off date t does not change
because data arrive later.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trading_app.bitemporal import (
    Bar,
    BarValidationError,
    BitemporalStore,
    PointInTimeView,
)

UTC = dt.timezone.utc


def ts(year: int, month: int, day: int, hour: int = 22) -> dt.datetime:
    """Tz-aware timestamp. 22:00 UTC ≈ US market close."""
    return dt.datetime(year, month, day, hour, tzinfo=UTC)


def make_bar(
    day: int,
    close: float = 100.0,
    *,
    symbol: str = "AAPL.US",
    event_time: dt.datetime | None = None,
    available_at: dt.datetime | None = None,
    adjusted_close: float | None = None,
    source: str = "test",
) -> Bar:
    """Builds a valid bar with as little ceremony as possible."""
    event = event_time or ts(2026, 1, day)
    return Bar(
        symbol=symbol,
        bar_size="1d",
        event_time=event,
        available_at=available_at or event,
        open=close - 1,
        high=close + 2,
        low=close - 2,
        close=close,
        adjusted_close=adjusted_close,
        volume=1_000_000,
        source=source,
    )


@pytest.fixture
def store():
    """Fresh in-memory store per test."""
    with BitemporalStore(":memory:") as s:
        yield s


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestBarValidation:
    def test_valid_bar_is_accepted(self) -> None:
        bar = make_bar(5, close=100.0)
        assert bar.close == 100.0
        assert bar.event_time.tzinfo is not None

    def test_naive_event_time_is_rejected(self) -> None:
        """The quietest error of the layer: naive timestamps."""
        with pytest.raises(BarValidationError, match="timezone-naive"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=dt.datetime(2026, 1, 5, 22),  # without tzinfo
                available_at=ts(2026, 1, 5),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_naive_available_at_is_rejected(self) -> None:
        with pytest.raises(BarValidationError, match="timezone-naive"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=ts(2026, 1, 5),
                available_at=dt.datetime(2026, 1, 5, 22),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_timestamps_are_normalised_to_utc(self) -> None:
        """Input in another zone is allowed; UTC is stored."""
        berlin = dt.timezone(dt.timedelta(hours=2))
        bar = Bar(
            symbol="SAP.XETRA",
            bar_size="1d",
            event_time=dt.datetime(2026, 1, 5, 17, 30, tzinfo=berlin),
            available_at=dt.datetime(2026, 1, 5, 17, 30, tzinfo=berlin),
            open=99, high=102, low=98, close=100,
            volume=1_000, source="test",
        )
        assert bar.event_time.utcoffset() == dt.timedelta(0)
        assert bar.event_time.hour == 15  # 17:30 CEST = 15:30 UTC

    def test_available_at_before_event_time_is_rejected(self) -> None:
        """Convention K2: a bar is not known before it has ended."""
        with pytest.raises(BarValidationError, match="K2"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=ts(2026, 1, 5),
                available_at=ts(2026, 1, 4),  # one day too early
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_available_at_equal_to_event_time_is_allowed(self) -> None:
        bar = make_bar(5)
        assert bar.available_at == bar.event_time

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("high", 97.0, "high"),        # high < low
            ("open", 200.0, "open"),       # open outside the range
            ("close", 200.0, "close"),     # close outside the range
            ("volume", -5.0, "negative"),
            ("close", -100.0, "positive"),
        ],
    )
    def test_implausible_values_are_rejected(self, field, value, message) -> None:
        fields = dict(
            symbol="AAPL.US", bar_size="1d",
            event_time=ts(2026, 1, 5), available_at=ts(2026, 1, 5),
            open=99.0, high=102.0, low=98.0, close=100.0,
            volume=1_000.0, source="test",
        )
        fields[field] = value
        with pytest.raises(BarValidationError, match=message):
            Bar(**fields)

    def test_nan_price_is_rejected(self) -> None:
        with pytest.raises(BarValidationError, match="NaN"):
            Bar(
                symbol="AAPL.US", bar_size="1d",
                event_time=ts(2026, 1, 5), available_at=ts(2026, 1, 5),
                open=99, high=102, low=98, close=float("nan"),
                volume=1_000, source="test",
            )

    def test_missing_source_is_rejected(self) -> None:
        """Without provenance, contradicting data cannot be resolved: whom to believe?"""
        with pytest.raises(BarValidationError, match="source"):
            Bar(
                symbol="AAPL.US", bar_size="1d",
                event_time=ts(2026, 1, 5), available_at=ts(2026, 1, 5),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="",
            )

    def test_bar_is_immutable(self) -> None:
        bar = make_bar(5)
        with pytest.raises(AttributeError):
            bar.close = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Point-in-time barrier
# ---------------------------------------------------------------------------


class TestPointInTime:
    def test_empty_view_is_not_an_error(self, store) -> None:
        """Before the IPO there were no prices. That is a result."""
        frame = store.view(ts(2026, 1, 10)).bars("AAPL.US")
        assert isinstance(frame, pd.DataFrame)
        assert frame.empty

    def test_future_stays_invisible(self, store) -> None:
        """The core: what became known after the cut-off date must not appear."""
        store.append([make_bar(day, close=100 + day) for day in (5, 6, 7, 8)])

        view = store.view(ts(2026, 1, 6, 23))
        frame = view.bars("AAPL.US")

        assert len(frame) == 2
        assert list(frame["close"]) == [105.0, 106.0]

    def test_delayed_publication(self, store) -> None:
        """event_time and available_at diverge — the reason for bitemporality."""
        store.append([
            make_bar(5, close=105, available_at=ts(2026, 1, 8)),  # 3 days' delay
        ])

        assert store.view(ts(2026, 1, 7)).bars("AAPL.US").empty
        assert len(store.view(ts(2026, 1, 9)).bars("AAPL.US")) == 1

    def test_correction_applies_only_from_its_publication(self, store) -> None:
        """A correction must not change the past retroactively."""
        store.append([make_bar(5, close=100.0, available_at=ts(2026, 1, 5))])
        store.append([make_bar(5, close=101.5, available_at=ts(2026, 1, 9))])

        before = store.view(ts(2026, 1, 7)).bars("AAPL.US")
        after = store.view(ts(2026, 1, 10)).bars("AAPL.US")

        assert len(before) == 1 and before.iloc[0]["close"] == 100.0
        assert len(after) == 1 and after.iloc[0]["close"] == 101.5

    def test_cutoff_is_inclusive(self, store) -> None:
        """available_at == as_of: the bar is known."""
        store.append([make_bar(5, available_at=ts(2026, 1, 5))])
        assert len(store.view(ts(2026, 1, 5)).bars("AAPL.US")) == 1

    def test_one_second_before_still_invisible(self, store) -> None:
        store.append([make_bar(5, available_at=ts(2026, 1, 5))])
        just_before = ts(2026, 1, 5) - dt.timedelta(seconds=1)
        assert store.view(just_before).bars("AAPL.US").empty

    def test_time_window(self, store) -> None:
        store.append([make_bar(day, close=100 + day) for day in range(5, 15)])
        frame = store.view(ts(2026, 2, 1)).bars(
            "AAPL.US", start=ts(2026, 1, 7), end=ts(2026, 1, 9)
        )
        assert list(frame["close"]) == [107.0, 108.0, 109.0]

    def test_symbols_stay_separate(self, store) -> None:
        store.append([
            make_bar(5, symbol="AAPL.US", close=100),
            make_bar(5, symbol="MSFT.US", close=400),
        ])
        view = store.view(ts(2026, 1, 10))
        assert view.bars("AAPL.US").iloc[0]["close"] == 100.0
        assert view.bars("MSFT.US").iloc[0]["close"] == 400.0
        assert view.symbols() == ["AAPL.US", "MSFT.US"]

    def test_bar_size_stays_separate(self, store) -> None:
        """Daily and hourly bars must never mix."""
        event = ts(2026, 1, 5)
        shared = dict(
            symbol="AAPL.US", event_time=event, available_at=event,
            open=99, high=102, low=98, volume=1_000, source="test",
        )
        store.append([
            Bar(bar_size="1d", close=100, **shared),
            Bar(bar_size="1h", close=101, **shared),
        ])
        view = store.view(ts(2026, 1, 10))
        assert view.bars("AAPL.US", "1d").iloc[0]["close"] == 100.0
        assert view.bars("AAPL.US", "1h").iloc[0]["close"] == 101.0

    def test_view_returns_no_ingested_at(self, store) -> None:
        """ingested_at is the most direct route to knowledge of the future."""
        store.append([make_bar(5)])
        frame = store.view(ts(2026, 1, 10)).bars("AAPL.US")
        assert "ingested_at" not in frame.columns
        assert "row_id" not in frame.columns

    def test_view_needs_tz_aware_cutoff(self, store) -> None:
        with pytest.raises(BarValidationError, match="timezone-naive"):
            store.view(dt.datetime(2026, 1, 10))

    def test_last_bar(self, store) -> None:
        store.append([make_bar(day, close=100 + day) for day in (5, 6, 7)])
        assert store.view(ts(2026, 1, 6, 23)).last_bar("AAPL.US")["close"] == 106.0
        assert store.view(ts(2026, 1, 1)).last_bar("AAPL.US") is None


# ---------------------------------------------------------------------------
# Append-only
# ---------------------------------------------------------------------------


class TestAppendOnly:
    def test_no_update_and_no_delete(self, store) -> None:
        """Whoever can overwrite bars can rewrite the past."""
        for forbidden in ("update", "delete", "upsert", "remove", "truncate"):
            assert not hasattr(store, forbidden), f"{forbidden}() must not exist"

    def test_correction_does_not_delete_the_original(self, store) -> None:
        store.append([make_bar(5, close=100.0, available_at=ts(2026, 1, 5))])
        store.append([make_bar(5, close=101.5, available_at=ts(2026, 1, 9))])

        assert store.total_rows() == 2
        history = store.history("AAPL.US", ts(2026, 1, 5))
        assert list(history["close"]) == [100.0, 101.5]

    def test_raw_tuples_are_rejected(self, store) -> None:
        """Otherwise input validation could be bypassed."""
        with pytest.raises(BarValidationError, match="Expected a Bar"):
            store.append([("AAPL.US", "1d", 100.0)])  # type: ignore[list-item]

    def test_empty_append_is_allowed(self, store) -> None:
        assert store.append([]) == 0

    def test_append_reports_row_count(self, store) -> None:
        assert store.append([make_bar(5), make_bar(6)]) == 2


# ---------------------------------------------------------------------------
# Time zones
# ---------------------------------------------------------------------------


class TestTimezones:
    def test_instant_survives_the_database_round_trip(self, store) -> None:
        """The same instant in as out — even if the display deceives.

        DuckDB returns timestamps in the local zone. A bar that goes in as
        14 Aug 22:00 UTC comes back out in Berlin as 15 Aug 00:00+02:00. That
        is the same instant but looks like a day's offset — and tempts one to
        build in a real error "as a correction". The test pins down what
        matters: the instant counts, not how it is written.
        """
        going_in = ts(2026, 8, 14, hour=22)
        store.append([make_bar(14, event_time=going_in, available_at=going_in)])

        coming_out = store.view(ts(2026, 9, 1)).bars("AAPL.US").iloc[0]["event_time"]
        assert coming_out.tz_convert("UTC").to_pydatetime() == going_in

    def test_cutoff_in_another_zone_returns_the_same(self, store) -> None:
        """A cut-off date is an instant, not a time on a clock face."""
        store.append([make_bar(day, available_at=ts(2026, 1, day)) for day in (5, 6, 7)])

        in_utc = ts(2026, 1, 6, hour=12)
        in_tokyo = in_utc.astimezone(dt.timezone(dt.timedelta(hours=9)))
        assert in_utc == in_tokyo  # the same instant, written differently

        assert len(store.view(in_utc).bars("AAPL.US")) == len(
            store.view(in_tokyo).bars("AAPL.US")
        )


# ---------------------------------------------------------------------------
# Leakage tests (quality standards 3.3)
# ---------------------------------------------------------------------------


class TestLeakage:
    def test_truncation_test(self, store) -> None:
        """Test 1: the view at t must be identical whether later data arrive or not.

        The central property. If it fails, every metric in the project is
        worthless without anything crashing.
        """
        store.append([make_bar(day, close=100 + day) for day in range(5, 11)])
        cutoff = ts(2026, 1, 7, 23)
        before = store.view(cutoff).bars("AAPL.US")

        # Add the future, including a correction of a bar that is already visible.
        store.append([make_bar(day, close=200 + day) for day in range(11, 20)])
        store.append([make_bar(6, close=999.0, available_at=ts(2026, 1, 15))])

        after = store.view(cutoff).bars("AAPL.US")
        pd.testing.assert_frame_equal(before, after)

    def test_future_perturbation_test(self, store) -> None:
        """Test 2: change data after t — the view up to t must not stir."""
        store.append([make_bar(day, close=100 + day) for day in range(5, 11)])
        cutoff = ts(2026, 1, 7, 23)
        before = store.view(cutoff).bars("AAPL.US")

        for day in range(8, 11):
            store.append([make_bar(day, close=500.0 + day, available_at=ts(2026, 1, 20))])

        pd.testing.assert_frame_equal(before, store.view(cutoff).bars("AAPL.US"))

    def test_no_access_to_the_raw_table(self, store) -> None:
        """Strategy code sees only the view — no public way back."""
        view = store.view(ts(2026, 1, 10))
        public = [n for n in dir(view) if not n.startswith("_")]
        assert set(public) == {"as_of", "bars", "last_bar", "symbols"}

    @settings(max_examples=50, deadline=None)
    @given(
        cutoff_day=st.integers(min_value=1, max_value=28),
        count=st.integers(min_value=1, max_value=20),
    )
    def test_monotonicity(self, cutoff_day: int, count: int) -> None:
        """A later cut-off date never sees less than an earlier one.

        Hypothesis searches for the counterexample instead of hoping for
        hand-picked cases. If the ranking stumbles on equal available_at, it
        shows here.
        """
        with BitemporalStore(":memory:") as s:
            s.append([make_bar(day % 28 + 1, close=100 + day) for day in range(count)])
            early = ts(2026, 1, cutoff_day)
            late = early + dt.timedelta(days=7)
            assert len(s.view(early).bars("AAPL.US")) <= len(s.view(late).bars("AAPL.US"))


# ---------------------------------------------------------------------------
# Adjusted and unadjusted prices
# ---------------------------------------------------------------------------


class TestPriceAdjustment:
    def test_both_price_worlds_stay_separate(self, store) -> None:
        """See docs/20260925_rueckwirkende-anpassung.md."""
        store.append([make_bar(5, close=256.87, adjusted_close=255.9246)])
        row = store.view(ts(2026, 1, 10)).bars("AAPL.US").iloc[0]
        assert row["close"] == 256.87
        assert row["adjusted_close"] == pytest.approx(255.9246)

    def test_adjusted_close_may_be_missing(self, store) -> None:
        """Intraday bars from EODHD are unadjusted — the field stays empty."""
        store.append([make_bar(5, close=100.0, adjusted_close=None)])
        row = store.view(ts(2026, 1, 10)).bars("AAPL.US").iloc[0]
        assert pd.isna(row["adjusted_close"])
        assert row["close"] == 100.0


# ---------------------------------------------------------------------------
# Persistent database
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_data_survive_closing(self, tmp_path) -> None:
        path = tmp_path / "test.duckdb"
        with BitemporalStore(path) as s:
            s.append([make_bar(5, close=100.0)])
        with BitemporalStore(path) as s:
            assert s.view(ts(2026, 1, 10)).bars("AAPL.US").iloc[0]["close"] == 100.0

    def test_timezone_survives_storage(self, tmp_path) -> None:
        """TIMESTAMPTZ, not TIMESTAMP — otherwise a naive value comes back."""
        path = tmp_path / "tz.duckdb"
        with BitemporalStore(path) as s:
            s.append([make_bar(5)])
        with BitemporalStore(path) as s:
            frame = s.view(ts(2026, 1, 10)).bars("AAPL.US")
            assert frame["event_time"].dt.tz is not None
