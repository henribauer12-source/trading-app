"""Instrument master data with per-field provenance (investment spec A5.1).

The layer beneath product selection A5: TER, tracking difference, fund size
and the remaining characteristics of ETFs and ETCs, every single value with
its provenance. A5.1 demands literally: "Stored per field: value, source URL,
as-of date, retrieval date". Per field, not per row: the TER comes from the
February KID, the fund size from the August factsheet. A model with *one*
as-of date per instrument cannot represent that and would later produce
wrong peer groups.

**Design: one narrow table, one row per field value**
(``isin, field, period, value, unit, source_url, source_type, status, as_of,
retrieved_at``), not a wide table with one column per field.

- A new field is an entry in ``FIELDS``, not a schema migration.
- The provenance is attached to every row, hence to every single value. The
  question "where exactly does this value come from, and how old is it?" is
  answered by the row itself. A wide table would need four companion columns
  per field for that, or again one row per document — and with it the single
  as-of date per row that is to be avoided here.
- Annual values (tracking difference per calendar year) are rows with
  ``period``, not columns ``td_2023``, ``td_2024`` …
- ``value`` is stored as text in the database and converted back per field
  type on reading. Rejected: a DuckDB ``DECIMAL`` column. It has a fixed
  number of decimal places and rounds silently (``0.12345678901`` becomes
  ``0.1235`` in ``DECIMAL(18,4)``), and ``.df()`` turns it into ``float64``.
  Both violate "``Decimal``, stored as published".
- The price of the narrow form: the database does not know a value's type.
  Type checking therefore sits in ``FieldValue`` and runs on writing *and*
  on reading.

Time axes (quality standards 3.2; investment spec A5.1, v1.3):

| Column         | Role as in ``bars``   | Meaning                                      |
|----------------|-----------------------|----------------------------------------------|
| `as_of`        | `event_time`          | date of the document the value comes from    |
| `retrieved_at` | `available_at`        | from when the app knew the value             |
| `ingested_at`  | `ingested_at`         | when this row was written                    |

The point-in-time key is ``retrieved_at``, not ``as_of``. The actual
publication lies somewhere in between and is rarely stated in the document;
the retrieval is the earliest moment at which the app knew the value for
certain. If several values are known for a field, the one with the latest
``as_of`` applies; for equal ``as_of``, the one retrieved last. An older
document that is recorded later therefore does not displace a newer one.

Naming (convention in ``bitemporal``): ``as_of`` is always the document date;
the query horizon is ``InstrumentView.cut_off``, compared with ``retrieved_at``.

Verification status per value: ``VERIFIED`` only if the value was read in the
primary document. Second-hand values (``source_type`` ``secondary``) may be
stored but are never ``VERIFIED``. What an unverified value does in the hard
filters is governed by ``hard_filters``.

There is no scraper. Values come from a hand-maintained, versioned JSON file
(``load_source_file``); the permitted single download of a mandatory document
is handled by ``sources.documents``. JSON rather than YAML because no package
for YAML is approved.

Format of the source file — one entry per document read; the provenance is
stated once on the document and applies to each of its values (placeholders,
no real data)::

    {"documents": [{
        "isin": "XX0000000002",
        "source_type": "kid",
        "source_url": "https://issuer.invalid/kid.pdf",
        "as_of": "2026-02-15",
        "retrieved_at": "2026-03-01T10:00:00+01:00",
        "status": "VERIFIED",
        "values": {
            "ter": 0.1234,
            "ucits": true,
            "tracking_difference": {"2024": -0.0123, "2025": 0.0456}
        }
    }]}

Numbers are read as ``Decimal``, never as ``float``. The unit of every field
is in ``FIELDS``: ``ter`` in percent per year, so ``0.5`` for 0.50 %.

Limit as with ``BitemporalStore``: the append-only promise holds for this API,
not for someone who writes into the file via SQL on their own connection.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from trading_app.bitemporal import BarValidationError, _require_aware

__all__ = [
    "FIELDS",
    "Distribution",
    "FieldType",
    "FieldValue",
    "FieldValueValidationError",
    "InstrumentStore",
    "InstrumentView",
    "Replication",
    "SourceType",
    "VerificationStatus",
    "load_source_file",
]


class FieldValueValidationError(ValueError):
    """A master-data value failed input validation."""


class SourceType(StrEnum):
    """Kind of document a value comes from."""

    KID = "kid"
    FACTSHEET = "factsheet"
    PROSPECTUS = "prospectus"
    ANNUAL_REPORT = "annual_report"
    ISSUER = "issuer"  # any other publication by the issuer
    EXCHANGE = "exchange"  # e.g. the Xetra operator: XLM, tradability
    STATUTE = "statute"
    SECONDARY = "secondary"  # second hand, e.g. a comparison portal


class VerificationStatus(StrEnum):
    """The spec's status labels (A0) VERIFIZIERT and UNVERIFIZIERT."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class Replication(StrEnum):
    """Levels as in A5.3, criterion "structure and counterparty risk"."""

    PHYSICAL_FULL = "physical_full"
    PHYSICAL_OPTIMISED = "physical_optimised"
    SYNTHETIC_SINGLE_COUNTERPARTY = "synthetic_single_counterparty"
    SYNTHETIC_MULTIPLE_COUNTERPARTIES = "synthetic_multiple_counterparties"


