"""Einzeldownload öffentlicher Pflichtdokumente (KID, Factsheet) — und nichts sonst.

A5.1 erlaubt, öffentliche Pflichtdokumente manuell oder als einzelnen
Download mit niedriger Frequenz zu holen. Verboten sind automatisierte
Abfragen bei justETF (AGB § 3.1) und Vanguard (Nutzungsbedingungen) sowie
undokumentierte interne APIs von Emittenten (z. B. iShares). Das Verbot
steht deshalb im Code, nicht nur in der Doku:

1. **Sperrliste.** Beginnt ein Label des Hostnamens mit ``justetf`` oder
   ``vanguard``, wird die Adresse vor jeder Verbindung abgewiesen — auch als
   Ziel einer Weiterleitung. Präfix statt exakter Domain, weil Vanguard unter
   vielen Namen auftritt (``vanguard.de``, ``global.vanguard.com``,
   ``vanguardinvestor.co.uk``, die eigene Endung ``.vanguard``). Lieber eine
   fremde Seite zu viel gesperrt als eine verbotene zugelassen.
2. **Nur einzelne PDF-Dokumente.** Nur ``https``, der Pfad endet auf
   ``.pdf``, keine Query, und die Antwort muss mit ``%PDF-`` beginnen.
   Interne APIs lassen sich nicht per Domain sperren, weil sie auf denselben
   Hosts liegen wie die erlaubten PDFs. Die Regel lässt deshalb nur eine
   Adressform zu, die ein Dokument bezeichnet und keine Abfrage.
3. **Eine Adresse pro Aufruf.** Keine Schleife, keine Link-Verfolgung.

Was so nicht erreichbar ist, lädt ein Mensch im Browser und trägt die Adresse
in die Quelldatei ein (``stammdaten.lade_quelldatei``).

Nicht geregelt, weil A5.1 keine Zahl nennt: was „niedrige Frequenz“ heißt.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

__all__ = [
    "DokumentError",
    "VerboteneQuelleError",
    "lade_dokument",
    "pruefe_url",
]

# Label-Präfixe gesperrter Anbieter (A5.1).
_GESPERRT = ("justetf", "vanguard")

# Ein KID hat drei Seiten, ein Factsheet wenige. Alles darüber ist kein
# Pflichtdokument.
_HOECHSTGROESSE = 50 * 1024 * 1024


class DokumentError(RuntimeError):
    """Der Download ist gescheitert oder lieferte kein PDF."""


class VerboteneQuelleError(DokumentError):
    """Die Adresse ist nach A5.1 für automatisierte Abrufe verboten."""


def _pruefe_host(url: str) -> None:
    """https und Sperrliste. Gilt auch für jedes Weiterleitungsziel."""
    teile = urllib.parse.urlsplit(url)
    if teile.scheme != "https":
        raise VerboteneQuelleError(f"Nur https-Adressen, war {teile.scheme!r}: {url}")
    host = (teile.hostname or "").lower()
    if not host:
        raise VerboteneQuelleError(f"Adresse ohne Host: {url}")
    if any(label.startswith(_GESPERRT) for label in host.split(".")):
        raise VerboteneQuelleError(
            f"{host} ist gesperrt. Automatisierte Abfragen bei justETF (AGB § 3.1) und "
            "Vanguard (Nutzungsbedingungen) sind verboten (Anlage-Spezifikation A5.1). "
            "Das Dokument von Hand im Browser laden und die Adresse in die Quelldatei eintragen."
        )


def pruefe_url(url: str) -> None:
    """Prüft eine Adresse vor dem ersten Abruf.

    Raises:
        VerboteneQuelleError: Gesperrter Anbieter, kein https, oder keine
            einzelne PDF-Datei.
    """
    _pruefe_host(url)
    teile = urllib.parse.urlsplit(url)
    if teile.query or not teile.path.lower().endswith(".pdf"):
        raise VerboteneQuelleError(
            f"Nur einzelne PDF-Dokumente: Der Pfad muss auf .pdf enden, ohne Query. War: {url}. "
            "Undokumentierte interne APIs von Emittenten sind verboten (A5.1)."
        )


class _GepruefteWeiterleitung(urllib.request.HTTPRedirectHandler):
    """Prüft jedes Weiterleitungsziel, bevor es aufgerufen wird.

    Ohne diese Klasse folgt urllib einer Weiterleitung still — ein Link über
    einen Kurz-URL-Dienst könnte bei einem gesperrten Anbieter landen.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _pruefe_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def lade_dokument(url: str, ziel: str | Path, *, timeout: float = 30.0) -> Path:
    """Lädt genau ein öffentliches PDF und legt es ab.

    Der Dateiname ist der SHA-256 des Inhalts: Dieselbe Fassung ergibt
    dieselbe Datei, eine neue Fassung überschreibt keine alte.

    Args:
        url: Adresse des Dokuments (https, Pfad auf ``.pdf``, ohne Query).
        ziel: Ordner für die Ablage — außerhalb von iCloud, etwa
            ``~/claude-local/trading-app/dokumente/``.
        timeout: Zeitlimit in Sekunden.

    Returns:
        Pfad der abgelegten Datei.

    Raises:
        VerboteneQuelleError: Adresse oder Weiterleitungsziel ist verboten.
            In diesem Fall gab es keine Verbindung zum verbotenen Host.
        DokumentError: Netz- oder HTTP-Fehler, zu groß, oder kein PDF.
    """
    pruefe_url(url)
    oeffner = urllib.request.build_opener(_GepruefteWeiterleitung)
    try:
        with oeffner.open(url, timeout=timeout) as antwort:
            inhalt = antwort.read(_HOECHSTGROESSE + 1)
    except urllib.error.HTTPError as fehler:
        raise DokumentError(f"HTTP {fehler.code} bei {url}") from fehler
    except urllib.error.URLError as fehler:
        raise DokumentError(f"Netzwerkfehler bei {url}: {fehler.reason}") from fehler

    if len(inhalt) > _HOECHSTGROESSE:
        raise DokumentError(f"{url} ist größer als {_HOECHSTGROESSE} Byte — kein Pflichtdokument")
    if not inhalt.startswith(b"%PDF-"):
        raise DokumentError(
            f"{url} lieferte kein PDF (Anfang: {inhalt[:20]!r}). Nichts abgelegt."
        )

    ordner = Path(ziel).expanduser()
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / f"{hashlib.sha256(inhalt).hexdigest()}.pdf"
    pfad.write_bytes(inhalt)
    return pfad
