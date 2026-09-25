"""Tests of the EODHD adapter.

No network. The responses come from real calls on 2026-09-25 — the numbers
were really measured, just frozen. A test that goes to the network uses up
the daily quota (20 calls) and turns red when the provider has a hiccup.

The most important test is ``test_silent_truncation_aborts_hard``: it pins
down the property that HTTP 200 with truncated data counts as an error.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import urllib.error
from typing import Any

import pytest

from trading_app.bitemporal import BitemporalStore
from trading_app.sources.eodhd import (
    EodhdClient,
    EodhdError,
    FreePlanLimitError,
    IntradayUnavailableError,
)

UTC = dt.timezone.utc

# Real response from /api/eod/AAPL.US, retrieved 2026-09-25.
REAL_BARS = [
    {
        "date": "2026-09-22", "open": 331.5, "high": 336.28, "low": 330.91,
        "close": 335.5, "adjusted_close": 335.5, "volume": 44163300,
    },
    {
        "date": "2026-09-23", "open": 336.0, "high": 338.19, "low": 333.62,
        "close": 334.15, "adjusted_close": 334.15, "volume": 38102500,
    },
    {
        "date": "2026-09-24", "open": 334.4, "high": 337.92, "low": 333.35,
        "close": 335.92, "adjusted_close": 335.92, "volume": 35217600,
    },
]

# The same response as it comes when the request reaches back more than twelve
# months: HTTP 200, less data, the hint only in the warning field.
TRUNCATED_BARS = [
    {**row, "warning": "Data is limited by one year as you have free subscription"}
    for row in REAL_BARS
]


class FakeResponse(io.BytesIO):
    """Minimal counterpart to what urlopen returns as a context manager."""

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.fixture
def fake_net(monkeypatch):
    """Replaces urlopen. Returns a recorder of the URLs called."""
    calls: list[str] = []

    def install(payload: Any = None, *, http_error: int | None = None, body: str = ""):
        def fake(url, timeout=None):  # noqa: ARG001
            calls.append(url)
            if http_error is not None:
                raise urllib.error.HTTPError(
                    url, http_error, body, {}, io.BytesIO(body.encode())
                )
            return FakeResponse(json.dumps(payload).encode())

        monkeypatch.setattr("urllib.request.urlopen", fake)
        return calls

    return install


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "test-token-not-real")
    return EodhdClient()


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class TestToken:
    def test_token_comes_from_the_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("EODHD_API_TOKEN", "from-the-environment")
        assert EodhdClient()._token == "from-the-environment"

    def test_without_token_clear_message(self, monkeypatch) -> None:
        monkeypatch.delenv("EODHD_API_TOKEN", raising=False)
        with pytest.raises(EodhdError, match="No API token"):
            EodhdClient()

    def test_token_never_appears_in_an_error_message(self, monkeypatch, fake_net) -> None:
        """Error messages end up in the log. The token must not show up there."""
        monkeypatch.setenv("EODHD_API_TOKEN", "secret-abc123")
        fake_net(http_error=500, body="Internal Server Error")
        with pytest.raises(EodhdError) as error:
            EodhdClient().daily_bars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))
        assert "secret-abc123" not in str(error.value)


# ---------------------------------------------------------------------------
# The silent truncation — the most important test in this file
# ---------------------------------------------------------------------------


class TestOneYearLimit:
    def test_silent_truncation_aborts_hard(self, client, fake_net) -> None:
        """HTTP 200 with truncated data must be an error, not a warning.

        A warning in the log gets overlooked for half a year. Until then every
        analysis rests on twelve months of data instead of ten years.
        """
        fake_net(TRUNCATED_BARS)
        with pytest.raises(FreePlanLimitError, match="silently truncated"):
            client.daily_bars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))

    def test_error_message_names_provider_text_and_way_out(self, client, fake_net) -> None:
        fake_net(TRUNCATED_BARS)
        with pytest.raises(FreePlanLimitError) as error:
            client.daily_bars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))
        text = str(error.value)
        assert "limited by one year" in text   # the provider's original text
        assert "twelve months" in text         # what to do

    def test_warning_on_any_bar_is_enough(self, client, fake_net) -> None:
        """EODHD attaches the field per bar — a single one must suffice."""
        mixed = [dict(REAL_BARS[0]), dict(REAL_BARS[1]), dict(TRUNCATED_BARS[2])]
        fake_net(mixed)
        with pytest.raises(FreePlanLimitError):
            client.daily_bars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))

    def test_without_warning_everything_goes_through(self, client, fake_net) -> None:
        """At exactly twelve months the field is missing — measured on 2026-09-25."""
        fake_net(REAL_BARS)
        bars = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        assert len(bars) == 3


# ---------------------------------------------------------------------------
# Intraday
# ---------------------------------------------------------------------------


class TestIntradayBlocked:
    def test_http_403_becomes_clear_exception(self, client, fake_net) -> None:
        fake_net(http_error=403, body="Only EOD data allowed for free users")
        with pytest.raises(IntradayUnavailableError) as error:
            client.daily_bars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))
        text = str(error.value)
        assert "free plan" in text
        assert "retroactively" in text  # pointer to the trap when upgrading

    def test_429_names_the_daily_limit(self, client, fake_net) -> None:
        fake_net(http_error=429, body="Too many requests")
        with pytest.raises(EodhdError, match="20 calls"):
            client.daily_bars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))


# ---------------------------------------------------------------------------
# Conversion into Bar objects
# ---------------------------------------------------------------------------


class TestConversion:
    def test_fields_land_correctly(self, client, fake_net) -> None:
        fake_net(REAL_BARS)
        bars = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        first = bars[0]
        assert first.symbol == "AAPL.US"
        assert first.bar_size == "1d"
        assert first.close == 335.5
        assert first.adjusted_close == 335.5
        assert first.volume == 44163300
        assert first.source == "eodhd"

    def test_available_at_is_after_market_close(self, client, fake_net) -> None:
        """When in doubt, too late: too early would be look-ahead."""
        fake_net(REAL_BARS)
        bar = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))[0]
        assert bar.available_at > bar.event_time
        assert bar.available_at - bar.event_time == dt.timedelta(hours=1)

    def test_buffer_is_configurable(self, monkeypatch, fake_net) -> None:
        monkeypatch.setenv("EODHD_API_TOKEN", "test")
        fake_net(REAL_BARS)
        client = EodhdClient(availability_buffer=dt.timedelta(hours=6))
        bar = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))[0]
        assert bar.available_at - bar.event_time == dt.timedelta(hours=6)

    def test_market_close_for_xetra(self, client, fake_net) -> None:
        fake_net(REAL_BARS)
        bar = client.daily_bars(
            "SAP.XETRA", dt.date(2026, 9, 22), dt.date(2026, 9, 24),
            market_close=dt.time(16, 30),
        )[0]
        assert bar.event_time.hour == 16 and bar.event_time.minute == 30

    def test_bars_come_sorted(self, client, fake_net) -> None:
        fake_net(list(reversed(REAL_BARS)))
        bars = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        assert [b.event_time for b in bars] == sorted(b.event_time for b in bars)

    def test_missing_adjusted_close_becomes_none(self, client, fake_net) -> None:
        without = [{k: v for k, v in REAL_BARS[0].items() if k != "adjusted_close"}]
        fake_net(without)
        bar = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 22))[0]
        assert bar.adjusted_close is None

    def test_start_after_end_is_rejected(self, client) -> None:
        with pytest.raises(ValueError, match="is after"):
            client.daily_bars("AAPL.US", dt.date(2026, 3, 1), dt.date(2026, 1, 1))

    def test_broken_json_is_reported(self, client, monkeypatch) -> None:
        def broken(url, timeout=None):  # noqa: ARG001
            return FakeResponse(b"<html>Maintenance</html>")
        monkeypatch.setattr("urllib.request.urlopen", broken)
        with pytest.raises(EodhdError, match="not valid JSON"):
            client.daily_bars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))


# ---------------------------------------------------------------------------
# Splits and dividends
# ---------------------------------------------------------------------------


class TestSplitsAndDividends:
    def test_splits(self, client, fake_net) -> None:
        """Real response from 2026-09-25."""
        fake_net([
            {"date": "2014-06-09", "split": "7.000000/1.000000"},
            {"date": "2020-08-31", "split": "4.000000/1.000000"},
        ])
        splits = client.splits("AAPL.US", dt.date(2010, 1, 1), dt.date(2026, 9, 25))
        assert len(splits) == 2
        assert splits[1]["split"] == "4.000000/1.000000"

    def test_dividends_carry_declarationdate(self, client, fake_net) -> None:
        """The actual value of the free token: the correct available_at."""
        fake_net([{
            "date": "2026-08-10", "declarationDate": "2026-07-31",
            "recordDate": "2026-08-11", "paymentDate": "2026-08-14",
            "value": 0.27, "unadjustedValue": 0.27, "currency": "USD",
        }])
        div = client.dividends("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 9, 25))
        assert div[0]["declarationDate"] == "2026-07-31"
        # The declaration precedes the ex-date — otherwise available_at would be wrong.
        assert div[0]["declarationDate"] < div[0]["date"]


# ---------------------------------------------------------------------------
# Interplay with the data layer
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_loaded_bars_end_up_in_the_store(self, client, fake_net) -> None:
        fake_net(REAL_BARS)
        bars = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))

        with BitemporalStore(":memory:") as store:
            assert store.append(bars) == 3
            view = store.view(dt.datetime(2026, 9, 25, tzinfo=UTC))
            frame = view.bars("AAPL.US")
            assert len(frame) == 3
            assert frame.iloc[-1]["close"] == 335.92

    def test_pit_barrier_holds_for_real_data_too(self, client, fake_net) -> None:
        """Cut-off 23 Sep 22:30 — the bar of the 23rd is available only at 23:00."""
        fake_net(REAL_BARS)
        bars = client.daily_bars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))

        with BitemporalStore(":memory:") as store:
            store.append(bars)
            view = store.view(dt.datetime(2026, 9, 23, 22, 30, tzinfo=UTC))
            frame = view.bars("AAPL.US")
            assert len(frame) == 1
            assert frame.iloc[0]["close"] == 335.5  # only the 22nd
