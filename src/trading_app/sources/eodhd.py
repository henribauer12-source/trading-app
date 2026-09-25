"""Adapter for EODHD — daily data, splits, dividends.

The free plan has two quirks, both of which silently lead to wrong results if
they are not caught:

**1. Silent truncation to twelve months.** A request from January 2015 comes
back with data from September 2025 — HTTP 200, no error message. The only
hint is in a ``warning`` field on every single bar:

    "Data is limited by one year as you have free subscription"

Whoever does not read it takes a ten-year backtest for valid that rests on
twelve months. That is why ``EodhdClient`` **aborts hard** on this field
instead of warning. A warning in the log gets overlooked; an exception does
not.

**2. No intraday.** ``/api/intraday`` answers with HTTP 403, "Only EOD data
allowed for free users". The client reports this as an exception of its own
with a pointer to the subscription path, instead of passing on a bare HTTP
error.

On the ``available_at`` field: EODHD delivers daily data after market close
but does not say exactly when. The client therefore deliberately sets
``available_at`` conservatively to market close plus a buffer (default:
1 hour). Setting it too late costs signal quality; too early creates
look-ahead. When in doubt, too late — an overly cautious backtest is
unpleasant, an overly optimistic one is worthless.

The token comes exclusively from the environment (``EODHD_API_TOKEN``), never
from the code. It lives in ``~/claude-local/trading-app/.env``, outside Git
and iCloud.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from trading_app.bitemporal import Bar

__all__ = [
    "EodhdClient",
    "EodhdError",
    "FreePlanLimitError",
    "IntradayUnavailableError",
]

UTC = dt.timezone.utc
_BASE_URL = "https://eodhd.com/api"

# The text with which EODHD announces the silent truncation.
_ONE_YEAR_LIMIT_WARNING = "limited by one year"


class EodhdError(RuntimeError):
    """Base class of all EODHD errors."""


class FreePlanLimitError(EodhdError):
    """The response was silently truncated.

    A type of its own, so that a caller can react to it specifically — for
    instance by shrinking the load window — without catching real network
    errors too.
    """


class IntradayUnavailableError(EodhdError):
    """Intraday is blocked on the free plan (HTTP 403)."""


class EodhdClient:
    """Thin adapter over the EODHD REST API.

    Example:
        >>> client = EodhdClient()                     # token from the environment
        >>> bars = client.daily_bars("AAPL.US",
        ...                          start=date(2026, 1, 1),
        ...                          end=date(2026, 3, 1))
        >>> store.append(bars)
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        availability_buffer: dt.timedelta = dt.timedelta(hours=1),
    ) -> None:
        """
        Args:
            token: API token. Default: ``EODHD_API_TOKEN`` from the environment.
            timeout: Time limit per request in seconds.
            availability_buffer: Added to market close for ``available_at``.
                Better too large than too small.

        Raises:
            EodhdError: If no token can be found.
        """
        self._token = token or os.environ.get("EODHD_API_TOKEN")
        if not self._token:
            raise EodhdError(
                "No API token. Either set EODHD_API_TOKEN or pass token=.\n"
                "Load it with: set -a && . ~/claude-local/trading-app/.env && set +a"
            )
        self._timeout = timeout
        self._buffer = availability_buffer

    # -- Network ----------------------------------------------------------

    def _fetch(self, path: str, **params: Any) -> Any:
        """Performs a request and returns the JSON response.

        Raises:
            IntradayUnavailableError: On HTTP 403 for intraday.
            EodhdError: On all other HTTP and network errors.
        """
        params = {"api_token": self._token, "fmt": "json", **params}
        url = f"{_BASE_URL}/{path}?{urllib.parse.urlencode(params)}"

        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:200]
            if error.code == 403:
                raise IntradayUnavailableError(
                    f"EODHD refuses access (HTTP 403): {body}\n"
                    "The free plan only unlocks EOD data. Intraday "
                    "requires a subscription (~15 €/month with student discount) — and "
                    "then additionally a module of its own for split adjustment, "
                    "because EODHD does not adjust intraday bars retroactively. "
                    "See docs/20260925_rueckwirkende-anpassung.md."
                ) from error
            if error.code == 429:
                raise EodhdError(
                    f"Daily limit exhausted (HTTP 429): {body}\n"
                    "The free plan allows 20 calls per day."
                ) from error
            # Never the token in the message — it ends up in the log.
            raise EodhdError(f"HTTP {error.code} for /{path}: {body}") from error
        except urllib.error.URLError as error:
            raise EodhdError(f"Network error for /{path}: {error.reason}") from error

        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise EodhdError(f"Response was not valid JSON: {raw[:200]}") from error

    @staticmethod
    def _check_one_year_limit(rows: list[dict[str, Any]], symbol: str) -> None:
        """Aborts if EODHD silently truncated the response.

        Deliberately an exception instead of a log warning: the truncation is
        exactly the kind of error that stays unnoticed for months and devalues
        every analysis built on it.
        """
        for row in rows:
            warning = row.get("warning")
            if warning and _ONE_YEAR_LIMIT_WARNING in str(warning).lower():
                raise FreePlanLimitError(
                    f"EODHD silently truncated the response for {symbol}.\n"
                    f"Provider message: {warning!r}\n"
                    "The free plan returns at most twelve months — the request came "
                    "back with HTTP 200, but with less data than requested. "
                    "Either shrink the load window to twelve months or "
                    "get the history from another source."
                )

    # -- Daily bars -------------------------------------------------------

    def daily_bars(
        self,
        symbol: str,
        start: dt.date,
        end: dt.date,
        *,
        market_close: dt.time = dt.time(22, 0),
    ) -> list[Bar]:
        """Loads daily bars and returns them as validated ``Bar`` objects.

        Args:
            symbol: EODHD ticker, e.g. ``AAPL.US`` or ``SAP.XETRA``.
            start: First trading day (inclusive).
            end: Last trading day (inclusive).
            market_close: Closing time in UTC. Default 22:00 ≈ US close.
                For Xetra set 16:30 UTC.

        Returns:
            Bars by ``event_time`` ascending, with ``adjusted_close``.

        Raises:
            FreePlanLimitError: If the response was silently truncated.
            EodhdError: On HTTP or network errors.
        """
        if start > end:
            raise ValueError(f"start ({start}) is after end ({end})")

        rows = self._fetch(
            f"eod/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        if not isinstance(rows, list):
            raise EodhdError(f"Unexpected response shape for {symbol}: {type(rows).__name__}")

        self._check_one_year_limit(rows, symbol)

        bars: list[Bar] = []
        for row in rows:
            day = dt.date.fromisoformat(row["date"])
            event = dt.datetime.combine(day, market_close, tzinfo=UTC)
            bars.append(
                Bar(
                    symbol=symbol,
                    bar_size="1d",
                    event_time=event,
                    available_at=event + self._buffer,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    adjusted_close=(
                        float(row["adjusted_close"])
                        if row.get("adjusted_close") is not None
                        else None
                    ),
                    volume=float(row.get("volume") or 0.0),
                    source="eodhd",
                )
            )
        bars.sort(key=lambda b: b.event_time)
        return bars

    # -- Splits and dividends ---------------------------------------------

    def splits(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        """Split history as a list of ``{date, split}``.

        ``split`` is given as text, e.g. ``"4.000000/1.000000"`` for the AAPL
        split of 31 August 2020.
        """
        rows = self._fetch(
            f"splits/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        return rows if isinstance(rows, list) else []

    def dividends(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        """Dividend history, including ``declarationDate``.

        The reason EODHD stays in the project despite the free plan: the
        declaration date is the correct ``available_at`` time for any dividend
        signal. ``yfinance`` does not provide it, and without the field a
        dividend strategy silently turns into clairvoyance.
        """
        rows = self._fetch(
            f"div/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        return rows if isinstance(rows, list) else []

    def account_status(self) -> dict[str, Any]:
        """Plan and remaining quota. Costs a call itself."""
        response = self._fetch("user")
        return response if isinstance(response, dict) else {}
