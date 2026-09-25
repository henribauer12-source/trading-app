"""Tests der Instrument-Stammdaten (Anlage-Spezifikation A5.1).

**Alle ISINs, URLs und Zahlen hier sind Platzhalter.** Die ISINs beginnen mit
``XX`` (kein Ländercode) und bestehen sonst aus Nullen; ihre Prüfziffern sind
von Hand nach ISO 6166 gerechnet. Die URLs enden auf ``.invalid`` (RFC 2606).
Keine Zahl in dieser Datei ist recherchiert.

Der wichtigste Block ist ``TestLeckage``, nach dem Muster von
``tests/test_bitemporal.py``.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trading_app.stammdaten import (
    FELDER,
    Ausschuettung,
    Feldwert,
    FeldwertValidationError,
    InstrumentStore,
    Pruefstatus,
    QuelleTyp,
    Replikation,
    lade_quelldatei,
)

UTC = dt.timezone.utc

# Platzhalter-ISINs, Prüfziffer von Hand gerechnet.
ISIN_A = "XX0000000002"
ISIN_B = "XX0000000010"
URL_KID = "https://emittent.invalid/kid.pdf"
URL_FACTSHEET = "https://emittent.invalid/factsheet.pdf"


def zeit(jahr: int, monat: int, tag: int, stunde: int = 12) -> dt.datetime:
    return dt.datetime(jahr, monat, tag, stunde, tzinfo=UTC)


def mach_wert(
    feld: str = "ter",
    wert: object = Decimal("0.1234"),
    *,
    isin: str = ISIN_A,
    stand: dt.date = dt.date(2026, 2, 15),
    abgerufen_am: dt.datetime | None = None,
    status: Pruefstatus = Pruefstatus.VERIFIZIERT,
    quelle_typ: QuelleTyp = QuelleTyp.KID,
    quelle_url: str = URL_KID,
    periode: str = "",
    einheit: str | None = None,
) -> Feldwert:
    """Baut einen gültigen Feldwert; abgerufen wird vorgabemäßig am Standtag."""
    return Feldwert(
        isin=isin,
        feld=feld,
        wert=wert,
        quelle_url=quelle_url,
        quelle_typ=quelle_typ,
        status=status,
        stand=stand,
        abgerufen_am=abgerufen_am or zeit(stand.year, stand.month, stand.day),
        periode=periode,
        einheit=einheit,
    )


@pytest.fixture
def store():
    with InstrumentStore(":memory:") as s:
        yield s


# ---------------------------------------------------------------------------
# Eingangsprüfung
# ---------------------------------------------------------------------------


class TestFeldwertPruefung:
    def test_gueltiger_wert_wird_angenommen(self) -> None:
        wert = mach_wert("ter", Decimal("0.1234"))
        assert wert.wert == Decimal("0.1234")
        assert isinstance(wert.wert, Decimal)
        assert wert.einheit == "% p. a."  # aus FELDER gesetzt

    def test_float_wird_abgelehnt(self) -> None:
        """CLAUDE.md: Geldbeträge und Kosten in Decimal, nie float."""
        with pytest.raises(FeldwertValidationError, match="float ist verboten"):
            mach_wert("ter", 0.1234)

    def test_bool_ist_keine_zahl(self) -> None:
        """True ist in Python 1 — als TER wäre das ein stiller Tippfehler."""
        with pytest.raises(FeldwertValidationError, match="ter"):
            mach_wert("ter", True)

    def test_komma_wird_abgelehnt(self) -> None:
        with pytest.raises(FeldwertValidationError, match="kein Komma"):
            mach_wert("ter", "0,1234")

    def test_nan_wird_abgelehnt(self) -> None:
        with pytest.raises(FeldwertValidationError, match="endliche"):
            mach_wert("ter", Decimal("NaN"))

    def test_text_und_int_werden_zu_decimal(self) -> None:
        assert mach_wert("ter", "0.1234").wert == Decimal("0.1234")
        assert mach_wert("fondsvolumen", 123_456_789).wert == Decimal(123_456_789)

    def test_unbekanntes_feld_wird_abgelehnt(self) -> None:
        with pytest.raises(FeldwertValidationError, match="unbekanntes Feld"):
            mach_wert("kurs", Decimal("1"))

    def test_isin_mit_falscher_pruefziffer_wird_abgelehnt(self) -> None:
        """Eine vertauschte Ziffer in einer von Hand gepflegten Liste."""
        with pytest.raises(FeldwertValidationError, match="Prüfziffer"):
            mach_wert(isin="XX0000000003")

    @pytest.mark.parametrize("isin", ["XX000000002", "xx0000000002", "XX000000000A", "", None])
    def test_isin_im_falschen_format_wird_abgelehnt(self, isin) -> None:
        with pytest.raises(FeldwertValidationError, match="Format"):
            mach_wert(isin=isin)

    def test_zeitzonenloses_abgerufen_am_wird_abgelehnt(self) -> None:
        with pytest.raises(FeldwertValidationError, match="zeitzonenlos"):
            mach_wert(abgerufen_am=dt.datetime(2026, 3, 1, 10))

    def test_abgerufen_am_wird_auf_utc_normiert(self) -> None:
        berlin = dt.timezone(dt.timedelta(hours=1))
        wert = mach_wert(abgerufen_am=dt.datetime(2026, 3, 1, 10, tzinfo=berlin))
        assert wert.abgerufen_am.utcoffset() == dt.timedelta(0)
        assert wert.abgerufen_am.hour == 9

    def test_abruf_vor_dem_stand_wird_abgelehnt(self) -> None:
        """Wie available_at >= event_time (K2): kein Abruf vor dem Dokument."""
        with pytest.raises(FeldwertValidationError, match="K2"):
            mach_wert(stand=dt.date(2026, 8, 31), abgerufen_am=zeit(2026, 8, 30))

    def test_abruf_am_standtag_ist_erlaubt(self) -> None:
        wert = mach_wert(stand=dt.date(2026, 8, 31), abgerufen_am=zeit(2026, 8, 31, 0))
        assert wert.stand == dt.date(2026, 8, 31)

    def test_zweite_hand_kann_nicht_verifiziert_sein(self) -> None:
        with pytest.raises(FeldwertValidationError, match="zweiter Hand"):
            mach_wert(quelle_typ=QuelleTyp.SEKUNDAER, status=Pruefstatus.VERIFIZIERT)

    def test_zweite_hand_als_unverifiziert_ist_erlaubt(self) -> None:
        """Werte zweiter Hand dürfen gespeichert werden — markiert."""
        wert = mach_wert(quelle_typ=QuelleTyp.SEKUNDAER, status=Pruefstatus.UNVERIFIZIERT)
        assert wert.status is Pruefstatus.UNVERIFIZIERT

    def test_status_und_quelle_als_text(self) -> None:
        """So kommen sie aus der Quelldatei."""
        wert = mach_wert(quelle_typ="factsheet", status="UNVERIFIZIERT")
        assert wert.quelle_typ is QuelleTyp.FACTSHEET
        assert wert.status is Pruefstatus.UNVERIFIZIERT

    @pytest.mark.parametrize("status", ["verifiziert", "GEPRUEFT", ""])
    def test_unbekannter_status_wird_abgelehnt(self, status) -> None:
        with pytest.raises(FeldwertValidationError, match="nicht erlaubt"):
            mach_wert(status=status)

    def test_falsche_einheit_wird_abgelehnt(self) -> None:
        """Eine TER in Basispunkten neben einer in Prozent wäre ein Faktor 100."""
        with pytest.raises(FeldwertValidationError, match="geführt"):
            mach_wert("ter", Decimal("12"), einheit="Basispunkte")

    @pytest.mark.parametrize("url", ["", "kid.pdf", "ftp://emittent.invalid/kid.pdf", None])
    def test_quelle_ist_pflicht(self, url) -> None:
        with pytest.raises(FeldwertValidationError, match="quelle_url"):
            mach_wert(quelle_url=url)

    def test_jahreswert_braucht_ein_jahr(self) -> None:
        with pytest.raises(FeldwertValidationError, match="Kalenderjahr"):
            mach_wert("tracking_differenz", Decimal("-0.0123"))

    def test_jahreswert_steht_erst_am_jahresende_fest(self) -> None:
        """Eine TD für 2026 kann nicht in einem Factsheet vom August 2026 stehen."""
        with pytest.raises(FeldwertValidationError, match="Jahresende"):
            mach_wert(
                "tracking_differenz", Decimal("-0.0123"),
                periode="2026", stand=dt.date(2026, 8, 31),
            )

    def test_jahreswert_am_31_dezember_ist_erlaubt(self) -> None:
        wert = mach_wert(
            "tracking_differenz", Decimal("-0.0123"),
            periode="2025", stand=dt.date(2025, 12, 31),
        )
        assert wert.periode == "2025"

    def test_periode_bei_normalem_feld_ist_verboten(self) -> None:
        with pytest.raises(FeldwertValidationError, match="keine Perioden"):
            mach_wert("ter", Decimal("0.1234"), periode="2025")

    @pytest.mark.parametrize(
        ("feld", "wert"),
        [
            ("ucits", "ja"),
            ("ucits", 1),
            ("domizil", "ie"),
            ("domizil", "IRL"),
            ("replikationsmethode", "synthetisch"),
            ("ausschuettungsart", "monatlich"),
            ("auflagedatum", dt.datetime(2015, 6, 1, tzinfo=UTC)),
            ("auflagedatum", "01.06.2015"),
            ("index_name", "   "),
        ],
    )
    def test_falscher_typ_je_feld_wird_abgelehnt(self, feld, wert) -> None:
        with pytest.raises(FeldwertValidationError, match=feld):
            mach_wert(feld, wert)

    def test_feldwert_ist_unveraenderlich(self) -> None:
        wert = mach_wert()
        with pytest.raises(AttributeError):
            wert.wert = Decimal("9")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Decimal und Typen über die Datenbank
# ---------------------------------------------------------------------------


class TestDatenbankRunde:
    def test_decimal_kommt_exakt_zurueck(self, store) -> None:
        """Mehr Stellen, als float halten kann: ein float-Umweg fiele hier auf."""
        genau = Decimal("0.1234567890123456789")
        store.append([mach_wert("ter", genau)])
        zurueck = store.view(zeit(2026, 9, 1)).feld(ISIN_A, "ter").wert
        assert isinstance(zurueck, Decimal)
        assert zurueck == genau
        assert str(zurueck) == "0.1234567890123456789"

    def test_nachkommanullen_bleiben_wie_veroeffentlicht(self, store) -> None:
        store.append([mach_wert("ter", Decimal("0.1230"))])
        assert str(store.view(zeit(2026, 9, 1)).feld(ISIN_A, "ter").wert) == "0.1230"

    def test_td_wird_nicht_gerundet(self, store) -> None:
        """Die Wesentlichkeitsschwelle 0,05 Pp. ist Sache der Bewertung, nicht der Ablage."""
        store.append([
            mach_wert("tracking_differenz", Decimal("-0.0123"),
                      periode="2025", stand=dt.date(2026, 1, 31)),
        ])
        td = store.view(zeit(2026, 9, 1)).reihe(ISIN_A, "tracking_differenz")["2025"]
        assert td.wert == Decimal("-0.0123")

    @pytest.mark.parametrize(
        ("feld", "wert"),
        [
            ("fondsvolumen", Decimal("123456789012.34")),
            ("xlm", Decimal("7.5")),
            ("transaktionskosten_kid", Decimal("-0.0100")),  # Vorzeichen bleibt erhalten
            ("ucits", True),
            ("xetra_handelbar", False),
            ("auflagedatum", dt.date(2015, 6, 1)),
            ("domizil", "XX"),
            ("index_name", "Platzhalter-Index"),
            ("replikationsmethode", Replikation.SYNTHETISCH_MEHRERE_GEGENPARTEIEN),
            ("ausschuettungsart", Ausschuettung.THESAURIEREND),
        ],
    )
    def test_jeder_typ_ueberlebt_die_datenbank(self, store, feld, wert) -> None:
        store.append([mach_wert(feld, wert)])
        zurueck = store.view(zeit(2026, 9, 1)).feld(ISIN_A, feld).wert
        assert zurueck == wert
        assert type(zurueck) is type(wert)

    def test_jedes_feld_in_felder_hat_einen_typ(self) -> None:
        """Die Pflichtfelder aus A5.2/A5.3 sind alle registriert."""
        pflicht = {
            "ter", "tracking_differenz", "fondsvolumen", "replikationsmethode", "domizil",
            "auflagedatum", "index_name", "ausschuettungsart", "ucits", "kid_sprache_de",
            "xetra_handelbar", "transaktionskosten_kid", "xlm", "aktienfonds_invstg",
            "waehrungsgesichert", "haltekosten",
        }
        assert pflicht <= set(FELDER)
        assert [f for f, typ in FELDER.items() if typ.je_jahr] == ["tracking_differenz"]


# ---------------------------------------------------------------------------
# Point-in-time
# ---------------------------------------------------------------------------


class TestPointInTime:
    def test_leere_sicht_ist_kein_fehler(self, store) -> None:
        sicht = store.view(zeit(2026, 9, 1))
        assert sicht.feld(ISIN_A, "ter") is None
        assert sicht.reihe(ISIN_A, "tracking_differenz") == {}
        assert sicht.isins() == []

    def test_factsheet_vom_august_fehlt_per_juni(self, store) -> None:
        """Das Beispiel aus dem Auftrag: Stand 31.08., Sicht per 30.06."""
        store.append([
            mach_wert("fondsvolumen", Decimal("123456789"), quelle_typ=QuelleTyp.FACTSHEET,
                      quelle_url=URL_FACTSHEET, stand=dt.date(2026, 8, 31),
                      abgerufen_am=zeit(2026, 9, 3)),
        ])
        assert store.view(zeit(2026, 6, 30)).feld(ISIN_A, "fondsvolumen") is None
        assert store.view(zeit(2026, 9, 4)).feld(ISIN_A, "fondsvolumen") is not None

    def test_zaehlt_ab_abruf_nicht_ab_stand(self, store) -> None:
        """Zwischen Stand und Abruf wusste die App den Wert noch nicht."""
        store.append([mach_wert(stand=dt.date(2026, 2, 15), abgerufen_am=zeit(2026, 3, 1))])
        assert store.view(zeit(2026, 2, 20)).feld(ISIN_A, "ter") is None
        assert store.view(zeit(2026, 3, 2)).feld(ISIN_A, "ter") is not None

    def test_stichtag_ist_einschliesslich(self, store) -> None:
        store.append([mach_wert(abgerufen_am=zeit(2026, 3, 1))])
        assert store.view(zeit(2026, 3, 1)).feld(ISIN_A, "ter") is not None

    def test_eine_sekunde_vorher_noch_unsichtbar(self, store) -> None:
        store.append([mach_wert(abgerufen_am=zeit(2026, 3, 1))])
        knapp_davor = zeit(2026, 3, 1) - dt.timedelta(seconds=1)
        assert store.view(knapp_davor).feld(ISIN_A, "ter") is None

    def test_korrektur_gilt_erst_ab_ihrem_abruf(self, store) -> None:
        """Eine korrigierte TER ist eine neue Zeile mit späterem abgerufen_am."""
        store.append([mach_wert(wert=Decimal("0.1234"), abgerufen_am=zeit(2026, 3, 1))])
        store.append([mach_wert(wert=Decimal("0.4321"), abgerufen_am=zeit(2026, 6, 1))])

        assert store.view(zeit(2026, 4, 1)).feld(ISIN_A, "ter").wert == Decimal("0.1234")
        assert store.view(zeit(2026, 7, 1)).feld(ISIN_A, "ter").wert == Decimal("0.4321")

    def test_juengerer_stand_schlaegt_spaeter_erfasstes_altes_dokument(self, store) -> None:
        """Wer das KID des Vorjahres nachträgt, verdrängt das aktuelle nicht."""
        store.append([mach_wert(wert=Decimal("0.1111"), stand=dt.date(2026, 2, 15),
                                abgerufen_am=zeit(2026, 3, 1))])
        store.append([mach_wert(wert=Decimal("0.2222"), stand=dt.date(2025, 2, 10),
                                abgerufen_am=zeit(2026, 9, 1))])

        assert store.view(zeit(2026, 9, 10)).feld(ISIN_A, "ter").wert == Decimal("0.1111")

    def test_jedes_feld_hat_seine_eigene_herkunft(self, store) -> None:
        """Der Kern von A5.1: TER aus dem KID, Volumen aus dem Factsheet."""
        store.append([
            mach_wert("ter", Decimal("0.1234"), stand=dt.date(2026, 2, 15),
                      abgerufen_am=zeit(2026, 3, 1)),
            mach_wert("fondsvolumen", Decimal("123456789"), quelle_typ=QuelleTyp.FACTSHEET,
                      quelle_url=URL_FACTSHEET, stand=dt.date(2026, 8, 31),
                      abgerufen_am=zeit(2026, 9, 3)),
        ])
        sicht = store.view(zeit(2026, 9, 10))
        ter = sicht.feld(ISIN_A, "ter")
        volumen = sicht.feld(ISIN_A, "fondsvolumen")

        assert (ter.quelle_url, ter.quelle_typ, ter.stand) == (
            URL_KID, QuelleTyp.KID, dt.date(2026, 2, 15)
        )
        assert (volumen.quelle_url, volumen.quelle_typ, volumen.stand) == (
            URL_FACTSHEET, QuelleTyp.FACTSHEET, dt.date(2026, 8, 31)
        )
        assert ter.abgerufen_am == zeit(2026, 3, 1)
        assert volumen.abgerufen_am == zeit(2026, 9, 3)

    def test_reihe_liefert_alle_jahre(self, store) -> None:
        store.append([
            mach_wert("tracking_differenz", Decimal(wert), periode=jahr,
                      stand=dt.date(2026, 1, 31), abgerufen_am=zeit(2026, 2, 5))
            for jahr, wert in (("2025", "0.0300"), ("2023", "-0.0100"), ("2024", "0.0200"))
        ])
        reihe = store.view(zeit(2026, 9, 1)).reihe(ISIN_A, "tracking_differenz")
        assert list(reihe) == ["2023", "2024", "2025"]
        assert [w.wert for w in reihe.values()] == [
            Decimal("-0.0100"), Decimal("0.0200"), Decimal("0.0300")
        ]

    def test_feld_und_reihe_verwechseln_geht_nicht(self, store) -> None:
        sicht = store.view(zeit(2026, 9, 1))
        with pytest.raises(FeldwertValidationError, match="reihe"):
            sicht.feld(ISIN_A, "tracking_differenz")
        with pytest.raises(FeldwertValidationError, match="feld"):
            sicht.reihe(ISIN_A, "ter")

    def test_instrumente_trennen_sauber(self, store) -> None:
        store.append([
            mach_wert(isin=ISIN_A, wert=Decimal("0.1111")),
            mach_wert(isin=ISIN_B, wert=Decimal("0.2222")),
        ])
        sicht = store.view(zeit(2026, 9, 1))
        assert sicht.feld(ISIN_A, "ter").wert == Decimal("0.1111")
        assert sicht.feld(ISIN_B, "ter").wert == Decimal("0.2222")
        assert sicht.isins() == [ISIN_A, ISIN_B]

    def test_isins_respektieren_den_stichtag(self, store) -> None:
        """Auch hier einschließlich: abgerufen genau zum Stichtag ist bekannt."""
        store.append([mach_wert(isin=ISIN_B, abgerufen_am=zeit(2026, 5, 1))])
        assert store.view(zeit(2026, 4, 1)).isins() == []
        assert store.view(zeit(2026, 5, 1) - dt.timedelta(seconds=1)).isins() == []
        assert store.view(zeit(2026, 5, 1)).isins() == [ISIN_B]

    def test_sicht_braucht_tz_bewussten_stichtag(self, store) -> None:
        with pytest.raises(FeldwertValidationError, match="zeitzonenlos"):
            store.view(dt.datetime(2026, 9, 1))


# ---------------------------------------------------------------------------
# Append-only
# ---------------------------------------------------------------------------


class TestAppendOnly:
    def test_kein_update_und_kein_delete(self, store) -> None:
        for verboten in ("update", "delete", "upsert", "remove", "truncate"):
            assert not hasattr(store, verboten), f"{verboten}() darf es nicht geben"

    def test_korrektur_loescht_das_original_nicht(self, store) -> None:
        store.append([mach_wert(wert=Decimal("0.1234"), abgerufen_am=zeit(2026, 3, 1))])
        store.append([mach_wert(wert=Decimal("0.4321"), abgerufen_am=zeit(2026, 6, 1))])

        assert store.zeilen_gesamt() == 2
        historie = store.historie(ISIN_A, "ter")
        assert list(historie["wert"]) == ["0.1234", "0.4321"]
        assert "ingested_at" in historie.columns  # die Prüfspur zeigt alles

    def test_erneutes_laden_ist_idempotent(self, store) -> None:
        """Dieselbe Quelldatei zweimal geladen: keine Doppelungen."""
        werte = [mach_wert(), mach_wert("fondsvolumen", Decimal("123456789"))]
        assert store.append(werte) == 2
        assert store.append(werte) == 0
        assert store.zeilen_gesamt() == 2

    def test_rohe_dicts_werden_abgelehnt(self, store) -> None:
        with pytest.raises(FeldwertValidationError, match="Erwartet wurde ein Feldwert"):
            store.append([{"isin": ISIN_A, "feld": "ter", "wert": "0.1"}])  # type: ignore[list-item]

    def test_fehler_im_stapel_schreibt_nichts(self, store) -> None:
        with pytest.raises(FeldwertValidationError):
            store.append([mach_wert(), "kaputt"])  # type: ignore[list-item]
        assert store.zeilen_gesamt() == 0

    def test_leeres_anhaengen_ist_erlaubt(self, store) -> None:
        assert store.append([]) == 0

    def test_tabelle_prueft_selbst(self, store) -> None:
        """Wer an der API vorbei per SQL schreibt, scheitert an den CHECKs."""
        import duckdb

        with pytest.raises(duckdb.ConstraintException):
            store._conn.execute(
                """
                INSERT INTO instrument_felder (isin, feld, periode, wert, einheit, quelle_url,
                    quelle_typ, status, stand, abgerufen_am, ingested_at)
                VALUES ('XX0000000002', 'ter', '', '0.1', '% p. a.', 'https://x.invalid/a.pdf',
                        'sekundaer', 'VERIFIZIERT', DATE '2026-02-15',
                        TIMESTAMPTZ '2026-03-01 00:00:00+00', now())
                """
            )

    @pytest.mark.parametrize(
        ("abgerufen_am", "erlaubt"),
        [
            ("2026-08-30 23:59:59+00", False),
            # 31.08. 01:00 in Berlin ist 30.08. 23:00 UTC: verglichen wird in UTC,
            # unabhängig von der Zone des Rechners.
            ("2026-08-31 01:00:00+02", False),
            ("2026-08-31 00:00:00+00", True),
        ],
    )
    def test_tabelle_prueft_abruf_nach_stand(self, store, abgerufen_am, erlaubt) -> None:
        """K2 auch gegen Roh-SQL: kein Abruf vor dem Stand-Datum."""
        import duckdb

        sql = f"""
            INSERT INTO instrument_felder (isin, feld, periode, wert, einheit, quelle_url,
                quelle_typ, status, stand, abgerufen_am, ingested_at)
            VALUES ('XX0000000002', 'ter', '', '0.1', '% p. a.', 'https://x.invalid/a.pdf',
                    'kid', 'VERIFIZIERT', DATE '2026-08-31',
                    TIMESTAMPTZ '{abgerufen_am}', now())
        """
        if erlaubt:
            store._conn.execute(sql)
            assert store.zeilen_gesamt() == 1
        else:
            with pytest.raises(duckdb.ConstraintException):
                store._conn.execute(sql)


# ---------------------------------------------------------------------------
# Dauerhafte Datenbank
# ---------------------------------------------------------------------------


class TestPersistenz:
    def test_werte_ueberleben_das_schliessen(self, tmp_path) -> None:
        pfad = tmp_path / "stammdaten.duckdb"
        with InstrumentStore(pfad) as s:
            s.append([mach_wert("ter", Decimal("0.1234"))])
        with InstrumentStore(pfad) as s:
            wert = s.view(zeit(2026, 9, 1)).feld(ISIN_A, "ter")
            assert wert.wert == Decimal("0.1234")
            assert wert.abgerufen_am.utcoffset() == dt.timedelta(0)


# ---------------------------------------------------------------------------
# Leckage-Tests (Qualitätsstandards 3.3)
# ---------------------------------------------------------------------------


def _alles(sicht, isins=(ISIN_A, ISIN_B)) -> dict:
    """Jeder Wert, den eine Sicht zu den Test-ISINs liefert."""
    ergebnis = {}
    for isin in isins:
        for feld, typ in FELDER.items():
            ergebnis[isin, feld] = sicht.reihe(isin, feld) if typ.je_jahr else sicht.feld(isin, feld)
    return ergebnis


class TestLeckage:
    def test_abschneide_test(self, store) -> None:
        """Test 1: Die Sicht bei t bleibt gleich, egal was danach abgerufen wird."""
        store.append([
            mach_wert("ter", Decimal("0.1234"), abgerufen_am=zeit(2026, 3, 1)),
            mach_wert("tracking_differenz", Decimal("-0.0100"), periode="2025",
                      stand=dt.date(2026, 1, 31), abgerufen_am=zeit(2026, 2, 5)),
            mach_wert("fondsvolumen", Decimal("123456789"), quelle_typ=QuelleTyp.FACTSHEET,
                      quelle_url=URL_FACTSHEET, stand=dt.date(2026, 5, 31),
                      abgerufen_am=zeit(2026, 6, 3)),
        ])
        stichtag = zeit(2026, 6, 30)
        vorher = _alles(store.view(stichtag))
        isins_vorher = store.view(stichtag).isins()

        # Später abgerufen: Korrektur eines sichtbaren Werts, neues Factsheet,
        # neues Jahr, neues Instrument.
        store.append([
            mach_wert("ter", Decimal("0.9999"), abgerufen_am=zeit(2026, 7, 1)),
            mach_wert("fondsvolumen", Decimal("987654321"), quelle_typ=QuelleTyp.FACTSHEET,
                      quelle_url=URL_FACTSHEET, stand=dt.date(2026, 8, 31),
                      abgerufen_am=zeit(2026, 9, 3)),
            mach_wert("tracking_differenz", Decimal("0.0500"), periode="2025",
                      stand=dt.date(2026, 8, 31), abgerufen_am=zeit(2026, 9, 3)),
            mach_wert("tracking_differenz", Decimal("0.0700"), periode="2026",
                      stand=dt.date(2026, 12, 31), abgerufen_am=zeit(2027, 1, 20)),
            mach_wert(isin=ISIN_B, abgerufen_am=zeit(2026, 7, 2)),
        ])

        assert _alles(store.view(stichtag)) == vorher
        assert store.view(stichtag).isins() == isins_vorher

    def test_zukunfts_stoertest(self, store) -> None:
        """Test 2: Absurde Werte nach t dürfen die Sicht bis t nicht rühren."""
        store.append([
            mach_wert("ter", Decimal("0.1234"), abgerufen_am=zeit(2026, 3, 1)),
            mach_wert("fondsvolumen", Decimal("123456789"), abgerufen_am=zeit(2026, 3, 1)),
        ])
        stichtag = zeit(2026, 6, 30)
        vorher = _alles(store.view(stichtag))

        for tag in range(1, 20):
            store.append([
                mach_wert("ter", Decimal(1000 + tag), abgerufen_am=zeit(2026, 7, tag)),
                mach_wert("fondsvolumen", Decimal(-tag), abgerufen_am=zeit(2026, 7, tag)),
            ])

        assert _alles(store.view(stichtag)) == vorher

    def test_kein_zugang_zur_rohen_tabelle(self, store) -> None:
        sicht = store.view(zeit(2026, 9, 1))
        oeffentlich = {n for n in dir(sicht) if not n.startswith("_")}
        assert oeffentlich == {"as_of", "feld", "reihe", "isins"}

    @settings(max_examples=60, deadline=None)
    @given(
        zeilen=st.lists(
            st.tuples(
                st.sampled_from([ISIN_A, ISIN_B]),
                st.sampled_from(["ter", "fondsvolumen", "tracking_differenz"]),
                st.integers(min_value=0, max_value=500),  # Stand: Tage nach 01.01.2024
                st.integers(min_value=0, max_value=90),  # Abruf: Tage nach dem Stand
                st.integers(min_value=-9999, max_value=9999),  # Wert in Zehntausendsteln
            ),
            min_size=1,
            max_size=25,
        ),
        stichtag_tag=st.integers(min_value=0, max_value=620),
    )
    def test_abschneiden_aendert_nichts(self, zeilen, stichtag_tag) -> None:
        """Abschneide-Test als Eigenschaft: Sicht auf alles == Sicht auf das Bekannte.

        Speicher A hat jede Zeile, Speicher B nur die bis zum Stichtag
        abgerufenen. Hypothesis sucht die Datenlage, in der sich beide Sichten
        unterscheiden — dann hätte die Zukunft die Vergangenheit verändert.
        """
        basis = dt.date(2024, 1, 1)
        stichtag = zeit(2024, 1, 1) + dt.timedelta(days=stichtag_tag)
        werte = []
        for isin, feld, stand_tag, verzug, zehntausendstel in zeilen:
            stand = basis + dt.timedelta(days=stand_tag)
            werte.append(
                mach_wert(
                    feld,
                    Decimal(zehntausendstel).scaleb(-4),
                    isin=isin,
                    stand=stand,
                    abgerufen_am=zeit(stand.year, stand.month, stand.day)
                    + dt.timedelta(days=verzug),
                    periode=str(stand.year - 1) if feld == "tracking_differenz" else "",
                )
            )

        with InstrumentStore(":memory:") as voll, InstrumentStore(":memory:") as bekannt:
            voll.append(werte)
            bekannt.append([w for w in werte if w.abgerufen_am <= stichtag])

            sicht = voll.view(stichtag)
            assert _alles(sicht) == _alles(bekannt.view(stichtag))
            assert sicht.isins() == bekannt.view(stichtag).isins()
            for wert in _alles(sicht).values():
                for einzel in wert.values() if isinstance(wert, dict) else [wert]:
                    if einzel is not None:
                        assert einzel.abgerufen_am <= stichtag


# ---------------------------------------------------------------------------
# Quelldatei
# ---------------------------------------------------------------------------


def _schreibe(tmp_path, dokumente) -> str:
    pfad = tmp_path / "stammdaten.json"
    pfad.write_text(json.dumps({"dokumente": dokumente}), encoding="utf-8")
    return pfad


KID_DOKUMENT = {
    "isin": ISIN_A,
    "quelle_typ": "kid",
    "quelle_url": URL_KID,
    "stand": "2026-02-15",
    "abgerufen_am": "2026-03-01T10:00:00+01:00",
    "status": "VERIFIZIERT",
    "werte": {"ter": 0.1234, "ucits": True, "domizil": "XX"},
}

FACTSHEET_DOKUMENT = {
    "isin": ISIN_A,
    "quelle_typ": "factsheet",
    "quelle_url": URL_FACTSHEET,
    "stand": "2026-08-31",
    "abgerufen_am": "2026-09-03T08:00:00+00:00",
    "status": "UNVERIFIZIERT",
    "werte": {
        "fondsvolumen": 123456789.01,
        "tracking_differenz": {"2024": -0.0123, "2025": 0.0456},
    },
}


class TestQuelldatei:
    def test_jedes_dokument_vererbt_seine_herkunft(self, tmp_path) -> None:
        werte = lade_quelldatei(_schreibe(tmp_path, [KID_DOKUMENT, FACTSHEET_DOKUMENT]))
        nach_feld = {(w.feld, w.periode): w for w in werte}

        assert len(werte) == 6  # 3 aus dem KID, 1 Volumen + 2 Jahreswerte aus dem Factsheet
        assert nach_feld["ter", ""].quelle_url == URL_KID
        assert nach_feld["ter", ""].stand == dt.date(2026, 2, 15)
        assert nach_feld["ter", ""].abgerufen_am == zeit(2026, 3, 1, 9)
        assert nach_feld["fondsvolumen", ""].quelle_typ is QuelleTyp.FACTSHEET
        assert nach_feld["fondsvolumen", ""].status is Pruefstatus.UNVERIFIZIERT
        assert nach_feld["tracking_differenz", "2024"].stand == dt.date(2026, 8, 31)

    def test_zahlen_werden_nie_float(self, tmp_path) -> None:
        """JSON kennt nur float — der Loader liest trotzdem Decimal."""
        werte = lade_quelldatei(_schreibe(tmp_path, [KID_DOKUMENT, FACTSHEET_DOKUMENT]))
        nach_feld = {(w.feld, w.periode): w.wert for w in werte}
        assert nach_feld["ter", ""] == Decimal("0.1234")
        assert nach_feld["fondsvolumen", ""] == Decimal("123456789.01")
        assert nach_feld["tracking_differenz", "2024"] == Decimal("-0.0123")

    def test_datei_landet_im_store(self, tmp_path, store) -> None:
        store.append(lade_quelldatei(_schreibe(tmp_path, [KID_DOKUMENT, FACTSHEET_DOKUMENT])))
        sicht = store.view(zeit(2026, 9, 10))
        assert sicht.feld(ISIN_A, "ucits").wert is True
        assert list(sicht.reihe(ISIN_A, "tracking_differenz")) == ["2024", "2025"]

    def test_zeitzonenloser_abruf_nennt_das_dokument(self, tmp_path) -> None:
        kaputt = {**FACTSHEET_DOKUMENT, "abgerufen_am": "2026-09-03T08:00:00"}
        with pytest.raises(FeldwertValidationError, match="Dokument 2.*zeitzonenlos"):
            lade_quelldatei(_schreibe(tmp_path, [KID_DOKUMENT, kaputt]))

    def test_vertippter_schluessel_wird_gemeldet(self, tmp_path) -> None:
        kaputt = {k: v for k, v in KID_DOKUMENT.items() if k != "quelle_url"}
        kaputt["quelle_ulr"] = URL_KID
        with pytest.raises(FeldwertValidationError, match="quelle_ulr"):
            lade_quelldatei(_schreibe(tmp_path, [kaputt]))

    def test_unbekanntes_feld_wird_gemeldet(self, tmp_path) -> None:
        kaputt = {**KID_DOKUMENT, "werte": {"terr": 0.1}}
        with pytest.raises(FeldwertValidationError, match="Dokument 1.*terr"):
            lade_quelldatei(_schreibe(tmp_path, [kaputt]))

    def test_jahreswert_ohne_jahr_wird_gemeldet(self, tmp_path) -> None:
        kaputt = {**FACTSHEET_DOKUMENT, "werte": {"tracking_differenz": 0.01}}
        with pytest.raises(FeldwertValidationError, match="Jahreswert"):
            lade_quelldatei(_schreibe(tmp_path, [kaputt]))

    def test_falsche_grundform_wird_gemeldet(self, tmp_path) -> None:
        pfad = tmp_path / "falsch.json"
        pfad.write_text(json.dumps([KID_DOKUMENT]), encoding="utf-8")
        with pytest.raises(FeldwertValidationError, match="dokumente"):
            lade_quelldatei(pfad)
