"""Bitemporal storage and point-in-time access.

The core of phase 1. Two rules govern the whole design:

1. **Append-only.** A row once written is never changed and never deleted.
   Corrections come in as a new row with a later `available_at`. That keeps
   it reconstructable what the app *believed* at any point in the past — not
   just what is true today.

2. **`PointInTimeView` is the only interface for strategy code.**
   It returns exclusively rows with `available_at <= cut_off`. Without this
   barrier, knowledge of the future sooner or later creeps into a signal, and
   the backtest becomes worthless without anything crashing.

Three timestamps per row (quality standards section 3.2):

| Field          | Meaning                                                |
|----------------|--------------------------------------------------------|
| `event_time`   | when it happened — here: end of the bar                |
| `available_at` | from when it was publicly known                        |
| `ingested_at`  | when this app stored it                                |

`event_time` and `available_at` diverge as soon as data are published late or
corrected afterwards. Exactly this gap is the reason for bitemporal storage.

Naming convention for the whole data layer:

- ``as_of`` is always a **document date** (event time): the date of the
  document a value was read from. A property of the data.
- ``cut_off`` is always a **query horizon**: the world as the app knew it at
  time T, compared with ``available_at`` (or ``retrieved_at`` in
  ``instruments``). A property of the question.

Prices are kept twice — `close` as traded, `adjusted_close` adjusted for
splits and dividends. Why that is no luxury is explained in
`docs/20260925_rueckwirkende-anpassung.md`: over twelve months of AAPL the two
columns are almost half a percentage point of return apart, always in the
same direction.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

__all__ = ["Bar", "BitemporalStore", "PointInTimeView", "BarValidationError"]


class BarValidationError(ValueError):
    """A bar failed input validation.

    Deliberately a class of its own: a loader should be able to react
    specifically to faulty market data without catching every other
    ValueError too.
    """


def _require_aware(name: str, value: dt.datetime) -> dt.datetime:
    """Reject timezone-naive timestamps and normalise everything to UTC.

    A naive timestamp is the quietest source of error in the whole layer: the
    comparison `available_at <= cut_off` then runs up to two hours wrong,
    depending on daylight saving time, but raises no message. Two hours are
    enough for look-ahead across a trading day.
    """
    if not isinstance(value, dt.datetime):
        raise BarValidationError(f"{name} must be a datetime, was {type(value).__name__}")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise BarValidationError(
            f"{name} is timezone-naive. Timezone-naive timestamps are forbidden — "
            "depending on daylight saving time they compare up to two hours wrong. "
            "Expected a tz-aware datetime, e.g. with tz=datetime.timezone.utc."
        )
    return value.astimezone(dt.timezone.utc)


@dataclass(frozen=True, slots=True)
class Bar:
    """An OHLCV bar with its two time axes.

    Immutable (`frozen=True`), because a bar that has already been validated
    should no longer be changeable on its way into the database.

    Attributes:
        symbol: Instrument ticker, e.g. ``AAPL.US``.
        bar_size: Bar length as text, e.g. ``1d``, ``1h``, ``1m``.
        event_time: End of the bar, tz-aware.
        available_at: From when the bar was publicly known, tz-aware.
        open, high, low, close: Prices **as traded**, unadjusted.
        adjusted_close: Close adjusted for splits/dividends, or None.
        volume: Traded quantity.
        source: Provenance, e.g. ``eodhd``. With contradicting sources the
            only chance to tell afterwards whom to believe.
    """

    symbol: str
    bar_size: str
    event_time: dt.datetime
    available_at: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    adjusted_close: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise BarValidationError("symbol must not be empty")
        if not self.bar_size or not self.bar_size.strip():
            raise BarValidationError("bar_size must not be empty")
        if not self.source or not self.source.strip():
            raise BarValidationError("source must not be empty — provenance is mandatory")

        event_time = _require_aware("event_time", self.event_time)
        available_at = _require_aware("available_at", self.available_at)

        # Convention K2 of the calculation-core spec: a bar is available at
        # the earliest from its end time. Were available_at < event_time, a
        # strategy could know the close before it is settled.
        if available_at < event_time:
            raise BarValidationError(
                f"available_at ({available_at.isoformat()}) is before event_time "
                f"({event_time.isoformat()}). A bar cannot be known "
                "before it has ended (convention K2)."
            )

        object.__setattr__(self, "event_time", event_time)
        object.__setattr__(self, "available_at", available_at)

        prices = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
        for name, value in prices.items():
            if value is None:
                raise BarValidationError(f"{name} is missing")
            number = float(value)
            if number != number:  # NaN
                raise BarValidationError(f"{name} is NaN")
            if number <= 0:
                raise BarValidationError(f"{name} must be positive, was {number}")
            object.__setattr__(self, name, number)

        if self.high < self.low:
            raise BarValidationError(f"high ({self.high}) is below low ({self.low})")
        if not (self.low <= self.open <= self.high):
            raise BarValidationError(
                f"open ({self.open}) is outside [low={self.low}, high={self.high}]"
            )
        if not (self.low <= self.close <= self.high):
            raise BarValidationError(
                f"close ({self.close}) is outside [low={self.low}, high={self.high}]"
            )

        volume = float(self.volume)
        if volume != volume:
            raise BarValidationError("volume is NaN")
        if volume < 0:
            raise BarValidationError(f"volume must not be negative, was {volume}")
        object.__setattr__(self, "volume", volume)

        if self.adjusted_close is not None:
            adj = float(self.adjusted_close)
            if adj != adj:
                raise BarValidationError("adjusted_close is NaN")
            if adj <= 0:
                raise BarValidationError(f"adjusted_close must be positive, was {adj}")
            object.__setattr__(self, "adjusted_close", adj)


_SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS bars_row_id START 1;

CREATE TABLE IF NOT EXISTS bars (
    -- Monotonic write order. The only reliable tiebreaker when two
    -- corrections carry the same available_at.
    row_id        BIGINT      PRIMARY KEY DEFAULT nextval('bars_row_id'),
    symbol        VARCHAR     NOT NULL,
    bar_size      VARCHAR     NOT NULL,
    event_time    TIMESTAMPTZ NOT NULL,
    available_at  TIMESTAMPTZ NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL,
    open          DOUBLE      NOT NULL,
    high          DOUBLE      NOT NULL,
    low           DOUBLE      NOT NULL,
    close         DOUBLE      NOT NULL,
    adjusted_close DOUBLE,
    volume        DOUBLE      NOT NULL,
    source        VARCHAR     NOT NULL,
    -- The database repeats the checks from Bar.__post_init__.
    -- Not redundant: the class protects against programming errors,
    -- the table protects against anyone who ever writes into it via SQL.
    CHECK (available_at >= event_time),
    CHECK (high >= low),
    CHECK (open BETWEEN low AND high),
    CHECK (close BETWEEN low AND high),
    CHECK (volume >= 0)
);

-- The filter available_at <= cut_off runs on every single access.
CREATE INDEX IF NOT EXISTS bars_pit_idx
    ON bars (symbol, bar_size, available_at, event_time);
"""

