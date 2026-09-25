"""Instrument-Stammdaten mit feldweiser Herkunft (Anlage-Spezifikation A5.1).

Die Schicht unter der Produktauswahl A5: TER, Tracking-Differenz,
Fondsvolumen und die übrigen Merkmale von ETFs und ETCs, jeder einzelne Wert
mit seiner Herkunft. A5.1 verlangt wörtlich: „Je Feld gespeichert: Wert,
Quell-URL, Stand-Datum, Abrufdatum“. Feldweise, nicht zeilenweise: Die TER
stammt aus dem KID vom Februar, das Fondsvolumen aus dem Factsheet vom August.
Ein Modell mit *einem* Stand-Datum je Instrument kann das nicht abbilden und
würde später falsche Vergleichsgruppen erzeugen.

**Entwurf: eine schmale Tabelle, eine Zeile je Feldwert**
(``isin, feld, periode, wert, einheit, quelle_url, quelle_typ, status, stand,
abgerufen_am``), keine breite Tabelle mit einer Spalte je Feld.

- Ein neues Feld ist ein Eintrag in ``FELDER``, keine Schemamigration.
- Die Herkunft hängt an jeder Zeile, also an jedem einzelnen Wert. Die Frage
  „woher stammt genau dieser Wert, und wie alt ist er?“ beantwortet die Zeile
  selbst. Eine breite Tabelle bräuchte dafür vier Begleitspalten je Feld oder
  wieder eine Zeile je Dokument — und damit das eine Stand-Datum pro Zeile,
  das hier vermieden werden soll.
- Jahreswerte (Tracking-Differenz je Kalenderjahr) sind Zeilen mit
  ``periode``, keine Spalten ``td_2023``, ``td_2024`` …
- ``wert`` steht als Text in der Datenbank und wird beim Lesen je Feldtyp
  zurückverwandelt. Verworfen: eine DuckDB-``DECIMAL``-Spalte. Die hat eine
  feste Nachkommazahl und rundet still (``0.12345678901`` wird in
  ``DECIMAL(18,4)`` zu ``0.1235``), und ``.df()`` macht aus ihr ``float64``.
  Beides verletzt „``Decimal``, gespeichert wie veröffentlicht“.
- Preis der schmalen Form: Die Datenbank kennt den Typ eines Werts nicht. Die
  Typprüfung sitzt deshalb in ``Feldwert`` und läuft beim Schreiben *und*
  beim Lesen.

Zeitachsen (Qualitätsstandards 3.2; Anlage-Spezifikation A5.1, v1.3):

| Spalte         | Rolle wie in ``bars`` | Bedeutung                                    |
|----------------|-----------------------|----------------------------------------------|
| `stand`        | `event_time`          | Datum des Dokuments, aus dem der Wert stammt |
| `abgerufen_am` | `available_at`        | ab wann die App den Wert kannte              |
| `ingested_at`  | `ingested_at`         | wann diese Zeile geschrieben wurde           |

Point-in-time-Schlüssel ist ``abgerufen_am``, nicht ``stand``. Die echte
Veröffentlichung liegt irgendwo dazwischen und steht selten im Dokument; der
Abruf ist der früheste Zeitpunkt, zu dem die App den Wert sicher kannte. Sind
zu einem Feld mehrere Werte bekannt, gilt der mit dem jüngsten ``stand``, bei
gleichem Stand der zuletzt abgerufene. Ein älteres Dokument, das erst später
erfasst wird, verdrängt also kein neueres.

Prüfstatus je Wert: ``VERIFIZIERT`` nur, wenn der Wert im Primärdokument
gelesen wurde. Werte zweiter Hand (``quelle_typ`` ``sekundaer``) dürfen
gespeichert werden, sind aber nie ``VERIFIZIERT``. Was ein unverifizierter
Wert in den harten Filtern bewirkt, regelt ``harte_filter``.

Es gibt keinen Scraper. Werte kommen aus einer von Hand gepflegten,
versionierten JSON-Datei (``lade_quelldatei``); den erlaubten Einzeldownload
eines Pflichtdokuments erledigt ``sources.dokumente``. JSON statt YAML, weil
für YAML kein Paket freigegeben ist.

Format der Quelldatei — ein Eintrag je gelesenem Dokument; die Herkunft steht
einmal am Dokument und gilt für jeden seiner Werte (Platzhalter, keine echten
Daten)::

    {"dokumente": [{
        "isin": "XX0000000002",
        "quelle_typ": "kid",
        "quelle_url": "https://emittent.invalid/kid.pdf",
        "stand": "2026-02-15",
        "abgerufen_am": "2026-03-01T10:00:00+01:00",
        "status": "VERIFIZIERT",
        "werte": {
            "ter": 0.1234,
            "ucits": true,
            "tracking_differenz": {"2024": -0.0123, "2025": 0.0456}
        }
    }]}

Zahlen werden als ``Decimal`` gelesen, nie als ``float``. Die Einheit jedes
Felds steht in ``FELDER``: ``ter`` in Prozent pro Jahr, also ``0.5`` für
0,50 %.

Grenze wie bei ``BitemporalStore``: Die Append-only-Zusage gilt für diese API,
nicht für jemanden, der mit eigener Verbindung per SQL in die Datei schreibt.
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
    "FELDER",
    "Ausschuettung",
    "Feldtyp",
    "Feldwert",
    "FeldwertValidationError",
    "InstrumentStore",
    "InstrumentView",
    "Pruefstatus",
    "QuelleTyp",
    "Replikation",
    "lade_quelldatei",
]


class FeldwertValidationError(ValueError):
    """Ein Stammdatenwert hat die Eingangsprüfung nicht bestanden."""


class QuelleTyp(StrEnum):
    """Art des Dokuments, aus dem ein Wert stammt."""

    KID = "kid"
    FACTSHEET = "factsheet"
    PROSPEKT = "prospekt"
    JAHRESBERICHT = "jahresbericht"
    EMITTENT = "emittent"  # sonstige Veröffentlichung des Emittenten
    BOERSE = "boerse"  # z. B. Deutsche Börse: XLM, Handelbarkeit
    GESETZ = "gesetz"
    SEKUNDAER = "sekundaer"  # zweite Hand, z. B. ein Vergleichsportal


class Pruefstatus(StrEnum):
    """Kennzeichnung wie in der Spezifikation (A0, „Status-Kennzeichnung“)."""

    VERIFIZIERT = "VERIFIZIERT"
    UNVERIFIZIERT = "UNVERIFIZIERT"


class Replikation(StrEnum):
    """Stufen wie in A5.3, Kriterium „Struktur und Gegenparteirisiko“."""

    PHYSISCH_VOLLSTAENDIG = "physisch_vollstaendig"
    PHYSISCH_OPTIMIERT = "physisch_optimiert"
    SYNTHETISCH_EINE_GEGENPARTEI = "synthetisch_eine_gegenpartei"
    SYNTHETISCH_MEHRERE_GEGENPARTEIEN = "synthetisch_mehrere_gegenparteien"


class Ausschuettung(StrEnum):
    THESAURIEREND = "thesaurierend"
    AUSSCHUETTEND = "ausschuettend"


# ---------------------------------------------------------------------------
# Feldtypen
#
# Jede Prüffunktion nimmt den Wert in seiner Python-Form *oder* in seiner
# Textform aus der Datenbank und gibt die kanonische Python-Form zurück. So
# läuft beim Lesen dieselbe Prüfung wie beim Schreiben.
# ---------------------------------------------------------------------------


def _dezimal(wert: object) -> Decimal:
    # bool ist in Python ein int: True als 1 durchzulassen wäre ein stiller
    # Tippfehler in der Quelldatei.
    if isinstance(wert, bool) or not isinstance(wert, (Decimal, int, str)):
        raise FeldwertValidationError(
            f"erwartet wird Decimal, int oder Text, bekommen: {type(wert).__name__}. "
            "float ist verboten — 0.1 als float ist nicht genau 0,1."
        )
    try:
        zahl = Decimal(wert)
    except InvalidOperation:
        raise FeldwertValidationError(
            f"{wert!r} ist keine Zahl (Dezimalpunkt, kein Komma)"
        ) from None
    if not zahl.is_finite():
        raise FeldwertValidationError(f"{wert!r} ist keine endliche Zahl")
    return zahl


def _ja_nein(wert: object) -> bool:
    if isinstance(wert, bool):
        return wert
    if wert in ("true", "false"):
        return wert == "true"
    raise FeldwertValidationError(f"erwartet wird true oder false, bekommen: {wert!r}")


def _datum(wert: object) -> dt.date:
    # datetime ist eine Unterklasse von date und trüge eine Uhrzeit mit.
    if isinstance(wert, dt.date) and not isinstance(wert, dt.datetime):
        return wert
    if isinstance(wert, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", wert):
        try:
            return dt.date.fromisoformat(wert)
        except ValueError:
            pass
    raise FeldwertValidationError(
        f"erwartet wird ein Datum JJJJ-MM-TT ohne Uhrzeit, bekommen: {wert!r}"
    )


def _text(wert: object) -> str:
    if not isinstance(wert, str) or not wert.strip():
        raise FeldwertValidationError(f"erwartet wird nicht-leerer Text, bekommen: {wert!r}")
    return wert.strip()


def _land(wert: object) -> str:
    if not isinstance(wert, str) or not re.fullmatch(r"[A-Z]{2}", wert):
        raise FeldwertValidationError(
            f"erwartet wird ein Ländercode nach ISO 3166-1 alpha-2 wie 'LU', bekommen: {wert!r}"
        )
    return wert


def _auswahl(auswahl: type[StrEnum]) -> Callable[[object], StrEnum]:
    def pruefe(wert: object) -> StrEnum:
        try:
            return auswahl(wert)
        except ValueError:
            erlaubt = ", ".join(e.value for e in auswahl)
            raise FeldwertValidationError(
                f"{wert!r} ist nicht erlaubt; erlaubt: {erlaubt}"
            ) from None

    return pruefe


def _als_text(wert: object) -> str:
    """Kanonische Textform für die Datenbank. Umkehrung: die Prüffunktion."""
    if isinstance(wert, bool):
        return "true" if wert else "false"
    if isinstance(wert, dt.date):
        return wert.isoformat()
    # Decimal: str() ist exakt und behält die Nachkommastellen wie
    # veröffentlicht ("0.1230" bleibt "0.1230"). StrEnum: der Wert.
    return str(wert)


@dataclass(frozen=True, slots=True)
class Feldtyp:
    """Wie ein Feld geprüft und geführt wird.

    Attribute:
        pruefe: Prüf- und Umwandlungsfunktion.
        einheit: Einheit, in der der Wert gespeichert wird; leer bei Merkmalen.
        je_jahr: Jahreswert mit Kalenderjahr als ``periode``.
    """

    pruefe: Callable[[object], Any]
    einheit: str = ""
    je_jahr: bool = False


# Die Felder, die A5.2 und A5.3 brauchen. Ein neues Feld ist eine Zeile hier.
FELDER: dict[str, Feldtyp] = {
    "ter": Feldtyp(_dezimal, "% p. a."),
    # Wie veröffentlicht, ungerundet. Die Wesentlichkeitsschwelle 0,05 Pp.
    # ist Sache der Bewertung A5.3, nicht der Ablage.
    "tracking_differenz": Feldtyp(_dezimal, "Prozentpunkte p. a.", je_jahr=True),
    "fondsvolumen": Feldtyp(_dezimal, "EUR"),
    "replikationsmethode": Feldtyp(_auswahl(Replikation)),
    "domizil": Feldtyp(_land),
    "auflagedatum": Feldtyp(_datum),
    # Für Filter 2 in der Schreibweise von A5.5, soweit A5.5 den Index nennt.
    "index_name": Feldtyp(_text),
    "ausschuettungsart": Feldtyp(_auswahl(Ausschuettung)),
    "ucits": Feldtyp(_ja_nein),
    "kid_sprache_de": Feldtyp(_ja_nein),
    "xetra_handelbar": Feldtyp(_ja_nein),
    "transaktionskosten_kid": Feldtyp(_dezimal, "Prozentpunkte"),
    "xlm": Feldtyp(_dezimal, "Basispunkte"),
    "aktienfonds_invstg": Feldtyp(_ja_nein),  # § 2 Abs. 6 InvStG
    "waehrungsgesichert": Feldtyp(_ja_nein),
    "haltekosten": Feldtyp(_dezimal, "% p. a."),  # nur Gold-ETC, ersetzt die TD
    # A5.2 Nr. 1 für Gold: ETC deutschen Rechts mit ausschließlichem Liefer-
    # oder Erlösanspruch auf hinterlegtes Gold.
    "gold_etc_lieferanspruch": Feldtyp(_ja_nein),
}


def _feldtyp(feld: str) -> Feldtyp:
    typ = FELDER.get(feld)
    if typ is None:
        raise FeldwertValidationError(
            f"unbekanntes Feld {feld!r}. Bekannt: {', '.join(FELDER)}. "
            "Ein neues Feld ist ein Eintrag in FELDER."
        )
    return typ


_ISIN_MUSTER = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")


def _pruefe_isin(isin: object) -> str:
    """Format und Prüfziffer nach ISO 6166.

    Die Prüfziffer fängt die meisten Tippfehler in einer von Hand gepflegten
    Liste ab — eine vertauschte Ziffer ergäbe sonst still ein anderes oder gar
    kein Instrument.
    """
    if not isinstance(isin, str) or not _ISIN_MUSTER.fullmatch(isin):
        raise FeldwertValidationError(
            f"ISIN {isin!r} hat nicht das Format nach ISO 6166 (2 Buchstaben, 9 Zeichen, 1 Ziffer)"
        )
    # Buchstaben zu Zahlen (A=10 … Z=35), dann Luhn über die Ziffernfolge.
    ziffern = "".join(str(int(zeichen, 36)) for zeichen in isin[:-1])
    summe = 0
    for position, zeichen in enumerate(reversed(ziffern)):
        ziffer = int(zeichen) * (2 if position % 2 == 0 else 1)
        summe += ziffer // 10 + ziffer % 10
    if (10 - summe % 10) % 10 != int(isin[-1]):
        raise FeldwertValidationError(f"ISIN {isin} hat eine falsche Prüfziffer — Tippfehler?")
    return isin


def _zeitpunkt(name: str, wert: dt.datetime) -> dt.datetime:
    """``_require_aware`` aus ``bitemporal``, mit der Fehlerklasse dieser Schicht."""
    try:
        return _require_aware(name, wert)
    except BarValidationError as fehler:
        raise FeldwertValidationError(str(fehler)) from None


@dataclass(frozen=True, slots=True)
class Feldwert:
    """Ein einzelner Stammdatenwert mit seiner vollständigen Herkunft.

    Unveränderlich, wie ``Bar``. Die Prüfung sitzt hier und nicht im Store,
    damit es keinen Weg gibt, einen ungeprüften Wert zu bauen.

    Attribute:
        isin: ISIN des Instruments; die Prüfziffer wird geprüft.
        feld: Name aus ``FELDER``.
        wert: Der Wert wie veröffentlicht; Typ je Feld (``Decimal``, ``bool``,
            ``date``, Text, Auswahl). ``float`` wird abgewiesen.
        quelle_url: Wo der Wert steht.
        quelle_typ: Art des Dokuments.
        status: ``VERIFIZIERT`` nur bei gelesenem Primärdokument.
        stand: Datum des Dokuments.
        abgerufen_am: Ab wann die App den Wert kannte, tz-bewusst.
        periode: Kalenderjahr bei Jahreswerten, sonst leer.
        einheit: Wird aus ``FELDER`` gesetzt. Angegeben nur zur Gegenprobe.
    """

    isin: str
    feld: str
    wert: Any
    quelle_url: str
    quelle_typ: QuelleTyp
    status: Pruefstatus
    stand: dt.date
    abgerufen_am: dt.datetime
    periode: str = ""
    einheit: str | None = None

    def __post_init__(self) -> None:
        _pruefe_isin(self.isin)
        typ = _feldtyp(self.feld)
        try:
            wert = typ.pruefe(self.wert)
        except FeldwertValidationError as fehler:
            raise FeldwertValidationError(f"{self.feld}: {fehler}") from None

        einheit = typ.einheit if self.einheit is None else self.einheit
        if einheit != typ.einheit:
            raise FeldwertValidationError(
                f"{self.feld} wird in {typ.einheit!r} geführt, angegeben war {einheit!r}. "
                "Umrechnen oder FELDER ändern — nie still mischen."
            )

        url = urllib.parse.urlsplit(self.quelle_url) if isinstance(self.quelle_url, str) else None
        if url is None or url.scheme not in ("http", "https") or not url.netloc:
            raise FeldwertValidationError(
                f"quelle_url {self.quelle_url!r} ist keine http(s)-Adresse. "
                "Ohne Quelle ist ein Wert nicht nachprüfbar (A5.1)."
            )

        quelle_typ = _auswahl(QuelleTyp)(self.quelle_typ)
        status = _auswahl(Pruefstatus)(self.status)
        if status is Pruefstatus.VERIFIZIERT and quelle_typ is QuelleTyp.SEKUNDAER:
            raise FeldwertValidationError(
                "Ein Wert aus zweiter Hand kann nicht VERIFIZIERT sein. VERIFIZIERT heißt: "
                "im Primärdokument gelesen (A5.1). Als UNVERIFIZIERT speichern."
            )

        stand = _datum(self.stand)
        abgerufen_am = _zeitpunkt("abgerufen_am", self.abgerufen_am)
        # Wie available_at >= event_time bei Bars (K2). Verglichen in UTC,
        # genau wie der CHECK in der Tabelle.
        if abgerufen_am.date() < stand:
            raise FeldwertValidationError(
                f"abgerufen_am ({abgerufen_am.isoformat()}) liegt vor dem Stand-Datum "
                f"({stand}). Ein Dokument lässt sich nicht abrufen, bevor es existiert "
                "(K2; verglichen in UTC)."
            )

        if typ.je_jahr:
            if not isinstance(self.periode, str) or not re.fullmatch(r"\d{4}", self.periode):
                raise FeldwertValidationError(
                    f"{self.feld} ist ein Jahreswert und braucht das Kalenderjahr als "
                    f"periode, z. B. '2025'; bekommen: {self.periode!r}"
                )
            if stand < dt.date(int(self.periode), 12, 31):
                raise FeldwertValidationError(
                    f"{self.feld} {self.periode} mit Stand {stand}: Ein Jahreswert steht "
                    "frühestens am Jahresende fest."
                )
        elif self.periode != "":
            raise FeldwertValidationError(
                f"{self.feld} hat keine Perioden; periode muss leer sein, war {self.periode!r}"
            )

        object.__setattr__(self, "wert", wert)
        object.__setattr__(self, "einheit", einheit)
        object.__setattr__(self, "quelle_typ", quelle_typ)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "stand", stand)
        object.__setattr__(self, "abgerufen_am", abgerufen_am)


_SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS instrument_felder_row_id START 1;

CREATE TABLE IF NOT EXISTS instrument_felder (
    -- Monotone Schreibreihenfolge, letzter Tiebreaker wie in bars.
    row_id        BIGINT      PRIMARY KEY DEFAULT nextval('instrument_felder_row_id'),
    isin          VARCHAR     NOT NULL,
    feld          VARCHAR     NOT NULL,
    -- Kalenderjahr bei Jahreswerten, sonst ''. Nicht NULL, damit Gleichheit
    -- ohne Sonderfall funktioniert.
    periode       VARCHAR     NOT NULL,
    -- Kanonischer Text; Rückverwandlung je Feldtyp in Python (Modul-Docstring).
    wert          VARCHAR     NOT NULL,
    einheit       VARCHAR     NOT NULL,
    quelle_url    VARCHAR     NOT NULL,
    quelle_typ    VARCHAR     NOT NULL,
    status        VARCHAR     NOT NULL,
    stand         DATE        NOT NULL,
    abgerufen_am  TIMESTAMPTZ NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL,
    -- Wiederholt die Prüfungen aus Feldwert, die ohne FELDER auskommen.
    CHECK (status IN ('VERIFIZIERT', 'UNVERIFIZIERT')),
    CHECK (status = 'UNVERIFIZIERT' OR quelle_typ <> 'sekundaer'),
    -- timezone('UTC', …), sonst hinge das Ergebnis von der Zeitzone des
    -- Rechners ab.
    CHECK (CAST(timezone('UTC', abgerufen_am) AS DATE) >= stand)
);

CREATE INDEX IF NOT EXISTS instrument_felder_pit_idx
    ON instrument_felder (isin, feld, abgerufen_am);
"""

