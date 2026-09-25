"""Tests der harten Filter A5.2 (Auswertung nach Anlage-Spezifikation v1.3).

**Alle ISINs, URLs und Zahlen hier sind Platzhalter** — siehe
``tests/test_stammdaten.py``. Die Volumina sind Grenzwerte der Spezifikation
(100 Mio. €, 500 Mio. €) und Zahlen knapp daneben, keine Fondsdaten.

Der wichtigste Block ist ``TestUnverifiziert``: Ein Wert aus zweiter Hand
darf keinen Filter stillschweigend bestehen lassen.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from trading_app.harte_filter import (
    Ausgang,
    Baustein,
    pruefe_harte_filter,
    volle_kalenderjahre,
)
from trading_app.stammdaten import Feldwert, InstrumentStore, Pruefstatus, QuelleTyp

UTC = dt.timezone.utc
ISIN = "XX0000000002"  # Platzhalter, Prüfziffer von Hand gerechnet
URL = "https://emittent.invalid/kid.pdf"
STICHTAG = dt.datetime(2026, 9, 25, 12, tzinfo=UTC)

INDEX = {
    Baustein.K1: "MSCI ACWI",
    Baustein.K2_GELDMARKT: "€STR",
}


def wert(feld: str, inhalt: object, *, status=Pruefstatus.VERIFIZIERT,
         quelle_typ=QuelleTyp.KID, abgerufen_am=dt.datetime(2026, 3, 1, tzinfo=UTC)) -> Feldwert:
    return Feldwert(
        isin=ISIN, feld=feld, wert=inhalt, quelle_url=URL, quelle_typ=quelle_typ,
        status=status, stand=dt.date(2026, 2, 15), abgerufen_am=abgerufen_am,
    )


def bestehende_werte(baustein: Baustein, **abweichungen: object) -> list[Feldwert]:
    """Ein verifizierter Satz, der alle mechanischen Filter des Bausteins besteht.

    ``abweichungen`` ersetzt einzelne Werte; ``None`` lässt das Feld weg.
    """
    inhalte: dict[str, object] = {
        "ucits": True,
        "gold_etc_lieferanspruch": True,
        "xetra_handelbar": True,
        "kid_sprache_de": True,
        "index_name": INDEX.get(baustein, "Platzhalter-Index"),
        "fondsvolumen": Decimal("500000000"),
        "auflagedatum": dt.date(2015, 6, 1),
        "aktienfonds_invstg": True,
        "waehrungsgesichert": True,
    }
    inhalte.update(abweichungen)
    return [wert(feld, inhalt) for feld, inhalt in inhalte.items() if inhalt is not None]


def befund(baustein: Baustein, werte: list[Feldwert], stichtag: dt.datetime = STICHTAG):
    with InstrumentStore(":memory:") as store:
        store.append(werte)
        return pruefe_harte_filter(store.view(stichtag), ISIN, baustein)


def ausgang(befund_, nummer: int, name: str | None = None) -> Ausgang:
    """Der Ausgang einer Einzelprüfung."""
    treffer = [
        p for p in befund_.pruefungen if p.nummer == nummer and (name is None or p.name == name)
    ]
    assert len(treffer) == 1, f"Prüfung {nummer}/{name} nicht eindeutig: {befund_.pruefungen}"
    return treffer[0].ausgang


# ---------------------------------------------------------------------------
# Vollständige Sätze
# ---------------------------------------------------------------------------


class TestVollstaendig:
    @pytest.mark.parametrize("baustein", [Baustein.K1, Baustein.K2_GELDMARKT])
    def test_bausteine_mit_konkretem_index_sind_zulaessig(self, baustein) -> None:
        b = befund(baustein, bestehende_werte(baustein))
        assert b.zulaessig, b.pruefungen
        assert b.ausgang is Ausgang.ERFUELLT
        assert b.neu is False

    @pytest.mark.parametrize(
        "baustein",
        [Baustein.K2_EUR_STAATSANLEIHEN, Baustein.K2_GLOBALE_ANLEIHEN,
         Baustein.S_GOLD, Baustein.S_FAKTOR],
    )
    def test_indexfamilie_bleibt_offen(self, baustein) -> None:
        """A5.5 nennt hier nur eine Indexfamilie — nicht raten, sondern offen lassen."""
        b = befund(baustein, bestehende_werte(baustein))
        assert ausgang(b, 2) is Ausgang.OFFEN
        assert b.ausgang is Ausgang.OFFEN
        assert not b.zulaessig
        offene = [p for p in b.pruefungen if p.ausgang is not Ausgang.ERFUELLT]
        assert [p.nummer for p in offene] == [2]

    @pytest.mark.parametrize(
        ("baustein", "nummern"),
        [
            (Baustein.K1, [1, 1, 1, 2, 3, 4, 5]),
            (Baustein.K2_GELDMARKT, [1, 1, 1, 2, 3, 4]),
            (Baustein.K2_EUR_STAATSANLEIHEN, [1, 1, 1, 2, 3, 4]),
            (Baustein.K2_GLOBALE_ANLEIHEN, [1, 1, 1, 2, 3, 4, 6]),
            (Baustein.S_GOLD, [1, 1, 1, 2, 3, 4]),
            (Baustein.S_FAKTOR, [1, 1, 1, 2, 3, 4, 5]),
        ],
    )
    def test_welche_filter_je_baustein_laufen(self, baustein, nummern) -> None:
        b = befund(baustein, bestehende_werte(baustein))
        assert [p.nummer for p in b.pruefungen] == nummern

    def test_baustein_als_text(self) -> None:
        b = befund("K1 Aktien Welt", bestehende_werte(Baustein.K1))
        assert b.baustein is Baustein.K1

    def test_unbekannter_baustein_wird_abgelehnt(self) -> None:
        with pytest.raises(ValueError):
            befund("K3", bestehende_werte(Baustein.K1))


# ---------------------------------------------------------------------------
# Filter 1: UCITS / Gold-ETC, Handelsplatz, KID
# ---------------------------------------------------------------------------


class TestFilter1:
    def test_kein_ucits_ist_verletzt(self) -> None:
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, ucits=False))
        assert ausgang(b, 1, "UCITS") is Ausgang.VERLETZT
        assert b.ausgang is Ausgang.VERLETZT

    def test_kein_deutsches_kid_ist_verletzt(self) -> None:
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, kid_sprache_de=False))
        assert ausgang(b, 1, "KID auf Deutsch") is Ausgang.VERLETZT

    def test_nicht_an_xetra_ist_offen_nicht_verletzt(self) -> None:
        """A5.2 lässt jeden deutschen Handelsplatz zu; das Feld kennt nur Xetra."""
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, xetra_handelbar=False))
        assert ausgang(b, 1, "Xetra") is Ausgang.OFFEN
        assert not b.zulaessig

    def test_gold_braucht_lieferanspruch_statt_ucits(self) -> None:
        """Ein Gold-ETC ist kein UCITS-Fonds; für S-Gold zählt der Lieferanspruch."""
        b = befund(Baustein.S_GOLD, bestehende_werte(Baustein.S_GOLD, ucits=False))
        assert ausgang(b, 1, "ETC mit Lieferanspruch") is Ausgang.ERFUELLT

        ohne = befund(
            Baustein.S_GOLD, bestehende_werte(Baustein.S_GOLD, gold_etc_lieferanspruch=False)
        )
        assert ausgang(ohne, 1, "ETC mit Lieferanspruch") is Ausgang.VERLETZT


# ---------------------------------------------------------------------------
# Filter 2: Index
# ---------------------------------------------------------------------------


class TestFilter2:
    @pytest.mark.parametrize("index", ["MSCI ACWI", "MSCI ACWI IMI", "FTSE All-World"])
    def test_k1_indizes_aus_a5_5(self, index) -> None:
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, index_name=index))
        assert ausgang(b, 2) is Ausgang.ERFUELLT

    @pytest.mark.parametrize("index", ["MSCI World", "MSCI ACWI ex USA", "€STR"])
    def test_anderer_index_ist_fuer_k1_verletzt(self, index) -> None:
        """World + EM ist eine Kombination auf Nutzerwunsch (A5.4), kein Einzelfonds für K1."""
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, index_name=index))
        assert ausgang(b, 2) is Ausgang.VERLETZT

    def test_geldmarkt_braucht_estr(self) -> None:
        b = befund(Baustein.K2_GELDMARKT,
                   bestehende_werte(Baustein.K2_GELDMARKT, index_name="MSCI ACWI"))
        assert ausgang(b, 2) is Ausgang.VERLETZT


# ---------------------------------------------------------------------------
# Filter 3: Fondsvolumen
# ---------------------------------------------------------------------------


class TestFilter3:
    @pytest.mark.parametrize(
        ("baustein", "volumen", "erwartet"),
        [
            (Baustein.K2_EUR_STAATSANLEIHEN, "100000000", Ausgang.ERFUELLT),  # ≥, Grenze gilt
            (Baustein.K2_EUR_STAATSANLEIHEN, "99999999.99", Ausgang.VERLETZT),
            (Baustein.K2_EUR_STAATSANLEIHEN, "50000000", Ausgang.VERLETZT),
            (Baustein.K2_EUR_STAATSANLEIHEN, "10000000", Ausgang.VERLETZT),
            (Baustein.S_FAKTOR, "100000000", Ausgang.ERFUELLT),
            (Baustein.S_GOLD, "99999999.99", Ausgang.VERLETZT),
            (Baustein.K2_GLOBALE_ANLEIHEN, "100000000", Ausgang.ERFUELLT),
            (Baustein.K1, "500000000", Ausgang.ERFUELLT),
            (Baustein.K1, "499999999.99", Ausgang.VERLETZT),
            (Baustein.K1, "100000000", Ausgang.VERLETZT),
            (Baustein.K2_GELDMARKT, "500000000", Ausgang.ERFUELLT),
            (Baustein.K2_GELDMARKT, "499999999.99", Ausgang.VERLETZT),
        ],
    )
    def test_schwellen(self, baustein, volumen, erwartet) -> None:
        b = befund(baustein, bestehende_werte(baustein, fondsvolumen=Decimal(volumen)))
        assert ausgang(b, 3) is erwartet


# ---------------------------------------------------------------------------
# Filter 4: Historie
# ---------------------------------------------------------------------------


class TestFilter4:
    @pytest.mark.parametrize(
        ("auflage", "stichtag", "jahre"),
        [
            (dt.date(2023, 1, 2), dt.date(2026, 9, 25), 2),  # 2023 nicht voll
            (dt.date(2023, 1, 1), dt.date(2026, 9, 25), 3),  # 2023 voll
            (dt.date(2022, 12, 31), dt.date(2026, 9, 25), 3),  # 2023–2025
            (dt.date(2025, 6, 1), dt.date(2026, 1, 1), 0),
            (dt.date(2025, 1, 1), dt.date(2026, 1, 1), 1),
            (dt.date(2025, 1, 1), dt.date(2025, 12, 31), 0),  # laufendes Jahr zählt nie
            (dt.date(2027, 1, 1), dt.date(2026, 9, 25), 0),  # Auflage nach dem Stichtag
        ],
    )
    def test_volle_kalenderjahre(self, auflage, stichtag, jahre) -> None:
        assert volle_kalenderjahre(auflage, stichtag) == jahre

    @pytest.mark.parametrize(
        ("auflage", "neu"),
        [
            (dt.date(2022, 6, 1), False),  # 2023, 2024, 2025
            (dt.date(2023, 6, 1), True),  # 2024, 2025
            (dt.date(2025, 6, 1), True),  # keins
        ],
    )
    def test_juengere_fonds_sind_neu_aber_nicht_ausgeschlossen(self, auflage, neu) -> None:
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, auflagedatum=auflage))
        assert b.neu is neu
        assert ausgang(b, 4) is Ausgang.ERFUELLT
        assert b.zulaessig

    def test_stichtag_der_sicht_zaehlt(self) -> None:
        """Derselbe Fonds, zwei Stichtage: erst neu, dann nicht mehr."""
        werte = bestehende_werte(Baustein.K1, auflagedatum=dt.date(2023, 6, 1))
        assert befund(Baustein.K1, werte, dt.datetime(2026, 12, 31, tzinfo=UTC)).neu is True
        assert befund(Baustein.K1, werte, dt.datetime(2027, 1, 1, tzinfo=UTC)).neu is False


# ---------------------------------------------------------------------------
# Filter 5 und 6
# ---------------------------------------------------------------------------


class TestFilter5Und6:
    @pytest.mark.parametrize("baustein", [Baustein.K1, Baustein.S_FAKTOR])
    def test_aktien_bausteine_brauchen_aktienfonds(self, baustein) -> None:
        b = befund(baustein, bestehende_werte(baustein, aktienfonds_invstg=False))
        assert ausgang(b, 5) is Ausgang.VERLETZT

    def test_globale_anleihen_brauchen_eur_absicherung(self) -> None:
        b = befund(Baustein.K2_GLOBALE_ANLEIHEN,
                   bestehende_werte(Baustein.K2_GLOBALE_ANLEIHEN, waehrungsgesichert=False))
        assert ausgang(b, 6) is Ausgang.VERLETZT

    def test_euro_anleihen_brauchen_keine_absicherung(self) -> None:
        b = befund(Baustein.K2_EUR_STAATSANLEIHEN,
                   bestehende_werte(Baustein.K2_EUR_STAATSANLEIHEN, waehrungsgesichert=False))
        assert 6 not in [p.nummer for p in b.pruefungen]


# ---------------------------------------------------------------------------
# Unverifizierte und fehlende Werte — der wichtigste Block
# ---------------------------------------------------------------------------


class TestUnverifiziert:
    def test_unverifizierter_wert_besteht_nie(self) -> None:
        """Ein Volumen aus zweiter Hand, weit über der Schwelle: trotzdem offen."""
        werte = bestehende_werte(Baustein.K1, fondsvolumen=None) + [
            wert("fondsvolumen", Decimal("99000000000"), status=Pruefstatus.UNVERIFIZIERT,
                 quelle_typ=QuelleTyp.SEKUNDAER),
        ]
        b = befund(Baustein.K1, werte)
        assert ausgang(b, 3) is Ausgang.OFFEN
        assert not b.zulaessig
        begruendung = next(p.begruendung for p in b.pruefungen if p.nummer == 3)
        assert "UNVERIFIZIERT" in begruendung
        assert "Primärdokument" in begruendung

    def test_unverifiziert_aus_primaerdokument_besteht_auch_nicht(self) -> None:
        """Aus dem KID abgeschrieben, aber noch nicht abgeglichen: offen."""
        werte = bestehende_werte(Baustein.K1, ucits=None) + [
            wert("ucits", True, status=Pruefstatus.UNVERIFIZIERT),
        ]
        assert ausgang(befund(Baustein.K1, werte), 1, "UCITS") is Ausgang.OFFEN

    def test_unverifizierter_verstoss_ist_offen_nicht_verletzt(self) -> None:
        """Zweite Hand schließt auch nicht endgültig aus."""
        werte = bestehende_werte(Baustein.K1, fondsvolumen=None) + [
            wert("fondsvolumen", Decimal("1"), status=Pruefstatus.UNVERIFIZIERT,
                 quelle_typ=QuelleTyp.SEKUNDAER),
        ]
        assert ausgang(befund(Baustein.K1, werte), 3) is Ausgang.OFFEN

    @pytest.mark.parametrize(
        ("feld", "nummer"),
        [("ucits", 1), ("index_name", 2), ("fondsvolumen", 3), ("auflagedatum", 4),
         ("aktienfonds_invstg", 5)],
    )
    def test_fehlender_wert_ist_offen(self, feld, nummer) -> None:
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, **{feld: None}))
        offene = [p for p in b.pruefungen if p.ausgang is Ausgang.OFFEN]
        assert [p.nummer for p in offene] == [nummer]
        assert "kein Wert" in offene[0].begruendung
        assert not b.zulaessig

    def test_unverifizierte_historie_ist_offen_und_nicht_neu(self) -> None:
        werte = bestehende_werte(Baustein.K1, auflagedatum=None) + [
            wert("auflagedatum", dt.date(2025, 6, 1), status=Pruefstatus.UNVERIFIZIERT),
        ]
        b = befund(Baustein.K1, werte)
        assert ausgang(b, 4) is Ausgang.OFFEN
        assert b.neu is False

    def test_verletzt_schlaegt_offen(self) -> None:
        """Ein verifizierter Verstoß schließt aus, egal was sonst offen ist."""
        b = befund(Baustein.K1, bestehende_werte(Baustein.K1, ucits=False, fondsvolumen=None))
        assert ausgang(b, 3) is Ausgang.OFFEN
        assert b.ausgang is Ausgang.VERLETZT


# ---------------------------------------------------------------------------
# Point-in-time in den Filtern
# ---------------------------------------------------------------------------


class TestStichtag:
    def test_wert_nach_dem_stichtag_zaehlt_nicht(self) -> None:
        spaet = dt.datetime(2026, 10, 1, tzinfo=UTC)
        werte = bestehende_werte(Baustein.K1, fondsvolumen=None) + [
            wert("fondsvolumen", Decimal("600000000"), abgerufen_am=spaet),
        ]
        assert ausgang(befund(Baustein.K1, werte, STICHTAG), 3) is Ausgang.OFFEN
        assert ausgang(befund(Baustein.K1, werte, spaet), 3) is Ausgang.ERFUELLT

    def test_spaetere_korrektur_aendert_frueheren_befund_nicht(self) -> None:
        """Volumen fällt nach dem Stichtag unter die Schwelle — der Befund per Stichtag bleibt."""
        werte = bestehende_werte(Baustein.K1) + [
            wert("fondsvolumen", Decimal("1"), abgerufen_am=dt.datetime(2026, 10, 1, tzinfo=UTC)),
        ]
        assert befund(Baustein.K1, werte, STICHTAG).zulaessig
        spaeter = befund(Baustein.K1, werte, dt.datetime(2026, 10, 2, tzinfo=UTC))
        assert ausgang(spaeter, 3) is Ausgang.VERLETZT

    def test_befund_traegt_den_stichtag(self) -> None:
        assert befund(Baustein.K1, bestehende_werte(Baustein.K1)).stichtag == STICHTAG