class Distribution(StrEnum):
    ACCUMULATING = "accumulating"
    DISTRIBUTING = "distributing"


# ---------------------------------------------------------------------------
# Field types
#
# Every check function takes the value in its Python form *or* in its text
# form from the database and returns the canonical Python form. That way the
# same check runs on reading as on writing.
# ---------------------------------------------------------------------------


def _decimal(value: object) -> Decimal:
    # bool is an int in Python: letting True through as 1 would be a silent
    # typo in the source file.
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise FieldValueValidationError(
            f"expected Decimal, int or text, got: {type(value).__name__}. "
            "float is forbidden — 0.1 as a float is not exactly 0.1."
        )
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise FieldValueValidationError(
            f"{value!r} is not a number (decimal point, no comma)"
        ) from None
    if not number.is_finite():
        raise FieldValueValidationError(f"{value!r} is not a finite number")
    return number


def _yes_no(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value in ("true", "false"):
        return value == "true"
    raise FieldValueValidationError(f"expected true or false, got: {value!r}")


def _date(value: object) -> dt.date:
    # datetime is a subclass of date and would carry a time of day.
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            pass
    raise FieldValueValidationError(
        f"expected a date YYYY-MM-DD without a time, got: {value!r}"
    )


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FieldValueValidationError(f"expected non-empty text, got: {value!r}")
    return value.strip()


def _country(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{2}", value):
        raise FieldValueValidationError(
            f"expected an ISO 3166-1 alpha-2 country code such as 'LU', got: {value!r}"
        )
    return value


def _choice(choices: type[StrEnum]) -> Callable[[object], StrEnum]:
    def check(value: object) -> StrEnum:
        try:
            return choices(value)
        except ValueError:
            allowed = ", ".join(e.value for e in choices)
            raise FieldValueValidationError(
                f"{value!r} is not allowed; allowed: {allowed}"
            ) from None

    return check


def _as_text(value: object) -> str:
    """Canonical text form for the database. Inverse: the check function."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.date):
        return value.isoformat()
    # Decimal: str() is exact and keeps the decimal places as published
    # ("0.1230" stays "0.1230"). StrEnum: the value.
    return str(value)


@dataclass(frozen=True, slots=True)
class FieldType:
    """How a field is checked and stored.

    Attributes:
        check: Check and conversion function.
        unit: Unit in which the value is stored; empty for characteristics.
        per_year: Annual value with the calendar year as ``period``.
    """

    check: Callable[[object], Any]
    unit: str = ""
    per_year: bool = False


# The fields that A5.2 and A5.3 need. A new field is one line here.
FIELDS: dict[str, FieldType] = {
    "ter": FieldType(_decimal, "% p. a."),
    # As published, unrounded. The materiality threshold of 0.05 pp is a
    # matter for scoring A5.3, not for storage.
    "tracking_difference": FieldType(_decimal, "percentage points p. a.", per_year=True),
    "fund_size": FieldType(_decimal, "EUR"),
    "replication_method": FieldType(_choice(Replication)),
    "domicile": FieldType(_country),
    "inception_date": FieldType(_date),
    # For filter 2 in the spelling of A5.5, where A5.5 names the index.
    "index_name": FieldType(_text),
    "distribution_type": FieldType(_choice(Distribution)),
    "ucits": FieldType(_yes_no),
    "kid_language_de": FieldType(_yes_no),
    "xetra_tradable": FieldType(_yes_no),
    "transaction_costs_kid": FieldType(_decimal, "percentage points"),
    "xlm": FieldType(_decimal, "basis points"),
    "equity_fund_invstg": FieldType(_yes_no),  # § 2 Abs. 6 InvStG
    "currency_hedged": FieldType(_yes_no),
    "holding_costs": FieldType(_decimal, "% p. a."),  # gold ETC only, replaces the TD
    # A5.2 no. 1 for gold: ETC under German law with an exclusive claim to
    # delivery of, or to the proceeds from, deposited gold.
    "gold_etc_delivery_claim": FieldType(_yes_no),
}


def _field_type(field: str) -> FieldType:
    field_type = FIELDS.get(field)
    if field_type is None:
        raise FieldValueValidationError(
            f"unknown field {field!r}. Known: {', '.join(FIELDS)}. "
            "A new field is an entry in FIELDS."
        )
    return field_type


_ISIN_PATTERN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")


def _check_isin(isin: object) -> str:
    """Format and check digit according to ISO 6166.

    The check digit catches most typos in a hand-maintained list — a
    transposed digit would otherwise silently yield a different instrument or
    none at all.
    """
    if not isinstance(isin, str) or not _ISIN_PATTERN.fullmatch(isin):
        raise FieldValueValidationError(
            f"ISIN {isin!r} does not have the ISO 6166 format "
            "(2 letters, 9 characters, 1 digit)"
        )
    # Letters to numbers (A=10 … Z=35), then Luhn over the digit string.
    digits = "".join(str(int(char, 36)) for char in isin[:-1])
    total = 0
    for position, char in enumerate(reversed(digits)):
        digit = int(char) * (2 if position % 2 == 0 else 1)
        total += digit // 10 + digit % 10
    if (10 - total % 10) % 10 != int(isin[-1]):
        raise FieldValueValidationError(f"ISIN {isin} has a wrong check digit — typo?")
    return isin


def _timestamp(name: str, value: dt.datetime) -> dt.datetime:
    """``_require_aware`` from ``bitemporal``, with this layer's error class."""
    try:
        return _require_aware(name, value)
    except BarValidationError as error:
        raise FieldValueValidationError(str(error)) from None


@dataclass(frozen=True, slots=True)
class FieldValue:
    """A single master-data value with its complete provenance.

    Immutable, like ``Bar``. Validation sits here and not in the store, so
    that there is no way to build an unchecked value.

    Attributes:
        isin: ISIN of the instrument; the check digit is verified.
        field: Name from ``FIELDS``.
        value: The value as published; type per field (``Decimal``, ``bool``,
            ``date``, text, choice). ``float`` is rejected.
        source_url: Where the value is stated.
        source_type: Kind of document.
        status: ``VERIFIED`` only for a primary document that was read.
        as_of: Date of the document.
        retrieved_at: From when the app knew the value, tz-aware.
        period: Calendar year for annual values, otherwise empty.
        unit: Set from ``FIELDS``. Given only as a cross-check.
    """

    isin: str
    field: str
    value: Any
    source_url: str
    source_type: SourceType
    status: VerificationStatus
    as_of: dt.date
    retrieved_at: dt.datetime
    period: str = ""
    unit: str | None = None

    def __post_init__(self) -> None:
        _check_isin(self.isin)
        field_type = _field_type(self.field)
        try:
            value = field_type.check(self.value)
        except FieldValueValidationError as error:
            raise FieldValueValidationError(f"{self.field}: {error}") from None

        unit = field_type.unit if self.unit is None else self.unit
        if unit != field_type.unit:
            raise FieldValueValidationError(
                f"{self.field} is stored in {field_type.unit!r}, {unit!r} was given. "
                "Convert, or change FIELDS — never mix silently."
            )

        url = urllib.parse.urlsplit(self.source_url) if isinstance(self.source_url, str) else None
        if url is None or url.scheme not in ("http", "https") or not url.netloc:
            raise FieldValueValidationError(
                f"source_url {self.source_url!r} is not an http(s) address. "
                "Without a source a value cannot be checked (A5.1)."
            )

        source_type = _choice(SourceType)(self.source_type)
        status = _choice(VerificationStatus)(self.status)
        if status is VerificationStatus.VERIFIED and source_type is SourceType.SECONDARY:
            raise FieldValueValidationError(
                "A second-hand value cannot be VERIFIED. VERIFIED means: "
                "read in the primary document (A5.1). Store it as UNVERIFIED."
            )

        as_of = _date(self.as_of)
        retrieved_at = _timestamp("retrieved_at", self.retrieved_at)
        # Like available_at >= event_time for bars (K2). Compared in UTC,
        # exactly like the CHECK in the table.
        if retrieved_at.date() < as_of:
            raise FieldValueValidationError(
                f"retrieved_at ({retrieved_at.isoformat()}) is before the as-of date "
                f"({as_of}). A document cannot be retrieved before it exists "
                "(K2; compared in UTC)."
            )

        if field_type.per_year:
            if not isinstance(self.period, str) or not re.fullmatch(r"\d{4}", self.period):
                raise FieldValueValidationError(
                    f"{self.field} is an annual value and needs the calendar year as "
                    f"period, e.g. '2025'; got: {self.period!r}"
                )
            if as_of < dt.date(int(self.period), 12, 31):
                raise FieldValueValidationError(
                    f"{self.field} {self.period} with as-of date {as_of}: an annual value "
                    "is final at year end at the earliest."
                )
        elif self.period != "":
            raise FieldValueValidationError(
                f"{self.field} has no periods; period must be empty, was {self.period!r}"
            )

        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "retrieved_at", retrieved_at)


_SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS instrument_fields_row_id START 1;

CREATE TABLE IF NOT EXISTS instrument_fields (
    -- Monotonic write order, last tiebreaker as in bars.
    row_id        BIGINT      PRIMARY KEY DEFAULT nextval('instrument_fields_row_id'),
    isin          VARCHAR     NOT NULL,
    field         VARCHAR     NOT NULL,
    -- Calendar year for annual values, otherwise ''. Not NULL, so that
    -- equality works without a special case.
    period        VARCHAR     NOT NULL,
    -- Canonical text; converted back per field type in Python (module docstring).
    value         VARCHAR     NOT NULL,
    unit          VARCHAR     NOT NULL,
    source_url    VARCHAR     NOT NULL,
    source_type   VARCHAR     NOT NULL,
    status        VARCHAR     NOT NULL,
    as_of         DATE        NOT NULL,
    retrieved_at  TIMESTAMPTZ NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL,
    -- Repeats the checks from FieldValue that do without FIELDS.
    CHECK (status IN ('VERIFIED', 'UNVERIFIED')),
    CHECK (status = 'UNVERIFIED' OR source_type <> 'secondary'),
    -- timezone('UTC', …), otherwise the result would depend on the
    -- machine's time zone.
    CHECK (CAST(timezone('UTC', retrieved_at) AS DATE) >= as_of)
);

CREATE INDEX IF NOT EXISTS instrument_fields_pit_idx
    ON instrument_fields (isin, field, retrieved_at);
"""

# What a view returns, in the order of the FieldValue attributes.
# row_id and ingested_at are deliberately missing — as with PointInTimeView.
_VIEW_COLUMNS = (
    "isin",
    "field",
    "value",
    "source_url",
    "source_type",
    "status",
    "as_of",
    "retrieved_at",
    "period",
    "unit",
)


class InstrumentView:
    """Master data as it was known at time ``cut_off``.

    The only object product selection gets to see. It returns only values
    with ``retrieved_at`` at or before this view's ``cut_off``; a factsheet
    retrieved only after the cut-off date does not exist for this view. There
    is no method that returns "everything".
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection, cut_off: dt.datetime) -> None:
        self._conn = conn
        self._cut_off = _timestamp("cut_off", cut_off)

    @property
    def cut_off(self) -> dt.datetime:
        """The cut-off date of this view (UTC)."""
        return self._cut_off

    def __repr__(self) -> str:
        return f"InstrumentView(cut_off={self._cut_off.isoformat()})"

    def field(self, isin: str, field: str) -> FieldValue | None:
        """The value of a field in force at the cut-off date, or None.

        No value is a valid result, not an error: before the first retrieval
        the app knew nothing about the instrument.
        """
        if _field_type(field).per_year:
            raise FieldValueValidationError(f"{field} is an annual value — use series()")
        values = self._current(isin, field)
        return values[0] if values else None

    def series(self, isin: str, field: str) -> dict[str, FieldValue]:
        """The annual values of a field in force at the cut-off date, year ascending."""
        if not _field_type(field).per_year:
            raise FieldValueValidationError(f"{field} is not an annual value — use field()")
        return {value.period: value for value in self._current(isin, field)}

    def isins(self) -> list[str]:
        """Instruments for which at least one value was known at the cut-off date."""
        rows = self._conn.execute(
            "SELECT DISTINCT isin FROM instrument_fields WHERE retrieved_at <= ? ORDER BY isin",
            [self._cut_off],
        ).fetchall()
        return [row[0] for row in rows]

    def _current(self, isin: str, field: str) -> list[FieldValue]:
        """Per period the value in force: latest as-of date, then latest retrieval."""
        columns = ", ".join(_VIEW_COLUMNS)
        sql = f"""
            SELECT {columns}
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY period
                    ORDER BY as_of DESC, retrieved_at DESC, row_id DESC
                ) AS _rank
                FROM instrument_fields
                WHERE isin = ? AND field = ? AND retrieved_at <= ?
            )
            WHERE _rank = 1
            ORDER BY period
        """
        rows = self._conn.execute(sql, [isin, field, self._cut_off]).fetchall()
        # Back through FieldValue: the same check as on writing, also against
        # rows that someone wrote via SQL, bypassing the API.
        return [FieldValue(*row) for row in rows]