# Was eine Sicht nach außen gibt, in der Reihenfolge der Feldwert-Attribute.
# row_id und ingested_at fehlen bewusst — wie bei PointInTimeView.
_VIEW_SPALTEN = (
    "isin",
    "feld",
    "wert",
    "quelle_url",
    "quelle_typ",
    "status",
    "stand",
    "abgerufen_am",
    "periode",
    "einheit",
)


class InstrumentView:
    """Stammdaten, wie sie zum Zeitpunkt ``as_of`` bekannt waren.

    Das einzige Objekt, das die Produktauswahl zu sehen bekommt. Es liefert
    nur Werte mit ``abgerufen_am <= as_of``; ein Factsheet, das erst nach dem
    Stichtag abgerufen wurde, existiert für diese Sicht nicht. Es gibt keine
    Methode, die „alles“ liefert.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection, as_of: dt.datetime) -> None:
        self._conn = conn
        self._as_of = _zeitpunkt("as_of", as_of)

    @property
    def as_of(self) -> dt.datetime:
        """Der Stichtag dieser Sicht (UTC)."""
        return self._as_of

    def __repr__(self) -> str:
        return f"InstrumentView(as_of={self._as_of.isoformat()})"

    def feld(self, isin: str, feld: str) -> Feldwert | None:
        """Der am Stichtag geltende Wert eines Felds, oder None.

        Kein Wert ist ein gültiges Ergebnis, kein Fehler: Vor dem ersten Abruf
        wusste die App nichts über das Instrument.
        """
        if _feldtyp(feld).je_jahr:
            raise FeldwertValidationError(f"{feld} ist ein Jahreswert — reihe() benutzen")
        werte = self._geltend(isin, feld)
        return werte[0] if werte else None

    def reihe(self, isin: str, feld: str) -> dict[str, Feldwert]:
        """Die am Stichtag geltenden Jahreswerte eines Felds, Jahr aufsteigend."""
        if not _feldtyp(feld).je_jahr:
            raise FeldwertValidationError(f"{feld} ist kein Jahreswert — feld() benutzen")
        return {wert.periode: wert for wert in self._geltend(isin, feld)}

    def isins(self) -> list[str]:
        """Instrumente, zu denen am Stichtag mindestens ein Wert bekannt war."""
        zeilen = self._conn.execute(
            "SELECT DISTINCT isin FROM instrument_felder WHERE abgerufen_am <= ? ORDER BY isin",
            [self._as_of],
        ).fetchall()
        return [zeile[0] for zeile in zeilen]

    def _geltend(self, isin: str, feld: str) -> list[Feldwert]:
        """Je Periode der geltende Wert: jüngster Stand, dann jüngster Abruf."""
        spalten = ", ".join(_VIEW_SPALTEN)
        sql = f"""
            SELECT {spalten}
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY periode
                    ORDER BY stand DESC, abgerufen_am DESC, row_id DESC
                ) AS _rang
                FROM instrument_felder
                WHERE isin = ? AND feld = ? AND abgerufen_am <= ?
            )
            WHERE _rang = 1
            ORDER BY periode
        """
        zeilen = self._conn.execute(sql, [isin, feld, self._as_of]).fetchall()
        # Zurück durch Feldwert: dieselbe Prüfung wie beim Schreiben, auch
        # gegen Zeilen, die jemand an der API vorbei per SQL geschrieben hat.
        return [Feldwert(*zeile) for zeile in zeilen]


_GLEICHE_ZEILE = """
    SELECT 1 FROM instrument_felder
    WHERE isin = ? AND feld = ? AND periode = ? AND wert = ? AND einheit = ?
      AND quelle_url = ? AND quelle_typ = ? AND status = ? AND stand = ?
      AND abgerufen_am = ?
    LIMIT 1
