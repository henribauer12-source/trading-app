"""Harte Filter der Produktauswahl (Anlage-Spezifikation A5.2, Auswertung v1.3).

„Ja/nein je Baustein“ — mit einem dritten Ausgang. Jede Prüfung endet mit
``erfüllt``, ``verletzt`` oder ``offen``:

- **offen**, wenn der Wert zum Stichtag fehlt oder UNVERIFIZIERT ist. Ein
  Wert aus zweiter Hand lässt einen Filter nie bestehen — auch dann nicht,
  wenn er ihn bestehen *würde*. Er schließt aber auch nicht endgültig aus.
- **zulässig** ist ein Produkt nur ohne verletzte und ohne offene Prüfung.

Warum ein Ergebnis und keine Ausnahme: Eine Ausnahme ließe einen einzigen
ungeprüften Wert die Auswertung aller dreißig Kandidaten abbrechen, und wer
sie mit ``try/except`` umgeht, lässt genau das durch, was sie aufhalten
sollte. Warum keine bloße Warnung: Eine Warnung neben einem „bestanden“ wird
übersehen, und dann steht ein Produkt auf Grundlage einer Zahl aus zweiter
Hand in der Empfehlung. Der Ausgang ``offen`` ist beides zugleich: Das
Produkt ist nicht zulässig, und die Begründung sagt, welcher Wert am
Primärdokument zu prüfen ist.

Nicht hier: die Bewertung A5.3, die Indexwahl A5.4, der Produktwechsel A5.6
und Filter 7 (sparplanfähig beim Broker — Nutzerdaten, keine Stammdaten).

Alle Werte kommen aus einer ``InstrumentView``; ihr Stichtag ist auch der
Stichtag für die Historie (Filter 4).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from trading_app.stammdaten import Feldwert, InstrumentView, Pruefstatus

__all__ = [
    "Ausgang",
    "Baustein",
    "Filterbefund",
    "Pruefung",
    "pruefe_harte_filter",
    "volle_kalenderjahre",
]


class Baustein(StrEnum):
    """Die Bausteine aus A5.5."""

    K1 = "K1 Aktien Welt"
    K2_GELDMARKT = "K2 Geldmarkt"
    K2_EUR_STAATSANLEIHEN = "K2 EUR-Staatsanleihen"
    K2_GLOBALE_ANLEIHEN = "K2 Globale Anleihen"
    S_GOLD = "S-Gold"
    S_FAKTOR = "S-Faktor"


class Ausgang(StrEnum):
    ERFUELLT = "erfüllt"
    VERLETZT = "verletzt"
    OFFEN = "offen"


# A5.2 Nr. 3: 100 Mio. € VERIFIZIERT (Lipper 2025); 500 Mio. € für K1 und
# Geldmarkt ENTSCHEIDUNG (eine Schließung realisiert Gewinne).
MINDESTVOLUMEN = Decimal("100000000")
MINDESTVOLUMEN_GROSS = Decimal("500000000")
_GROSSE_BAUSTEINE = frozenset({Baustein.K1, Baustein.K2_GELDMARKT})

# A5.2 Nr. 4.
MINDEST_KALENDERJAHRE = 3

# A5.2 Nr. 2 nach A5.5, nur wo A5.5 konkrete Indizes nennt (v1.3). Schreibweise
# exakt wie in A5.5 — so muss index_name in der Quelldatei stehen.
_INDIZES_A5_5 = {
    Baustein.K1: frozenset({"MSCI ACWI", "MSCI ACWI IMI", "FTSE All-World"}),
    Baustein.K2_GELDMARKT: frozenset({"€STR"}),
}

_AKTIEN_BAUSTEINE = frozenset({Baustein.K1, Baustein.S_FAKTOR})  # Nr. 5
_FREMDWAEHRUNGS_ANLEIHEN = frozenset({Baustein.K2_GLOBALE_ANLEIHEN})  # Nr. 6


@dataclass(frozen=True, slots=True)
class Pruefung:
    """Eine einzelne Prüfung; ``nummer`` ist die Nummer in A5.2."""

    nummer: int
    name: str
    ausgang: Ausgang
    begruendung: str


@dataclass(frozen=True, slots=True)
class Filterbefund:
    """Alle Prüfungen eines Instruments für einen Baustein zu einem Stichtag.

    Attribute:
        neu: Weniger als drei volle Kalenderjahre (Filter 4). Kein Ausschluss,
            sondern eine Kennzeichnung für die Bewertung A5.3.
    """

    isin: str
    baustein: Baustein
    stichtag: dt.datetime
    pruefungen: tuple[Pruefung, ...]
    neu: bool

    @property
    def ausgang(self) -> Ausgang:
        """Verletzt vor offen vor erfüllt."""
        ausgaenge = {pruefung.ausgang for pruefung in self.pruefungen}
        for schwerster in (Ausgang.VERLETZT, Ausgang.OFFEN):
            if schwerster in ausgaenge:
                return schwerster
        return Ausgang.ERFUELLT

    @property
    def zulaessig(self) -> bool:
        return self.ausgang is Ausgang.ERFUELLT


def volle_kalenderjahre(auflagedatum: dt.date, stichtag: dt.date) -> int:
    """Kalenderjahre, die ganz zwischen Auflage und Stichtag liegen (A5.2 Nr. 4, v1.3).

    Das laufende Jahr zählt nie, das Auflagejahr nur bei Auflage am 1. Januar.
    Kalenderjahre, weil A5.3 die Tracking-Differenz je Kalenderjahr mittelt:
    drei volle Jahre heißt drei Jahreswerte.
    """
    erstes = auflagedatum.year + (0 if (auflagedatum.month, auflagedatum.day) == (1, 1) else 1)
    return max(0, stichtag.year - erstes)


def pruefe_harte_filter(sicht: InstrumentView, isin: str, baustein: Baustein) -> Filterbefund:
    """Prüft A5.2 Nr. 1–6 für ein Instrument als Kandidat für einen Baustein.

    Args:
        sicht: Stammdaten zum Stichtag.
        isin: Das Instrument.
        baustein: Für welchen Baustein es geprüft wird — die Filter hängen
            davon ab (Volumenschwelle, Index, Aktienfonds, Währungssicherung).

    Returns:
        Den Befund mit jeder Einzelprüfung und ihrer Begründung.
    """
    baustein = Baustein(baustein)
    pruefungen: list[Pruefung] = []

    # Nr. 1
    if baustein is Baustein.S_GOLD:
        pruefungen.append(
            _pruefe(sicht, isin, 1, "ETC mit Lieferanspruch", "gold_etc_lieferanspruch", _ja)
        )
    else:
        pruefungen.append(_pruefe(sicht, isin, 1, "UCITS", "ucits", _ja))
    # Nicht an Xetra ist kein Ausschluss: A5.2 lässt jeden deutschen
    # Handelsplatz zu, der aber nicht als Feld erfasst ist → von Hand prüfen.
    pruefungen.append(
        _pruefe(sicht, isin, 1, "Xetra", "xetra_handelbar", _ja, sonst=Ausgang.OFFEN)
    )
    pruefungen.append(_pruefe(sicht, isin, 1, "KID auf Deutsch", "kid_sprache_de", _ja))

    # Nr. 2
    indizes = _INDIZES_A5_5.get(baustein)
    if indizes is None:
        pruefungen.append(
            Pruefung(
                2,
                "Index",
                Ausgang.OFFEN,
                f"A5.5 nennt für {baustein} nur eine Indexfamilie; von Hand prüfen, "
                "bis A5.5 konkrete Indizes nennt",
            )
        )
    else:
        pruefungen.append(
            _pruefe(
                sicht, isin, 2, "Index", "index_name", indizes.__contains__,
                regel=f"einer von {sorted(indizes)}",
            )
        )

    # Nr. 3
    schwelle = MINDESTVOLUMEN_GROSS if baustein in _GROSSE_BAUSTEINE else MINDESTVOLUMEN
    pruefungen.append(
        _pruefe(
            sicht, isin, 3, "Fondsvolumen", "fondsvolumen", lambda wert: wert >= schwelle,
            regel=f"≥ {schwelle} EUR",
        )
    )

    # Nr. 4
    historie, neu = _pruefe_historie(sicht, isin)
    pruefungen.append(historie)

    # Nr. 5
    if baustein in _AKTIEN_BAUSTEINE:
        pruefungen.append(
            _pruefe(sicht, isin, 5, "Aktienfonds (§ 2 Abs. 6 InvStG)", "aktienfonds_invstg", _ja)
        )

    # Nr. 6
    if baustein in _FREMDWAEHRUNGS_ANLEIHEN:
        pruefungen.append(_pruefe(sicht, isin, 6, "EUR-abgesichert", "waehrungsgesichert", _ja))

    return Filterbefund(isin, baustein, sicht.as_of, tuple(pruefungen), neu)


def _ja(wert: Any) -> bool:
    return wert is True


def _verifizierter_wert(
    sicht: InstrumentView, isin: str, nummer: int, name: str, feld: str
) -> tuple[Feldwert | None, Pruefung | None]:
    """Der Wert, oder eine offene Prüfung, wenn er fehlt oder unverifiziert ist."""
    wert = sicht.feld(isin, feld)
    if wert is None:
        return None, Pruefung(
            nummer, name, Ausgang.OFFEN, f"{feld}: zum Stichtag kein Wert bekannt"
        )
    if wert.status is not Pruefstatus.VERIFIZIERT:
        return None, Pruefung(
            nummer,
            name,
            Ausgang.OFFEN,
            f"{feld} = {wert.wert} ist {wert.status} ({wert.quelle_typ}, {wert.quelle_url}); "
            "zählt erst nach Abgleich mit dem Primärdokument",
        )
    return wert, None


def _pruefe(
    sicht: InstrumentView,
    isin: str,
    nummer: int,
    name: str,
    feld: str,
    bedingung: Callable[[Any], bool],
    *,
    regel: str = "ja",
    sonst: Ausgang = Ausgang.VERLETZT,
) -> Pruefung:
    wert, offen = _verifizierter_wert(sicht, isin, nummer, name, feld)
    if offen is not None:
        return offen
    ausgang = Ausgang.ERFUELLT if bedingung(wert.wert) else sonst
    return Pruefung(
        nummer,
        name,
        ausgang,
        f"{feld} = {wert.wert}, verlangt {regel} ({wert.quelle_typ}, Stand {wert.stand})",
    )


def _pruefe_historie(sicht: InstrumentView, isin: str) -> tuple[Pruefung, bool]:
    wert, offen = _verifizierter_wert(sicht, isin, 4, "Historie", "auflagedatum")
    if offen is not None:
        return offen, False
    jahre = volle_kalenderjahre(wert.wert, sicht.as_of.date())
    neu = jahre < MINDEST_KALENDERJAHRE
    begruendung = f"{jahre} volle Kalenderjahre seit Auflage am {wert.wert}"
    if neu:
        begruendung += (
            f"; weniger als {MINDEST_KALENDERJAHRE}: „neu“, Nettokosten über die TER "
            "mit 5 Punkten Abschlag (A5.3)"
        )
    return Pruefung(4, "Historie", Ausgang.ERFUELLT, begruendung), neu
