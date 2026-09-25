"""Bitemporale Datenhaltung und Point-in-time-Zugriff.

Der Kern von Phase 1. Zwei Regeln bestimmen den gesamten Entwurf:

1. **Append-only.** Eine einmal geschriebene Zeile wird nie geändert und nie
   gelöscht. Korrekturen kommen als neue Zeile mit späterem `available_at`
   herein. Damit bleibt rekonstruierbar, was die App zu einem beliebigen
   Zeitpunkt der Vergangenheit *geglaubt* hat — nicht nur, was heute stimmt.

2. **`PointInTimeView` ist die einzige Schnittstelle für Strategiecode.**
   Sie liefert ausschließlich Zeilen mit `available_at <= as_of`. Ohne diese
   Sperre wandert früher oder später Zukunftswissen in ein Signal, und der
   Backtest wird wertlos, ohne dass irgendetwas abstürzt.

Drei Zeitstempel pro Zeile (Qualitätsstandards Abschnitt 3.2):

| Feld           | Bedeutung                                              |
|----------------|--------------------------------------------------------|
| `event_time`   | wann es passierte — hier: Ende der Bar                 |
| `available_at` | ab wann es öffentlich bekannt war                      |
| `ingested_at`  | wann diese App es gespeichert hat                      |

`event_time` und `available_at` fallen auseinander, sobald Daten verzögert
veröffentlicht oder nachträglich korrigiert werden. Genau diese Lücke ist der
Grund für bitemporale Haltung.

Preise werden doppelt geführt — `close` wie gehandelt, `adjusted_close` um
Splits und Dividenden bereinigt. Warum das kein Luxus ist, steht in
`docs/20260925_rueckwirkende-anpassung.md`: Über zwölf Monate AAPL trennt die
beiden Spalten fast ein halber Prozentpunkt Rendite, immer in dieselbe Richtung.
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
    """Eine Bar hat die Eingangsprüfung nicht bestanden.

    Bewusst eine eigene Klasse: Ein Loader soll gezielt auf fehlerhafte
    Marktdaten reagieren können, ohne jeden anderen ValueError mitzufangen.
    """


def _require_aware(name: str, wert: dt.datetime) -> dt.datetime:
    """Zeitzonenlose Zeitstempel zurückweisen und alles auf UTC normieren.

    Ein naiver Zeitstempel ist die stillste Fehlerquelle der ganzen Schicht:
    Der Vergleich `available_at <= as_of` läuft dann je nach Sommerzeit bis zu
    zwei Stunden falsch, wirft aber keine Meldung. Zwei Stunden reichen für
    Look-ahead über einen Handelstag hinweg.
    """
    if not isinstance(wert, dt.datetime):
        raise BarValidationError(f"{name} muss ein datetime sein, war {type(wert).__name__}")
    if wert.tzinfo is None or wert.tzinfo.utcoffset(wert) is None:
        raise BarValidationError(
            f"{name} ist zeitzonenlos. Zeitzonenlose Zeitstempel sind verboten — "
            "sie vergleichen sich je nach Sommerzeit bis zu zwei Stunden falsch. "
            "Erwartet wird ein tz-bewusstes datetime, z. B. mit tz=datetime.timezone.utc."
        )
    return wert.astimezone(dt.timezone.utc)


@dataclass(frozen=True, slots=True)
class Bar:
    """Eine OHLCV-Bar mit ihren beiden Zeitachsen.

    Unveränderlich (`frozen=True`), weil eine bereits geprüfte Bar auf dem Weg
    in die Datenbank nicht mehr verändert werden können soll.

    Attribute:
        symbol: Instrumentenkürzel, z. B. ``AAPL.US``.
        bar_size: Bar-Länge als Text, z. B. ``1d``, ``1h``, ``1m``.
        event_time: Ende der Bar, tz-bewusst.
        available_at: Ab wann die Bar öffentlich bekannt war, tz-bewusst.
        open, high, low, close: Preise **wie gehandelt**, unbereinigt.
        adjusted_close: Um Splits/Dividenden bereinigter Schlusskurs, oder None.
        volume: Gehandelte Stückzahl.
        source: Herkunft, z. B. ``eodhd``. Bei widersprüchlichen Quellen die
            einzige Chance, hinterher zu erkennen, wem zu glauben ist.
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
            raise BarValidationError("symbol darf nicht leer sein")
        if not self.bar_size or not self.bar_size.strip():
            raise BarValidationError("bar_size darf nicht leer sein")
        if not self.source or not self.source.strip():
            raise BarValidationError("source darf nicht leer sein — Herkunft ist Pflicht")

        event_time = _require_aware("event_time", self.event_time)
        available_at = _require_aware("available_at", self.available_at)

        # Konvention K2 der Rechenkern-Spezifikation: Eine Bar ist frühestens
        # ab ihrem Endzeitpunkt verfügbar. Wäre available_at < event_time,
        # könnte eine Strategie den Schlusskurs kennen, bevor er feststeht.
        if available_at < event_time:
            raise BarValidationError(
                f"available_at ({available_at.isoformat()}) liegt vor event_time "
                f"({event_time.isoformat()}). Eine Bar kann nicht bekannt sein, "
                "bevor sie zu Ende ist (Konvention K2)."
            )

        object.__setattr__(self, "event_time", event_time)
        object.__setattr__(self, "available_at", available_at)

        preise = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
        for name, wert in preise.items():
            if wert is None:
                raise BarValidationError(f"{name} fehlt")
            zahl = float(wert)
            if zahl != zahl:  # NaN
                raise BarValidationError(f"{name} ist NaN")
            if zahl <= 0:
                raise BarValidationError(f"{name} muss positiv sein, war {zahl}")
            object.__setattr__(self, name, zahl)

        if self.high < self.low:
            raise BarValidationError(f"high ({self.high}) liegt unter low ({self.low})")
        if not (self.low <= self.open <= self.high):
            raise BarValidationError(
                f"open ({self.open}) liegt außerhalb [low={self.low}, high={self.high}]"
            )
        if not (self.low <= self.close <= self.high):
            raise BarValidationError(
                f"close ({self.close}) liegt außerhalb [low={self.low}, high={self.high}]"
            )

        volume = float(self.volume)
        if volume != volume:
            raise BarValidationError("volume ist NaN")
        if volume < 0:
            raise BarValidationError(f"volume darf nicht negativ sein, war {volume}")
        object.__setattr__(self, "volume", volume)

        if self.adjusted_close is not None:
            adj = float(self.adjusted_close)
            if adj != adj:
                raise BarValidationError("adjusted_close ist NaN")
            if adj <= 0:
                raise BarValidationError(f"adjusted_close muss positiv sein, war {adj}")
            object.__setattr__(self, "adjusted_close", adj)


_SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS bars_row_id START 1;

CREATE TABLE IF NOT EXISTS bars (
    -- Monotone Schreibreihenfolge. Einziger verlässlicher Tiebreaker, wenn
    -- zwei Korrekturen denselben available_at tragen.
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
    -- Die Datenbank wiederholt die Prüfungen aus Bar.__post_init__.
    -- Nicht doppelt gemoppelt: Die Klasse schützt vor Programmierfehlern,
    -- die Tabelle schützt vor jedem, der je per SQL hineinschreibt.
    CHECK (available_at >= event_time),
    CHECK (high >= low),
    CHECK (open BETWEEN low AND high),
    CHECK (close BETWEEN low AND high),
    CHECK (volume >= 0)
);

-- Der Filter available_at <= as_of läuft bei jedem einzelnen Zugriff.
CREATE INDEX IF NOT EXISTS bars_pit_idx
    ON bars (symbol, bar_size, available_at, event_time);
"""

# Spalten, die eine PointInTimeView nach außen gibt. row_id und ingested_at
# fehlen bewusst: Beide beschreiben die Speicherung, nicht den Markt, und
# ingested_at ist der direkteste Weg zu Zukunftswissen.
_VIEW_SPALTEN = (
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
    """Sicht auf die Daten, wie sie zum Zeitpunkt ``as_of`` bekannt waren.

    Das einzige Objekt, das Strategiecode zu sehen bekommt. Es gibt keinen Weg
    von hier zur rohen Tabelle — auch nicht versehentlich.

    Gibt es zu einer Bar mehrere Fassungen (Erstmeldung plus Korrekturen),
    liefert die Sicht die **zuletzt bekannte** Fassung mit
    ``available_at <= as_of``. Eine Korrektur, die erst nach ``as_of``
    veröffentlicht wurde, bleibt unsichtbar. Genau so war die Lage damals.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection, as_of: dt.datetime) -> None:
        self._conn = conn
        self._as_of = _require_aware("as_of", as_of)

    @property
    def as_of(self) -> dt.datetime:
        """Der Stichtag dieser Sicht (UTC)."""
        return self._as_of

    def __repr__(self) -> str:
        return f"PointInTimeView(as_of={self._as_of.isoformat()})"

    def bars(
        self,
        symbol: str,
        bar_size: str = "1d",
        start: dt.datetime | None = None,
        end: dt.datetime | None = None,
    ) -> pd.DataFrame:
        """Bars eines Instruments, wie sie am Stichtag bekannt waren.

        Args:
            symbol: Instrumentenkürzel.
            bar_size: Bar-Länge, Vorgabe ``1d``.
            start: Frühestes ``event_time`` (einschließlich), optional.
            end: Spätestes ``event_time`` (einschließlich), optional.

        Returns:
            DataFrame nach ``event_time`` aufsteigend sortiert. Leer, wenn zum
            Stichtag nichts bekannt war — das ist ein gültiges Ergebnis, kein
            Fehler: Vor dem Börsengang gab es eben keine Kurse.
        """
        bedingungen = ["symbol = ?", "bar_size = ?", "available_at <= ?"]
        parameter: list[Any] = [symbol, bar_size, self._as_of]

        if start is not None:
            bedingungen.append("event_time >= ?")
            parameter.append(_require_aware("start", start))
        if end is not None:
            bedingungen.append("event_time <= ?")
            parameter.append(_require_aware("end", end))

        spalten = ", ".join(_VIEW_SPALTEN)
        sql = f"""
            SELECT {spalten}
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY symbol, bar_size, event_time
                    ORDER BY available_at DESC, row_id DESC
                ) AS _rang
                FROM bars
                WHERE {' AND '.join(bedingungen)}
            )
            WHERE _rang = 1
            ORDER BY event_time
        """
        return self._conn.execute(sql, parameter).df()

    def letzte_bar(self, symbol: str, bar_size: str = "1d") -> pd.Series | None:
        """Die jüngste am Stichtag bekannte Bar, oder None."""
        frame = self.bars(symbol, bar_size)
        if frame.empty:
            return None
        return frame.iloc[-1]

    def symbole(self, bar_size: str | None = None) -> list[str]:
        """Instrumente, zu denen am Stichtag Daten vorlagen."""
        sql = "SELECT DISTINCT symbol FROM bars WHERE available_at <= ?"
        parameter: list[Any] = [self._as_of]
        if bar_size is not None:
            sql += " AND bar_size = ?"
            parameter.append(bar_size)
        sql += " ORDER BY symbol"
        return [zeile[0] for zeile in self._conn.execute(sql, parameter).fetchall()]