"""

_EINFUEGEN = """
    INSERT INTO instrument_felder (
        isin, feld, periode, wert, einheit, quelle_url, quelle_typ, status,
        stand, abgerufen_am, ingested_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class InstrumentStore:
    """Append-only-Speicher für Instrument-Stammdaten auf DuckDB.

    Kein Update, kein Delete — aus demselben Grund wie bei
    ``BitemporalStore``. Eine korrigierte TER ist eine neue Zeile mit
    späterem ``abgerufen_am``; die alte bleibt für frühere Stichtage sichtbar.

    Beispiel:
        >>> store = InstrumentStore(":memory:")
        >>> store.append(lade_quelldatei("stammdaten.json"))
        >>> sicht = store.view(as_of=datetime(2026, 9, 1, tzinfo=timezone.utc))
        >>> sicht.feld("XX0000000002", "ter")
    """

    def __init__(self, path: str | Path = ":memory:", *, read_only: bool = False) -> None:
        """Öffnet oder erzeugt eine Datenbank.

        Args:
            path: Dateipfad oder ``:memory:``. Dauerhafte Datenbanken gehören
                nach ``~/claude-local/trading-app/``, außerhalb von iCloud
                (ADR-0003).
            read_only: Nur-Lese-Zugriff.
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
        werte: Iterable[Feldwert],
        *,
        ingested_at: dt.datetime | None = None,
    ) -> int:
        """Hängt Werte an. Ändert niemals bestehende Zeilen.

        Eine wortgleiche Wiederholung — dieselbe Quelldatei ein zweites Mal
        geladen — wird übersprungen, damit Nachladen idempotent bleibt. Jede
        Abweichung, auch nur im Abrufdatum, ist eine neue Zeile. Alles oder
        nichts: Scheitert eine Zeile, wird keine geschrieben.

        Args:
            werte: Die anzuhängenden Werte.
            ingested_at: Speicherzeitpunkt, Vorgabe „jetzt“. Nur für Tests.

        Returns:
            Zahl der neu geschriebenen Zeilen.

        Raises:
            FeldwertValidationError: Wenn ein Element kein ``Feldwert`` ist.
        """
        jetzt = (
            dt.datetime.now(dt.timezone.utc)
            if ingested_at is None
            else _zeitpunkt("ingested_at", ingested_at)
        )

        zeilen: list[Sequence[Any]] = []
        for wert in werte:
            if not isinstance(wert, Feldwert):
                raise FeldwertValidationError(
                    f"Erwartet wurde ein Feldwert, bekommen: {type(wert).__name__}. "
                    "Rohe dicts werden nicht angenommen — sie umgehen die Eingangsprüfung."
                )
            zeilen.append(
                (
                    wert.isin,
                    wert.feld,
                    wert.periode,
                    _als_text(wert.wert),
                    wert.einheit,
                    wert.quelle_url,
                    wert.quelle_typ.value,
                    wert.status.value,
                    wert.stand,
                    wert.abgerufen_am,
                )
            )

        geschrieben = 0
        self._conn.begin()
        try:
            for zeile in zeilen:
                if self._conn.execute(_GLEICHE_ZEILE, zeile).fetchone():
                    continue
                self._conn.execute(_EINFUEGEN, [*zeile, jetzt])
                geschrieben += 1
        except BaseException:
            self._conn.rollback()
            raise
        self._conn.commit()
        return geschrieben

    def view(self, as_of: dt.datetime) -> InstrumentView:
        """Erzeugt die Sicht auf den Wissensstand zum Zeitpunkt ``as_of``."""
        return InstrumentView(self._conn, as_of)

    def zeilen_gesamt(self) -> int:
        """Alle je geschriebenen Zeilen. Nur für Betrieb und Diagnose."""
        return int(self._conn.execute("SELECT COUNT(*) FROM instrument_felder").fetchone()[0])

    def historie(self, isin: str, feld: str, periode: str = "") -> pd.DataFrame:
        """Alle Fassungen eines Felds, in Schreibreihenfolge.

        Die Prüfspur: wann hat sich dieser Wert geändert, woher kam jede
        Fassung? Für Betrieb und Fehlersuche, nicht für die Produktauswahl.
        """
        return self._conn.execute(
            """
            SELECT row_id, isin, feld, periode, wert, einheit, quelle_url, quelle_typ,
                   status, stand, abgerufen_am, ingested_at
            FROM instrument_felder
            WHERE isin = ? AND feld = ? AND periode = ?
            ORDER BY row_id
            """,
            [isin, feld, periode],
        ).df()


# ---------------------------------------------------------------------------
# Quelldatei
# ---------------------------------------------------------------------------

_DOKUMENT_SCHLUESSEL = frozenset(
    {"isin", "quelle_typ", "quelle_url", "stand", "abgerufen_am", "status", "werte"}
)


def lade_quelldatei(pfad: str | Path) -> list[Feldwert]:
    """Liest die von Hand gepflegte Quelldatei (Format im Modul-Docstring).

    Nur die lokale Datei, keine Netzverbindung. Zahlen werden als ``Decimal``
    gelesen.

    Raises:
        FeldwertValidationError: mit der Nummer des Dokuments in der Datei,
            damit sich der Fehler finden lässt.
    """
    daten = json.loads(Path(pfad).read_text(encoding="utf-8"), parse_float=Decimal)
    if not isinstance(daten, dict) or set(daten) != {"dokumente"} or not isinstance(
        daten["dokumente"], list
    ):
        raise FeldwertValidationError(
            'Die Quelldatei braucht genau einen Schlüssel "dokumente" mit einer Liste.'
        )

    werte: list[Feldwert] = []
    for nummer, dokument in enumerate(daten["dokumente"], start=1):
        try:
            werte.extend(_werte_aus_dokument(dokument))
        except (ValueError, TypeError) as fehler:  # FeldwertValidationError ist ein ValueError
            raise FeldwertValidationError(f"Dokument {nummer}: {fehler}") from None
    return werte


def _werte_aus_dokument(dokument: object) -> list[Feldwert]:
    if not isinstance(dokument, dict):
        raise FeldwertValidationError("Eintrag ist kein Objekt")
    if set(dokument) != _DOKUMENT_SCHLUESSEL:
        raise FeldwertValidationError(
            f"Schlüssel fehlen: {sorted(_DOKUMENT_SCHLUESSEL - set(dokument))}; "
            f"unbekannt: {sorted(set(dokument) - _DOKUMENT_SCHLUESSEL)}"
        )
    if not isinstance(dokument["werte"], dict):
        raise FeldwertValidationError('"werte" ist kein Objekt')

    herkunft = {
        "isin": dokument["isin"],
        "quelle_typ": dokument["quelle_typ"],
        "quelle_url": dokument["quelle_url"],
        "stand": dokument["stand"],
        "status": dokument["status"],
        "abgerufen_am": dt.datetime.fromisoformat(dokument["abgerufen_am"]),
    }
    werte: list[Feldwert] = []
    for feld, wert in dokument["werte"].items():
        if not _feldtyp(feld).je_jahr:
            werte.append(Feldwert(feld=feld, wert=wert, **herkunft))
            continue
        if not isinstance(wert, dict):
            raise FeldwertValidationError(
                f'{feld} ist ein Jahreswert: erwartet {{"2025": …}}, bekommen {wert!r}'
            )
        werte += [Feldwert(feld=feld, wert=w, periode=p, **herkunft) for p, w in wert.items()]
    return werte