_SAME_ROW = """
    SELECT 1 FROM instrument_fields
    WHERE isin = ? AND field = ? AND period = ? AND value = ? AND unit = ?
      AND source_url = ? AND source_type = ? AND status = ? AND as_of = ?
      AND retrieved_at = ?
    LIMIT 1
"""

_INSERT = """
    INSERT INTO instrument_fields (
        isin, field, period, value, unit, source_url, source_type, status,
        as_of, retrieved_at, ingested_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class InstrumentStore:
    """Append-only store for instrument master data on DuckDB.

    No update, no delete — for the same reason as with ``BitemporalStore``.
    A corrected TER is a new row with a later ``retrieved_at``; the old one
    stays visible for earlier cut-off dates.

    Example:
        >>> store = InstrumentStore(":memory:")
        >>> store.append(load_source_file("instruments.json"))
        >>> view = store.view(cut_off=datetime(2026, 9, 1, tzinfo=timezone.utc))
        >>> view.field("XX0000000002", "ter")
    """

    def __init__(self, path: str | Path = ":memory:", *, read_only: bool = False) -> None:
        """Opens or creates a database.

        Args:
            path: File path or ``:memory:``. Persistent databases belong in
                ``~/claude-local/trading-app/``, outside iCloud (ADR-0003).
            read_only: Read-only access.
        """
        self._path = str(path)
        self._conn = duckdb.connect(self._path, read_only=read_only)
        if not read_only:
            self._conn.execute(_SCHEMA)

    @property
    def path(self) -> str:
        return self._path

    def __enter__(self) -> InstrumentStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def append(
        self,
        values: Iterable[FieldValue],
        *,
        ingested_at: dt.datetime | None = None,
    ) -> int:
        """Appends values. Never changes existing rows.

        A verbatim repetition — the same source file loaded a second time — is
        skipped, so that reloading stays idempotent. Any difference, even just
        in the retrieval date, is a new row. All or nothing: if one row fails,
        none is written.

        Args:
            values: The values to append.
            ingested_at: Storage time, default "now". Tests only.

        Returns:
            Number of newly written rows.

        Raises:
            FieldValueValidationError: If an element is not a ``FieldValue``.
        """
        now = (
            dt.datetime.now(dt.timezone.utc)
            if ingested_at is None
            else _timestamp("ingested_at", ingested_at)
        )

        rows: list[Sequence[Any]] = []
        for value in values:
            if not isinstance(value, FieldValue):
                raise FieldValueValidationError(
                    f"Expected a FieldValue, got: {type(value).__name__}. "
                    "Raw dicts are not accepted — they bypass input validation."
                )
            rows.append(
                (
                    value.isin,
                    value.field,
                    value.period,
                    _as_text(value.value),
                    value.unit,
                    value.source_url,
                    value.source_type.value,
                    value.status.value,
                    value.as_of,
                    value.retrieved_at,
                )
            )

        written = 0
        self._conn.begin()
        try:
            for row in rows:
                if self._conn.execute(_SAME_ROW, row).fetchone():
                    continue
                self._conn.execute(_INSERT, [*row, now])
                written += 1
        except BaseException:
            self._conn.rollback()
            raise
        self._conn.commit()
        return written

    def view(self, cut_off: dt.datetime) -> InstrumentView:
        """Creates the view of the state of knowledge at time ``cut_off``."""
        return InstrumentView(self._conn, cut_off)

    def total_rows(self) -> int:
        """All rows ever written. For operations and diagnostics only."""
        return int(self._conn.execute("SELECT COUNT(*) FROM instrument_fields").fetchone()[0])

    def history(self, isin: str, field: str, period: str = "") -> pd.DataFrame:
        """All versions of a field, in write order.

        The audit trail: when did this value change, and where did each
        version come from? For operations and debugging, not for product
        selection.
        """
        return self._conn.execute(
            """
            SELECT row_id, isin, field, period, value, unit, source_url, source_type,
                   status, as_of, retrieved_at, ingested_at
            FROM instrument_fields
            WHERE isin = ? AND field = ? AND period = ?
            ORDER BY row_id
            """,
            [isin, field, period],
        ).df()


# ---------------------------------------------------------------------------
# Source file
# ---------------------------------------------------------------------------

_DOCUMENT_KEYS = frozenset(
    {"isin", "source_type", "source_url", "as_of", "retrieved_at", "status", "values"}
)


def load_source_file(path: str | Path) -> list[FieldValue]:
    """Reads the hand-maintained source file (format in the module docstring).

    Only the local file, no network connection. Numbers are read as
    ``Decimal``.

    Raises:
        FieldValueValidationError: with the number of the document in the
            file, so that the error can be found.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
    if not isinstance(data, dict) or set(data) != {"documents"} or not isinstance(
        data["documents"], list
    ):
        raise FieldValueValidationError(
            'The source file needs exactly one key "documents" holding a list.'
        )

    values: list[FieldValue] = []
    for number, document in enumerate(data["documents"], start=1):
        try:
            values.extend(_values_from_document(document))
        except (ValueError, TypeError) as error:  # FieldValueValidationError is a ValueError
            raise FieldValueValidationError(f"Document {number}: {error}") from None
    return values


def _values_from_document(document: object) -> list[FieldValue]:
    if not isinstance(document, dict):
        raise FieldValueValidationError("Entry is not an object")
    if set(document) != _DOCUMENT_KEYS:
        raise FieldValueValidationError(
            f"Keys missing: {sorted(_DOCUMENT_KEYS - set(document))}; "
            f"unknown: {sorted(set(document) - _DOCUMENT_KEYS)}"
        )
    if not isinstance(document["values"], dict):
        raise FieldValueValidationError('"values" is not an object')

    provenance = {
        "isin": document["isin"],
        "source_type": document["source_type"],
        "source_url": document["source_url"],
        "as_of": document["as_of"],
        "status": document["status"],
        "retrieved_at": dt.datetime.fromisoformat(document["retrieved_at"]),
    }
    values: list[FieldValue] = []
    for field, value in document["values"].items():
        if not _field_type(field).per_year:
            values.append(FieldValue(field=field, value=value, **provenance))
            continue
        if not isinstance(value, dict):
            raise FieldValueValidationError(
                f'{field} is an annual value: expected {{"2025": …}}, got {value!r}'
            )
        values += [
            FieldValue(field=field, value=v, period=p, **provenance) for p, v in value.items()
        ]
    return values