class BitemporalStore:
    """Append-only-Speicher für Marktdaten auf DuckDB.

    Die Klasse bietet **kein** Update und **kein** Delete. Das ist keine
    Bequemlichkeitslücke, sondern der Zweck: Wer eine Bar überschreiben kann,
    kann die Vergangenheit umschreiben, und dann beweist kein Backtest mehr
    irgendetwas.

    Grenze, die man kennen muss: Die Append-only-Zusage gilt für diese API.
    Wer sich eine eigene DuckDB-Verbindung auf dieselbe Datei öffnet, kann
    per SQL löschen. Gegen den eigenen entschlossenen Zugriff schützt die
    Schicht nicht — gegen den versehentlichen schon, und der ist der häufige.

    Beispiel:
        >>> store = BitemporalStore(":memory:")
        >>> store.append(bars)
        >>> sicht = store.view(as_of=datetime(2026, 3, 1, tzinfo=timezone.utc))
        >>> frame = sicht.bars("AAPL.US")
    """

    def __init__(self, path: str | Path = ":memory:", *, read_only: bool = False) -> None:
        """Öffnet oder erzeugt eine Datenbank.

        Args:
            path: Dateipfad oder ``:memory:``. Dauerhafte Datenbanken gehören
                nach ``~/claude-local/trading-app/`` — außerhalb von iCloud,
                weil iCloud in eine offene Datenbankdatei hineinsynchronisiert
                und sie dabei beschädigen kann (ADR-0003).
            read_only: Nur-Lese-Zugriff. Für Auswertungen neben einem
                laufenden Ingest.
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
        """Hängt Bars an. Ändert niemals bestehende Zeilen.

        Eine Korrektur ist keine Änderung, sondern eine weitere Zeile mit
        späterem ``available_at``. Die alte Fassung bleibt stehen und bleibt
        für Stichtage vor der Korrektur sichtbar.

        Args:
            bars: Die anzuhängenden Bars.
            ingested_at: Speicherzeitpunkt, Vorgabe „jetzt". Nur für Tests
                zu setzen — im Betrieb ist das die echte Uhr.

        Returns:
            Zahl der geschriebenen Zeilen.

        Raises:
            BarValidationError: Wenn ein Element keine ``Bar`` ist. Die
                inhaltliche Prüfung hat dann schon in ``Bar`` stattgefunden.
        """
        jetzt = (
            dt.datetime.now(dt.timezone.utc)
            if ingested_at is None
            else _require_aware("ingested_at", ingested_at)
        )

        zeilen: list[Sequence[Any]] = []
        for bar in bars:
            if not isinstance(bar, Bar):
                raise BarValidationError(
                    f"Erwartet wurde eine Bar, bekommen: {type(bar).__name__}. "
                    "Rohe Tupel oder dicts werden nicht angenommen — sie umgehen "
                    "die Eingangsprüfung."
                )
            zeilen.append(
                (
                    bar.symbol,
                    bar.bar_size,
                    bar.event_time,
                    bar.available_at,
                    jetzt,
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.adjusted_close,
                    bar.volume,
                    bar.source,
                )
            )

        if not zeilen:
            return 0

        self._conn.executemany(
            """
            INSERT INTO bars (
                symbol, bar_size, event_time, available_at, ingested_at,
                open, high, low, close, adjusted_close, volume, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            zeilen,
        )
        return len(zeilen)

    def view(self, as_of: dt.datetime) -> PointInTimeView:
        """Erzeugt die Sicht auf den Wissensstand zum Zeitpunkt ``as_of``."""
        return PointInTimeView(self._conn, as_of)

    def zeilen_gesamt(self) -> int:
        """Alle je geschriebenen Zeilen, Korrekturen eingeschlossen.

        Nur für Betrieb und Diagnose. Strategiecode hat hier nichts zu suchen:
        Die Zahl enthält Zeilen, die zum Stichtag noch nicht bekannt waren.
        """
        return int(self._conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0])

    def historie(self, symbol: str, event_time: dt.datetime, bar_size: str = "1d") -> pd.DataFrame:
        """Alle Fassungen **einer** Bar, älteste zuerst.

        Die Prüfspur: Sie beantwortet „wann hat sich diese Zahl geändert, und
        was stand vorher da?". Für Betrieb und Fehlersuche, nicht für
        Strategien.
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
