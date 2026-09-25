"""Tests des EODHD-Adapters.

Ohne Netz. Die Antworten stammen aus echten Abrufen vom 25.09.2026 — die
Zahlen sind real gemessen, nur eingefroren. Ein Test, der ans Netz geht,
verbraucht vom Tageskontingent (20 Aufrufe) und wird rot, wenn der Anbieter
Schluckauf hat.

Der wichtigste Test ist ``test_stille_kuerzung_bricht_hart_ab``: Er hält die
Eigenschaft fest, dass HTTP 200 mit gekürzten Daten als Fehler gilt.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import urllib.error
from typing import Any

import pytest

from trading_app.bitemporal import BitemporalStore
from trading_app.sources.eodhd import (
    EodhdClient,
    EodhdError,
    FreiPlanGrenzeError,
    IntradayNichtVerfuegbarError,
)

UTC = dt.timezone.utc

# Echte Antwort von /api/eod/AAPL.US, Abruf 2026-09-25.
ECHTE_BARS = [
    {
        "date": "2026-09-22", "open": 331.5, "high": 336.28, "low": 330.91,
        "close": 335.5, "adjusted_close": 335.5, "volume": 44163300,
    },
    {
        "date": "2026-09-23", "open": 336.0, "high": 338.19, "low": 333.62,
        "close": 334.15, "adjusted_close": 334.15, "volume": 38102500,
    },
    {
        "date": "2026-09-24", "open": 334.4, "high": 337.92, "low": 333.35,
        "close": 335.92, "adjusted_close": 335.92, "volume": 35217600,
    },
]

# Dieselbe Antwort, wie sie kommt, wenn die Anfrage über zwölf Monate
# zurückreicht: HTTP 200, weniger Daten, Hinweis nur im warning-Feld.
GEKUERZTE_BARS = [
    {**zeile, "warning": "Data is limited by one year as you have free subscription"}
    for zeile in ECHTE_BARS
]


class FakeAntwort(io.BytesIO):
    """Minimales Gegenstück zu dem, was urlopen als Kontextmanager liefert."""

    def __enter__(self) -> FakeAntwort:
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.fixture
def fake_netz(monkeypatch):
    """Ersetzt urlopen. Gibt einen Rekorder der aufgerufenen URLs zurück."""
    aufrufe: list[str] = []

    def setze(nutzlast: Any = None, *, http_fehler: int | None = None, körper: str = ""):
        def gefälscht(url, timeout=None):  # noqa: ARG001
            aufrufe.append(url)
            if http_fehler is not None:
                raise urllib.error.HTTPError(
                    url, http_fehler, körper, {}, io.BytesIO(körper.encode())
                )
            return FakeAntwort(json.dumps(nutzlast).encode())

        monkeypatch.setattr("urllib.request.urlopen", gefälscht)
        return aufrufe

    return setze


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "test-token-nicht-echt")
    return EodhdClient()


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class TestToken:
    def test_token_kommt_aus_der_umgebung(self, monkeypatch) -> None:
        monkeypatch.setenv("EODHD_API_TOKEN", "aus-der-umgebung")
        assert EodhdClient()._token == "aus-der-umgebung"

    def test_ohne_token_klare_meldung(self, monkeypatch) -> None:
        monkeypatch.delenv("EODHD_API_TOKEN", raising=False)
        with pytest.raises(EodhdError, match="Kein API-Token"):
            EodhdClient()

    def test_token_steht_nie_in_einer_fehlermeldung(self, monkeypatch, fake_netz) -> None:
        """Fehlermeldungen landen im Log. Der Token darf da nicht auftauchen."""
        monkeypatch.setenv("EODHD_API_TOKEN", "geheim-abc123")
        fake_netz(http_fehler=500, körper="Internal Server Error")
        with pytest.raises(EodhdError) as fehler:
            EodhdClient().tagesbars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))
        assert "geheim-abc123" not in str(fehler.value)


# ---------------------------------------------------------------------------
# Die stille Kürzung — der wichtigste Test dieser Datei
# ---------------------------------------------------------------------------


class TestJahresgrenze:
    def test_stille_kuerzung_bricht_hart_ab(self, client, fake_netz) -> None:
        """HTTP 200 mit gekürzten Daten muss ein Fehler sein, keine Warnung.

        Eine Warnung im Log übersieht man ein halbes Jahr lang. Bis dahin
        stehen alle Auswertungen auf zwölf statt zehn Jahren Daten.
        """
        fake_netz(GEKUERZTE_BARS)
        with pytest.raises(FreiPlanGrenzeError, match="still gekürzt"):
            client.tagesbars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))

    def test_fehlermeldung_nennt_anbietertext_und_ausweg(self, client, fake_netz) -> None:
        fake_netz(GEKUERZTE_BARS)
        with pytest.raises(FreiPlanGrenzeError) as fehler:
            client.tagesbars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))
        text = str(fehler.value)
        assert "limited by one year" in text   # Originaltext des Anbieters
        assert "zwölf Monate" in text          # was zu tun ist

    def test_warnung_an_irgendeiner_bar_reicht(self, client, fake_netz) -> None:
        """EODHD hängt das Feld pro Bar an — eine einzige muss genügen."""
        gemischt = [dict(ECHTE_BARS[0]), dict(ECHTE_BARS[1]), dict(GEKUERZTE_BARS[2])]
        fake_netz(gemischt)
        with pytest.raises(FreiPlanGrenzeError):
            client.tagesbars("AAPL.US", dt.date(2015, 1, 1), dt.date(2026, 9, 24))

    def test_ohne_warnung_laeuft_alles_durch(self, client, fake_netz) -> None:
        """Bei genau zwölf Monaten fehlt das Feld — gemessen am 25.09.2026."""
        fake_netz(ECHTE_BARS)
        bars = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        assert len(bars) == 3


# ---------------------------------------------------------------------------
# Intraday
# ---------------------------------------------------------------------------


class TestIntradayGesperrt:
    def test_http_403_wird_zu_klarer_ausnahme(self, client, fake_netz) -> None:
        fake_netz(http_fehler=403, körper="Only EOD data allowed for free users")
        with pytest.raises(IntradayNichtVerfuegbarError) as fehler:
            client.tagesbars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))
        text = str(fehler.value)
        assert "Free-Plan" in text
        assert "rückwirkend" in text  # Hinweis auf die Falle beim Upgrade

    def test_429_nennt_das_tageslimit(self, client, fake_netz) -> None:
        fake_netz(http_fehler=429, körper="Too many requests")
        with pytest.raises(EodhdError, match="20 Aufrufe"):
            client.tagesbars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))


# ---------------------------------------------------------------------------
# Umwandlung in Bar-Objekte
# ---------------------------------------------------------------------------


class TestUmwandlung:
    def test_felder_landen_richtig(self, client, fake_netz) -> None:
        fake_netz(ECHTE_BARS)
        bars = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        erste = bars[0]
        assert erste.symbol == "AAPL.US"
        assert erste.bar_size == "1d"
        assert erste.close == 335.5
        assert erste.adjusted_close == 335.5
        assert erste.volume == 44163300
        assert erste.source == "eodhd"

    def test_available_at_liegt_nach_boersenschluss(self, client, fake_netz) -> None:
        """Im Zweifel zu spät: zu früh wäre Look-ahead."""
        fake_netz(ECHTE_BARS)
        bar = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))[0]
        assert bar.available_at > bar.event_time
        assert bar.available_at - bar.event_time == dt.timedelta(hours=1)

    def test_puffer_ist_einstellbar(self, monkeypatch, fake_netz) -> None:
        monkeypatch.setenv("EODHD_API_TOKEN", "test")
        fake_netz(ECHTE_BARS)
        client = EodhdClient(verfuegbarkeits_puffer=dt.timedelta(hours=6))
        bar = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))[0]
        assert bar.available_at - bar.event_time == dt.timedelta(hours=6)

    def test_boersenschluss_fuer_xetra(self, client, fake_netz) -> None:
        fake_netz(ECHTE_BARS)
        bar = client.tagesbars(
            "SAP.XETRA", dt.date(2026, 9, 22), dt.date(2026, 9, 24),
            boersenschluss=dt.time(16, 30),
        )[0]
        assert bar.event_time.hour == 16 and bar.event_time.minute == 30

    def test_bars_kommen_sortiert(self, client, fake_netz) -> None:
        fake_netz(list(reversed(ECHTE_BARS)))
        bars = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))
        assert [b.event_time for b in bars] == sorted(b.event_time for b in bars)

    def test_fehlendes_adjusted_close_wird_zu_none(self, client, fake_netz) -> None:
        ohne = [{k: v for k, v in ECHTE_BARS[0].items() if k != "adjusted_close"}]
        fake_netz(ohne)
        bar = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 22))[0]
        assert bar.adjusted_close is None

    def test_start_nach_end_wird_abgelehnt(self, client) -> None:
        with pytest.raises(ValueError, match="liegt nach"):
            client.tagesbars("AAPL.US", dt.date(2026, 3, 1), dt.date(2026, 1, 1))

    def test_kaputtes_json_wird_gemeldet(self, client, monkeypatch) -> None:
        def kaputt(url, timeout=None):  # noqa: ARG001
            return FakeAntwort(b"<html>Wartungsarbeiten</html>")
        monkeypatch.setattr("urllib.request.urlopen", kaputt)
        with pytest.raises(EodhdError, match="kein gültiges JSON"):
            client.tagesbars("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 1, 31))


# ---------------------------------------------------------------------------
# Splits und Dividenden
# ---------------------------------------------------------------------------


class TestSplitsUndDividenden:
    def test_splits(self, client, fake_netz) -> None:
        """Echte Antwort vom 25.09.2026."""
        fake_netz([
            {"date": "2014-06-09", "split": "7.000000/1.000000"},
            {"date": "2020-08-31", "split": "4.000000/1.000000"},
        ])
        splits = client.splits("AAPL.US", dt.date(2010, 1, 1), dt.date(2026, 9, 25))
        assert len(splits) == 2
        assert splits[1]["split"] == "4.000000/1.000000"

    def test_dividenden_tragen_declarationdate(self, client, fake_netz) -> None:
        """Der eigentliche Wert des Free-Tokens: der korrekte available_at."""
        fake_netz([{
            "date": "2026-08-10", "declarationDate": "2026-07-31",
            "recordDate": "2026-08-11", "paymentDate": "2026-08-14",
            "value": 0.27, "unadjustedValue": 0.27, "currency": "USD",
        }])
        div = client.dividenden("AAPL.US", dt.date(2026, 1, 1), dt.date(2026, 9, 25))
        assert div[0]["declarationDate"] == "2026-07-31"
        # Ankündigung liegt vor dem Ex-Tag — sonst wäre available_at falsch.
        assert div[0]["declarationDate"] < div[0]["date"]


# ---------------------------------------------------------------------------
# Zusammenspiel mit der Datenschicht
# ---------------------------------------------------------------------------


class TestZusammenspiel:
    def test_geladene_bars_landen_im_store(self, client, fake_netz) -> None:
        fake_netz(ECHTE_BARS)
        bars = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))

        with BitemporalStore(":memory:") as store:
            assert store.append(bars) == 3
            sicht = store.view(dt.datetime(2026, 9, 25, tzinfo=UTC))
            frame = sicht.bars("AAPL.US")
            assert len(frame) == 3
            assert frame.iloc[-1]["close"] == 335.92

    def test_pit_sperre_greift_auch_bei_echten_daten(self, client, fake_netz) -> None:
        """Stichtag 23.09. 22:30 — die Bar vom 23. ist erst 23:00 verfügbar."""
        fake_netz(ECHTE_BARS)
        bars = client.tagesbars("AAPL.US", dt.date(2026, 9, 22), dt.date(2026, 9, 24))

        with BitemporalStore(":memory:") as store:
            store.append(bars)
            sicht = store.view(dt.datetime(2026, 9, 23, 22, 30, tzinfo=UTC))
            frame = sicht.bars("AAPL.US")
            assert len(frame) == 1
            assert frame.iloc[0]["close"] == 335.5  # nur der 22.