# Columns a PointInTimeView returns. row_id and ingested_at are deliberately
# missing: both describe the storage, not the market, and ingested_at is the
# most direct route to knowledge of the future.
_VIEW_COLUMNS = (
    "symbol",
    "bar_size",
    "event_time",
    "available_at",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "source",
)


class PointInTimeView:
    """View of the data as they were known at time ``cut_off``.

    The only object strategy code gets to see. There is no way from here to
    the raw table — not even by accident.

    If a bar has several versions (first report plus corrections), the view
    returns the **latest known** version with ``available_at <= cut_off``. A
    correction published only after ``cut_off`` stays invisible. That is
    exactly how things stood back then.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection, cut_off: dt.datetime) -> None:
        self._conn = conn
        self._cut_off = _require_aware("cut_off", cut_off)

    @property
    def cut_off(self) -> dt.datetime:
        """The cut-off date of this view (UTC)."""
        return self._cut_off

    def __repr__(self) -> str:
        return f"PointInTimeView(cut_off={self._cut_off.isoformat()})"

    def bars(
        self,
        symbol: str,
        bar_size: str = "1d",
        start: dt.datetime | None = None,
        end: dt.datetime | None = None,
    ) -> pd.DataFrame:
        """Bars of an instrument as they were known at the cut-off date.

        Args:
            symbol: Instrument ticker.
            bar_size: Bar length, default ``1d``.
            start: Earliest ``event_time`` (inclusive), optional.
            end: Latest ``event_time`` (inclusive), optional.

        Returns:
            DataFrame sorted by ``event_time`` ascending. Empty if nothing was
            known at the cut-off date — that is a valid result, not an error:
            before the IPO there simply were no prices.
        """
        conditions = ["symbol = ?", "bar_size = ?", "available_at <= ?"]
        params: list[Any] = [symbol, bar_size, self._cut_off]

        if start is not None:
            conditions.append("event_time >= ?")
            params.append(_require_aware("start", start))
        if end is not None:
            conditions.append("event_time <= ?")
            params.append(_require_aware("end", end))

        columns = ", ".join(_VIEW_COLUMNS)
        sql = f"""
            SELECT {columns}
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY symbol, bar_size, event_time
                    ORDER BY available_at DESC, row_id DESC
                ) AS _rank
                FROM bars
                WHERE {' AND '.join(conditions)}
            )
            WHERE _rank = 1
            ORDER BY event_time
        """
        return self._conn.execute(sql, params).df()

    def last_bar(self, symbol: str, bar_size: str = "1d") -> pd.Series | None:
        """The latest bar known at the cut-off date, or None."""
        frame = self.bars(symbol, bar_size)
        if frame.empty:
            return None
        return frame.iloc[-1]

    def symbols(self, bar_size: str | None = None) -> list[str]:
        """Instruments for which data were available at the cut-off date."""
        sql = "SELECT DISTINCT symbol FROM bars WHERE available_at <= ?"
        params: list[Any] = [self._cut_off]
        if bar_size is not None:
            sql += " AND bar_size = ?"
            params.append(bar_size)
        sql += " ORDER BY symbol"
        return [row[0] for row in self._conn.execute(sql, params).fetchall()]


class BitemporalStore:
    """Append-only store for market data on DuckDB.

    The class offers **no** update and **no** delete. That is not a gap in
    convenience but the point: whoever can overwrite a bar can rewrite the
    past, and then no backtest proves anything any more.

    A limit one has to know: the append-only promise holds for this API.
    Whoever opens their own DuckDB connection to the same file can delete via
    SQL. The layer does not protect against one's own determined access —
    against accidental access it does, and that is the common one.

    Example:
        >>> store = BitemporalStore(":memory:")
        >>> store.append(bars)
        >>> view = store.view(cut_off=datetime(2026, 3, 1, tzinfo=timezone.utc))
        >>> frame = view.bars("AAPL.US")
    """

    def __init__(self, path: str | Path = ":memory:", *, read_only: bool = False) -> None:
        """Opens or creates a database.

        Args:
            path: File path or ``:memory:``. Persistent databases belong in
                ``~/claude-local/trading-app/`` — outside iCloud, because
                iCloud syncs into an open database file and can corrupt it
                in the process (ADR-0003).
            read_only: Read-only access. For analyses alongside a running
                ingest.
        """
        self._path = str(path)
        self._conn = duckdb.connect(self._path, read_only=read_only)
        if not read_only:
            self._conn.execute(_SCHEMA)

    @property
    def path(self) -> str:
        return self._path

    def __enter__(self) -> BitemporalStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def append(
        self,
        bars: Iterable[Bar],
        *,
        ingested_at: dt.datetime | None = None,
    ) -> int:
        """Appends bars. Never changes existing rows.

        A correction is not a change but another row with a later
        ``available_at``. The old version stays and remains visible for
        cut-off dates before the correction.

        Args:
            bars: The bars to append.
            ingested_at: Storage time, default "now". Only to be set in
                tests — in operation this is the real clock.

        Returns:
            Number of rows written.

        Raises:
            BarValidationError: If an element is not a ``Bar``. The content
                check has then already taken place in ``Bar``.
        """
        now = (
            dt.datetime.now(dt.timezone.utc)
            if ingested_at is None
            else _require_aware("ingested_at", ingested_at)
        )

        rows: list[Sequence[Any]] = []
        for bar in bars:
            if not isinstance(bar, Bar):
                raise BarValidationError(
                    f"Expected a Bar, got: {type(bar).__name__}. "
                    "Raw tuples or dicts are not accepted — they bypass "
                    "input validation."
                )
            rows.append(
                (
                    bar.symbol,
                    bar.bar_size,
                    bar.event_time,
                    bar.available_at,
                    now,
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.adjusted_close,
                    bar.volume,
                    bar.source,
                )
            )

        if not rows:
            return 0

        self._conn.executemany(
            """
            INSERT INTO bars (
                symbol, bar_size, event_time, available_at, ingested_at,
                open, high, low, close, adjusted_close, volume, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    def view(self, cut_off: dt.datetime) -> PointInTimeView:
        """Creates the view of the state of knowledge at time ``cut_off``."""
        return PointInTimeView(self._conn, cut_off)

    def total_rows(self) -> int:
        """All rows ever written, corrections included.

        For operations and diagnostics only. Strategy code has no business
        here: the number includes rows that were not yet known at the
        cut-off date.
        """
        return int(self._conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0])

    def history(self, symbol: str, event_time: dt.datetime, bar_size: str = "1d") -> pd.DataFrame:
        """All versions of **one** bar, oldest first.

        The audit trail: it answers "when did this number change, and what was
        there before?". For operations and debugging, not for strategies.
        """
        return self._conn.execute(
            """
            SELECT row_id, symbol, bar_size, event_time, available_at, ingested_at,
                   open, high, low, close, adjusted_close, volume, source
            FROM bars
            WHERE symbol = ? AND bar_size = ? AND event_time = ?
            ORDER BY available_at, row_id
            """,
            [symbol, bar_size, _require_aware("event_time", event_time)],
        ).df()
