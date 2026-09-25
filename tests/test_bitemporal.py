"""Tests der bitemporalen Datenschicht.

Der wichtigste Block ist ``TestLeckage``: die Abschneide- und Störtests aus
Abschnitt 3.3 der Qualitätsstandards. Sie prüfen die eine Eigenschaft, an der
die ganze Schicht hängt — dass eine Sicht mit Stichtag t sich nicht dadurch
ändert, dass später Daten dazukommen.
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


def zeit(jahr: int, monat: int, tag: int, stunde: int = 22) -> dt.datetime:
    """Tz-bewusster Zeitstempel. 22:00 UTC ≈ US-Handelsschluss."""
    return dt.datetime(jahr, monat, tag, stunde, tzinfo=UTC)


def mach_bar(
    tag: int,
    close: float = 100.0,
    *,
    symbol: str = "AAPL.US",
    event_time: dt.datetime | None = None,
    available_at: dt.datetime | None = None,
    adjusted_close: float | None = None,
    source: str = "test",
) -> Bar:
    """Baut eine gültige Bar mit möglichst wenig Zeremonie."""
    ereignis = event_time or zeit(2026, 1, tag)
    return Bar(
        symbol=symbol,
        bar_size="1d",
        event_time=ereignis,
        available_at=available_at or ereignis,
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
    """Frischer In-Memory-Speicher pro Test."""
    with BitemporalStore(":memory:") as s:
        yield s


# ---------------------------------------------------------------------------
# Eingangsprüfung
# ---------------------------------------------------------------------------


class TestBarPruefung:
    def test_gueltige_bar_wird_angenommen(self) -> None:
        bar = mach_bar(5, close=100.0)
        assert bar.close == 100.0
        assert bar.event_time.tzinfo is not None

    def test_zeitzonenloses_event_time_wird_abgelehnt(self) -> None:
        """Der stillste Fehler der Schicht: naive Zeitstempel."""
        with pytest.raises(BarValidationError, match="zeitzonenlos"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=dt.datetime(2026, 1, 5, 22),  # ohne tzinfo
                available_at=zeit(2026, 1, 5),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_zeitzonenloses_available_at_wird_abgelehnt(self) -> None:
        with pytest.raises(BarValidationError, match="zeitzonenlos"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=zeit(2026, 1, 5),
                available_at=dt.datetime(2026, 1, 5, 22),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_zeitstempel_werden_auf_utc_normiert(self) -> None:
        """Eingabe in anderer Zone ist erlaubt, gespeichert wird UTC."""
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
        assert bar.event_time.hour == 15  # 17:30 MESZ = 15:30 UTC

    def test_available_at_vor_event_time_wird_abgelehnt(self) -> None:
        """Konvention K2: eine Bar ist nicht bekannt, bevor sie zu Ende ist."""
        with pytest.raises(BarValidationError, match="K2"):
            Bar(
                symbol="AAPL.US",
                bar_size="1d",
                event_time=zeit(2026, 1, 5),
                available_at=zeit(2026, 1, 4),  # einen Tag zu früh
                open=99, high=102, low=98, close=100,
                volume=1_000, source="test",
            )

    def test_available_at_gleich_event_time_ist_erlaubt(self) -> None:
        bar = mach_bar(5)
        assert bar.available_at == bar.event_time

    @pytest.mark.parametrize(
        ("feld", "wert", "meldung"),
        [
            ("high", 97.0, "high"),        # high < low
            ("open", 200.0, "open"),       # open außerhalb der Spanne
            ("close", 200.0, "close"),     # close außerhalb der Spanne
            ("volume", -5.0, "negativ"),
            ("close", -100.0, "positiv"),
        ],
    )
    def test_unplausible_werte_werden_abgelehnt(self, feld, wert, meldung) -> None:
        felder = dict(
            symbol="AAPL.US", bar_size="1d",
            event_time=zeit(2026, 1, 5), available_at=zeit(2026, 1, 5),
            open=99.0, high=102.0, low=98.0, close=100.0,
            volume=1_000.0, source="test",
        )
        felder[feld] = wert
        with pytest.raises(BarValidationError, match=meldung):
            Bar(**felder)

    def test_nan_preis_wird_abgelehnt(self) -> None:
        with pytest.raises(BarValidationError, match="NaN"):
            Bar(
                symbol="AAPL.US", bar_size="1d",
                event_time=zeit(2026, 1, 5), available_at=zeit(2026, 1, 5),
                open=99, high=102, low=98, close=float("nan"),
                volume=1_000, source="test",
            )

    def test_fehlende_quelle_wird_abgelehnt(self) -> None:
        """Ohne Herkunft ist bei widersprüchlichen Daten nicht zu klären, wem zu glauben ist."""
        with pytest.raises(BarValidationError, match="source"):
            Bar(
                symbol="AAPL.US", bar_size="1d",
                event_time=zeit(2026, 1, 5), available_at=zeit(2026, 1, 5),
                open=99, high=102, low=98, close=100,
                volume=1_000, source="",
            )

    def test_bar_ist_unveraenderlich(self) -> None:
        bar = mach_bar(5)
        with pytest.raises(AttributeError):
            bar.close = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Point-in-time-Sperre
# ---------------------------------------------------------------------------


class TestPointInTime:
    def test_leere_sicht_ist_kein_fehler(self, store) -> None:
        """Vor dem Börsengang gab es keine Kurse. Das ist ein Ergebnis."""
        frame = store.view(zeit(2026, 1, 10)).bars("AAPL.US")
        assert isinstance(frame, pd.DataFrame)
        assert frame.empty

    def test_zukunft_bleibt_unsichtbar(self, store) -> None:
        """Der Kern: was nach dem Stichtag bekannt wurde, darf nicht erscheinen."""
        store.append([mach_bar(tag, close=100 + tag) for tag in (5, 6, 7, 8)])

        sicht = store.view(zeit(2026, 1, 6, 23))
        frame = sicht.bars("AAPL.US")

        assert len(frame) == 2
        assert list(frame["close"]) == [105.0, 106.0]

    def test_verzoegerte_veroeffentlichung(self, store) -> None:
        """event_time und available_at fallen auseinander — der Grund für Bitemporalität."""
        store.append([
            mach_bar(5, close=105, available_at=zeit(2026, 1, 8)),  # 3 Tage Verzug
        ])

        assert store.view(zeit(2026, 1, 7)).bars("AAPL.US").empty
        assert len(store.view(zeit(2026, 1, 9)).bars("AAPL.US")) == 1

    def test_korrektur_gilt_erst_ab_ihrer_veroeffentlichung(self, store) -> None:
        """Eine Korrektur darf die Vergangenheit nicht rückwirkend verändern."""
        store.append([mach_bar(5, close=100.0, available_at=zeit(2026, 1, 5))])
        store.append([mach_bar(5, close=101.5, available_at=zeit(2026, 1, 9))])

        vorher = store.view(zeit(2026, 1, 7)).bars("AAPL.US")
        nachher = store.view(zeit(2026, 1, 10)).bars("AAPL.US")

        assert len(vorher) == 1 and vorher.iloc[0]["close"] == 100.0
        assert len(nachher) == 1 and nachher.iloc[0]["close"] == 101.5

    def test_stichtag_ist_einschliesslich(self, store) -> None:
        """available_at == as_of: die Bar ist bekannt."""
        store.append([mach_bar(5, available_at=zeit(2026, 1, 5))])
        assert len(store.view(zeit(2026, 1, 5)).bars("AAPL.US")) == 1

    def test_eine_sekunde_vorher_noch_unsichtbar(self, store) -> None:
        store.append([mach_bar(5, available_at=zeit(2026, 1, 5))])
        knapp_davor = zeit(2026, 1, 5) - dt.timedelta(seconds=1)
        assert store.view(knapp_davor).bars("AAPL.US").empty

    def test_zeitfenster(self, store) -> None:
        store.append([mach_bar(tag, close=100 + tag) for tag in range(5, 15)])
        frame = store.view(zeit(2026, 2, 1)).bars(
            "AAPL.US", start=zeit(2026, 1, 7), end=zeit(2026, 1, 9)
        )
        assert list(frame["close"]) == [107.0, 108.0, 109.0]

    def test_symbole_trennen_sauber(self, store) -> None:
        store.append([
            mach_bar(5, symbol="AAPL.US", close=100),
            mach_bar(5, symbol="MSFT.US", close=400),
        ])
        sicht = store.view(zeit(2026, 1, 10))
        assert sicht.bars("AAPL.US").iloc[0]["close"] == 100.0
        assert sicht.bars("MSFT.US").iloc[0]["close"] == 400.0
        assert sicht.symbole() == ["AAPL.US", "MSFT.US"]

    def test_bar_size_trennt_sauber(self, store) -> None:
        """Tages- und Stundenbars dürfen sich nie vermischen."""
        ereignis = zeit(2026, 1, 5)
        gemeinsam = dict(
            symbol="AAPL.US", event_time=ereignis, available_at=ereignis,
            open=99, high=102, low=98, volume=1_000, source="test",
        )
        store.append([
            Bar(bar_size="1d", close=100, **gemeinsam),
            Bar(bar_size="1h", close=101, **gemeinsam),
        ])
        sicht = store.view(zeit(2026, 1, 10))
        assert sicht.bars("AAPL.US", "1d").iloc[0]["close"] == 100.0
        assert sicht.bars("AAPL.US", "1h").iloc[0]["close"] == 101.0

    def test_sicht_liefert_kein_ingested_at(self, store) -> None:
        """ingested_at ist der direkteste Weg zu Zukunftswissen."""
        store.append([mach_bar(5)])
        frame = store.view(zeit(2026, 1, 10)).bars("AAPL.US")
        assert "ingested_at" not in frame.columns
        assert "row_id" not in frame.columns

    def test_sicht_braucht_tz_bewussten_stichtag(self, store) -> None:
        with pytest.raises(BarValidationError, match="zeitzonenlos"):
            store.view(dt.datetime(2026, 1, 10))

    def test_letzte_bar(self, store) -> None:
        store.append([mach_bar(tag, close=100 + tag) for tag in (5, 6, 7)])
        assert store.view(zeit(2026, 1, 6, 23)).letzte_bar("AAPL.US")["close"] == 106.0
        assert store.view(zeit(2026, 1, 1)).letzte_bar("AAPL.US") is None


# ---------------------------------------------------------------------------
# Append-only
# ---------------------------------------------------------------------------


class TestAppendOnly:
    def test_kein_update_und_kein_delete(self, store) -> None:
        """Wer Bars überschreiben kann, kann die Vergangenheit umschreiben."""
        for verboten in ("update", "delete", "upsert", "remove", "truncate"):
            assert not hasattr(store, verboten), f"{verboten}() darf es nicht geben"

    def test_korrektur_loescht_das_original_nicht(self, store) -> None:
        store.append([mach_bar(5, close=100.0, available_at=zeit(2026, 1, 5))])
        store.append([mach_bar(5, close=101.5, available_at=zeit(2026, 1, 9))])

        assert store.zeilen_gesamt() == 2
        historie = store.historie("AAPL.US", zeit(2026, 1, 5))
        assert list(historie["close"]) == [100.0, 101.5]

    def test_rohe_tupel_werden_abgelehnt(self, store) -> None:
        """Sonst ließe sich die Eingangsprüfung umgehen."""
        with pytest.raises(BarValidationError, match="Erwartet wurde eine Bar"):
            store.append([("AAPL.US", "1d", 100.0)])  # type: ignore[list-item]

    def test_leeres_anhaengen_ist_erlaubt(self, store) -> None:
        assert store.append([]) == 0

    def test_append_meldet_zeilenzahl(self, store) -> None:
        assert store.append([mach_bar(5), mach_bar(6)]) == 2


# ---------------------------------------------------------------------------
# Zeitzonen
# ---------------------------------------------------------------------------


class TestZeitzonen:
    def test_zeitpunkt_ueberlebt_die_runde_durch_die_datenbank(self, store) -> None:
        """Gleicher Zeitpunkt rein wie raus — auch wenn die Anzeige täuscht.

        DuckDB gibt Zeitstempel in der lokalen Zone zurück. Eine Bar, die als
        14.08. 22:00 UTC hineingeht, kommt in Berlin als 15.08. 00:00+02:00
        wieder heraus. Das ist derselbe Augenblick, sieht aber nach einem Tag
        Versatz aus — und verleitet dazu, "korrigierend" einen echten Fehler
        einzubauen. Der Test hält fest, worauf es ankommt: der Augenblick
        zählt, nicht seine Schreibweise.
        """
        hinein = zeit(2026, 8, 14, stunde=22)
        store.append([mach_bar(14, event_time=hinein, available_at=hinein)])

        heraus = store.view(zeit(2026, 9, 1)).bars("AAPL.US").iloc[0]["event_time"]
        assert heraus.tz_convert("UTC").to_pydatetime() == hinein

    def test_stichtag_in_fremder_zone_liefert_dasselbe(self, store) -> None:
        """Ein Stichtag ist ein Augenblick, keine Uhrzeit auf einem Zifferblatt."""
        store.append([mach_bar(tag, available_at=zeit(2026, 1, tag)) for tag in (5, 6, 7)])

        in_utc = zeit(2026, 1, 6, stunde=12)
        in_tokio = in_utc.astimezone(dt.timezone(dt.timedelta(hours=9)))
        assert in_utc == in_tokio  # derselbe Augenblick, andere Schreibweise

        assert len(store.view(in_utc).bars("AAPL.US")) == len(
            store.view(in_tokio).bars("AAPL.US")
        )


# ---------------------------------------------------------------------------
# Leckage-Tests (Qualitätsstandards 3.3)
# ---------------------------------------------------------------------------


class TestLeckage:
    def test_abschneide_test(self, store) -> None:
        """Test 1: Sicht bei t muss identisch sein, ob später Daten kommen oder nicht.

        Die zentrale Eigenschaft. Fällt sie, ist jede Kennzahl im Projekt
        wertlos, ohne dass irgendetwas abstürzt.
        """
        store.append([mach_bar(tag, close=100 + tag) for tag in range(5, 11)])
        stichtag = zeit(2026, 1, 7, 23)
        vorher = store.view(stichtag).bars("AAPL.US")

        # Zukunft dazu, inklusive Korrektur einer bereits sichtbaren Bar.
        store.append([mach_bar(tag, close=200 + tag) for tag in range(11, 20)])
        store.append([mach_bar(6, close=999.0, available_at=zeit(2026, 1, 15))])

        nachher = store.view(stichtag).bars("AAPL.US")
        pd.testing.assert_frame_equal(vorher, nachher)

    def test_zukunfts_stoertest(self, store) -> None:
        """Test 2: Daten nach t verändern — Sicht bis t darf sich nicht rühren."""
        store.append([mach_bar(tag, close=100 + tag) for tag in range(5, 11)])
        stichtag = zeit(2026, 1, 7, 23)
        vorher = store.view(stichtag).bars("AAPL.US")

        for tag in range(8, 11):
            store.append([mach_bar(tag, close=500.0 + tag, available_at=zeit(2026, 1, 20))])

        pd.testing.assert_frame_equal(vorher, store.view(stichtag).bars("AAPL.US"))

    def test_kein_zugang_zur_rohen_tabelle(self, store) -> None:
        """Strategiecode sieht nur die Sicht — kein öffentlicher Weg zurück."""
        sicht = store.view(zeit(2026, 1, 10))
        oeffentlich = [n for n in dir(sicht) if not n.startswith("_")]
        assert set(oeffentlich) == {"as_of", "bars", "letzte_bar", "symbole"}

    @settings(max_examples=50, deadline=None)
    @given(
        stichtag_tag=st.integers(min_value=1, max_value=28),
        anzahl=st.integers(min_value=1, max_value=20),
    )
    def test_monotonie(self, stichtag_tag: int, anzahl: int) -> None:
        """Ein späterer Stichtag sieht nie weniger als ein früherer.

        Hypothesis sucht das Gegenbeispiel, statt auf handverlesene Fälle zu
        hoffen. Stolpert die Rangfolge bei gleichem available_at, fällt es hier auf.
        """
        with BitemporalStore(":memory:") as s:
            s.append([mach_bar(tag % 28 + 1, close=100 + tag) for tag in range(anzahl)])
            frueh = zeit(2026, 1, stichtag_tag)
            spaet = frueh + dt.timedelta(days=7)
            assert len(s.view(frueh).bars("AAPL.US")) <= len(s.view(spaet).bars("AAPL.US"))


# ---------------------------------------------------------------------------
# Angepasste und unangepasste Preise
# ---------------------------------------------------------------------------


class TestPreisanpassung:
    def test_beide_preiswelten_bleiben_getrennt(self, store) -> None:
        """Siehe docs/20260925_rueckwirkende-anpassung.md."""
        store.append([mach_bar(5, close=256.87, adjusted_close=255.9246)])
        zeile = store.view(zeit(2026, 1, 10)).bars("AAPL.US").iloc[0]
        assert zeile["close"] == 256.87
        assert zeile["adjusted_close"] == pytest.approx(255.9246)

    def test_adjusted_close_darf_fehlen(self, store) -> None:
        """Intraday-Bars von EODHD sind unbereinigt — das Feld bleibt leer."""
        store.append([mach_bar(5, close=100.0, adjusted_close=None)])
        zeile = store.view(zeit(2026, 1, 10)).bars("AAPL.US").iloc[0]
        assert pd.isna(zeile["adjusted_close"])
        assert zeile["close"] == 100.0


# ---------------------------------------------------------------------------
# Dauerhafte Datenbank
# ---------------------------------------------------------------------------


class TestPersistenz:
    def test_daten_ueberleben_das_schliessen(self, tmp_path) -> None:
        pfad = tmp_path / "test.duckdb"
        with BitemporalStore(pfad) as s:
            s.append([mach_bar(5, close=100.0)])
        with BitemporalStore(pfad) as s:
            assert s.view(zeit(2026, 1, 10)).bars("AAPL.US").iloc[0]["close"] == 100.0

    def test_zeitzone_ueberlebt_die_speicherung(self, tmp_path) -> None:
        """TIMESTAMPTZ, nicht TIMESTAMP — sonst kommt ein naiver Wert zurück."""
        pfad = tmp_path / "tz.duckdb"
        with BitemporalStore(pfad) as s:
            s.append([mach_bar(5)])
        with BitemporalStore(pfad) as s:
            frame = s.view(zeit(2026, 1, 10)).bars("AAPL.US")
            assert frame["event_time"].dt.tz is not None
