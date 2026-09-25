"""Tests des Einzeldownloads mit Sperrliste (Anlage-Spezifikation A5.1).

Ohne Netz. Die gesperrten Hostnamen stehen hier nur als Zeichenketten; kein
Test baut eine Verbindung auf. Erlaubte Adressen enden auf ``.invalid``
(RFC 2606) und existieren nicht.

Der wichtigste Test ist ``test_gesperrte_adresse_oeffnet_keine_verbindung``:
Das Verbot heißt „kein automatisierter Zugriff“, also darf nicht einmal die
Anfrage hinausgehen.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request

import pytest

from trading_app.sources import dokumente
from trading_app.sources.dokumente import (
    DokumentError,
    VerboteneQuelleError,
    lade_dokument,
    pruefe_url,
)

PDF = b"%PDF-1.7\n% Platzhalter, kein echtes Dokument\n%%EOF\n"
ERLAUBT = "https://emittent.invalid/dokumente/kid.pdf"


class FakeAntwort(io.BytesIO):
    def __enter__(self) -> FakeAntwort:
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.fixture
def fake_oeffner(monkeypatch):
    """Ersetzt build_opener. Hält fest, mit welchen Handlern er gebaut wurde."""
    protokoll: dict[str, list] = {"handler": [], "urls": []}

    def setze(inhalt: bytes = PDF):
        class Oeffner:
            def open(self, url, timeout=None):  # noqa: ARG002
                protokoll["urls"].append(url)
                return FakeAntwort(inhalt)

        def bauen(*handler):
            protokoll["handler"].extend(handler)
            return Oeffner()

        monkeypatch.setattr(urllib.request, "build_opener", bauen)
        return protokoll

    return setze


# ---------------------------------------------------------------------------
# Sperrliste — hart einprogrammiert
# ---------------------------------------------------------------------------


class TestSperrliste:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.justetf.com/dokument.pdf",
            "https://justetf.com/dokument.pdf",
            "https://WWW.JUSTETF.COM/dokument.pdf",
            "https://www.justetf.de/dokument.pdf",
            "https://www.vanguard.de/dokument.pdf",
            "https://global.vanguard.com/dokument.pdf",
            "https://www.de.vanguard/dokument.pdf",
            "https://www.vanguardinvestor.co.uk/dokument.pdf",
            "https://www.justetf.com:443/dokument.pdf",
            "https://www.justetf.com./dokument.pdf",  # abschließender Punkt
            "https://emittent.invalid@www.justetf.com/dokument.pdf",  # Userinfo täuscht
        ],
    )
    def test_gesperrte_anbieter(self, url) -> None:
        with pytest.raises(VerboteneQuelleError, match="gesperrt"):
            pruefe_url(url)

    def test_meldung_nennt_grund_und_ausweg(self) -> None:
        with pytest.raises(VerboteneQuelleError) as fehler:
            pruefe_url("https://www.justetf.com/dokument.pdf")
        text = str(fehler.value)
        assert "A5.1" in text
        assert "von Hand" in text

    def test_aehnlicher_name_mitten_im_label_ist_nicht_gesperrt(self) -> None:
        """Gesperrt wird nach Label-Anfang, nicht nach Teilzeichenkette irgendwo."""
        pruefe_url("https://www.meinvanguard-vergleich.invalid/dokument.pdf")

    @pytest.mark.parametrize(
        "url",
        [
            ERLAUBT,
            "https://emittent.invalid/DOKUMENTE/KID.PDF",
            "https://emittent.invalid/kid.pdf#seite=2",
        ],
    )
    def test_einzelnes_pdf_beim_emittenten_ist_erlaubt(self, url) -> None:
        pruefe_url(url)


class TestNurEinzelnePdf:
    @pytest.mark.parametrize(
        "url",
        [
            "https://emittent.invalid/api/produkte?format=json",
            "https://emittent.invalid/kid.pdf?sprache=de",
            "https://emittent.invalid/produkt/uebersicht",
            "https://emittent.invalid/",
        ],
    )
    def test_abfragen_und_seiten_sind_verboten(self, url) -> None:
        """Interne APIs lassen sich nicht per Domain sperren — per Adressform schon."""
        with pytest.raises(VerboteneQuelleError, match="PDF"):
            pruefe_url(url)

    @pytest.mark.parametrize(
        "url", ["http://emittent.invalid/kid.pdf", "ftp://emittent.invalid/kid.pdf", "kid.pdf"]
    )
    def test_nur_https(self, url) -> None:
        with pytest.raises(VerboteneQuelleError, match="https"):
            pruefe_url(url)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class TestDownload:
    def test_gesperrte_adresse_oeffnet_keine_verbindung(self, monkeypatch, tmp_path) -> None:
        def verboten(*_):
            raise AssertionError("Verbindung aufgebaut, obwohl die Adresse gesperrt ist")

        monkeypatch.setattr(urllib.request, "build_opener", verboten)
        with pytest.raises(VerboteneQuelleError):
            lade_dokument("https://www.justetf.com/dokument.pdf", tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_pdf_wird_unter_seinem_hash_abgelegt(self, fake_oeffner, tmp_path) -> None:
        protokoll = fake_oeffner(PDF)
        pfad = lade_dokument(ERLAUBT, tmp_path / "dokumente")
        assert pfad.read_bytes() == PDF
        assert pfad.name == hashlib.sha256(PDF).hexdigest() + ".pdf"
        assert protokoll["urls"] == [ERLAUBT]

    def test_weiterleitungen_werden_geprueft(self, fake_oeffner, tmp_path) -> None:
        """Ohne den eigenen Handler folgte urllib einer Weiterleitung ungeprüft."""
        protokoll = fake_oeffner(PDF)
        lade_dokument(ERLAUBT, tmp_path)
        assert dokumente._GepruefteWeiterleitung in protokoll["handler"]

    def test_kein_pdf_wird_nicht_abgelegt(self, fake_oeffner, tmp_path) -> None:
        fake_oeffner(b'{"produkte": []}')
        with pytest.raises(DokumentError, match="kein PDF"):
            lade_dokument(ERLAUBT, tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_zu_grosse_antwort_wird_abgelehnt(self, fake_oeffner, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr(dokumente, "_HOECHSTGROESSE", 10)
        fake_oeffner(PDF)
        with pytest.raises(DokumentError, match="größer"):
            lade_dokument(ERLAUBT, tmp_path)


class TestWeiterleitung:
    def _anfrage(self) -> urllib.request.Request:
        return urllib.request.Request(ERLAUBT)

    @pytest.mark.parametrize(
        "ziel",
        ["https://www.justetf.com/umweg.pdf", "https://global.vanguard.com/umweg.pdf",
         "http://emittent.invalid/kid.pdf"],
    )
    def test_weiterleitung_zu_verbotenem_ziel_bricht_ab(self, ziel) -> None:
        handler = dokumente._GepruefteWeiterleitung()
        with pytest.raises(VerboteneQuelleError):
            handler.redirect_request(self._anfrage(), None, 302, "Found", {}, ziel)

    def test_weiterleitung_zum_cdn_mit_query_ist_erlaubt(self) -> None:
        """Signierte CDN-Adressen tragen Query-Parameter; geprüft wird dann der Inhalt."""
        handler = dokumente._GepruefteWeiterleitung()
        neu = handler.redirect_request(
            self._anfrage(), None, 302, "Found", {}, "https://cdn.invalid/kid.pdf?signatur=abc"
        )
        assert neu.full_url == "https://cdn.invalid/kid.pdf?signatur=abc"
