"""Adapter für EODHD — Tagesdaten, Splits, Dividenden.

Der Free-Plan hat zwei Eigenheiten, die beide still zu falschen Ergebnissen
führen, wenn man sie nicht abfängt:

**1. Stille Kürzung auf zwölf Monate.** Eine Anfrage ab Januar 2015 kommt mit
Daten ab September 2025 zurück — HTTP 200, keine Fehlermeldung. Der einzige
Hinweis steckt in einem ``warning``-Feld an jeder einzelnen Bar:

    "Data is limited by one year as you have free subscription"

Wer das nicht liest, hält einen Zehn-Jahres-Backtest für gültig, der auf zwölf
Monaten steht. Deshalb bricht ``EodhdClient`` bei diesem Feld **hart ab**,
statt zu warnen. Eine Warnung im Log übersieht man; eine Ausnahme nicht.

**2. Kein Intraday.** ``/api/intraday`` antwortet mit HTTP 403, „Only EOD data
allowed for free users". Der Client meldet das als eigene Ausnahme mit dem
Hinweis auf den Abo-Pfad, statt einen nackten HTTP-Fehler durchzureichen.

Zum ``available_at``-Feld: EODHD liefert Tagesdaten nach Börsenschluss, sagt
aber nicht, wann genau. Der Client setzt ``available_at`` deshalb bewusst
konservativ auf Börsenschluss plus einen Puffer (Vorgabe: 1 Stunde). Zu spät
anzusetzen kostet Signalqualität; zu früh erzeugt Look-ahead. Im Zweifel zu
spät — ein zu vorsichtiger Backtest ist unangenehm, ein zu optimistischer
ist wertlos.

Der Token kommt ausschließlich aus der Umgebung (``EODHD_API_TOKEN``),
niemals aus dem Code. Er liegt in ``~/claude-local/trading-app/.env``,
außerhalb von Git und iCloud.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from trading_app.bitemporal import Bar

__all__ = [
    "EodhdClient",
    "EodhdError",
    "FreiPlanGrenzeError",
    "IntradayNichtVerfuegbarError",
]

UTC = dt.timezone.utc
_BASIS_URL = "https://eodhd.com/api"

# Der Text, mit dem EODHD die stille Kürzung ankündigt.
_WARNUNG_JAHRESGRENZE = "limited by one year"


class EodhdError(RuntimeError):
    """Oberklasse aller EODHD-Fehler."""


class FreiPlanGrenzeError(EodhdError):
    """Die Antwort war still gekürzt.

    Ein eigener Typ, damit ein Aufrufer gezielt darauf reagieren kann —
    etwa das Ladefenster verkleinern — ohne echte Netzfehler mitzufangen.
    """


class IntradayNichtVerfuegbarError(EodhdError):
    """Intraday ist im Free-Plan gesperrt (HTTP 403)."""


class EodhdClient:
    """Dünner Adapter über die EODHD-REST-API.

    Beispiel:
        >>> client = EodhdClient()                     # Token aus der Umgebung
        >>> bars = client.tagesbars("AAPL.US",
        ...                         start=date(2026, 1, 1),
        ...                         end=date(2026, 3, 1))
        >>> store.append(bars)
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        verfuegbarkeits_puffer: dt.timedelta = dt.timedelta(hours=1),
    ) -> None:
        """
        Args:
            token: API-Token. Vorgabe: ``EODHD_API_TOKEN`` aus der Umgebung.
            timeout: Zeitlimit je Anfrage in Sekunden.
            verfuegbarkeits_puffer: Aufschlag auf den Börsenschluss für
                ``available_at``. Lieber zu groß als zu klein.

        Raises:
            EodhdError: Wenn kein Token zu finden ist.
        """
        self._token = token or os.environ.get("EODHD_API_TOKEN")
        if not self._token:
            raise EodhdError(
                "Kein API-Token. Entweder EODHD_API_TOKEN setzen oder token= übergeben.\n"
                "Laden mit: set -a && . ~/claude-local/trading-app/.env && set +a"
            )
        self._timeout = timeout
        self._puffer = verfuegbarkeits_puffer

    # -- Netzwerk ---------------------------------------------------------

    def _hole(self, pfad: str, **parameter: Any) -> Any:
        """Führt eine Anfrage aus und gibt die JSON-Antwort zurück.

        Raises:
            IntradayNichtVerfuegbarError: Bei HTTP 403 auf Intraday.
            EodhdError: Bei allen anderen HTTP- und Netzfehlern.
        """
        parameter = {"api_token": self._token, "fmt": "json", **parameter}
        url = f"{_BASIS_URL}/{pfad}?{urllib.parse.urlencode(parameter)}"

        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as antwort:
                rohdaten = antwort.read().decode("utf-8")
        except urllib.error.HTTPError as fehler:
            körper = fehler.read().decode("utf-8", errors="replace")[:200]
            if fehler.code == 403:
                raise IntradayNichtVerfuegbarError(
                    f"EODHD verweigert den Zugriff (HTTP 403): {körper}\n"
                    "Im Free-Plan sind nur EOD-Daten freigeschaltet. Intraday "
                    "erfordert ein Abo (~15 €/Monat mit Studentenrabatt) — und "
                    "dann zusätzlich ein eigenes Modul für die Split-Anpassung, "
                    "weil EODHD Intraday-Bars nicht rückwirkend bereinigt. "
                    "Siehe docs/20260925_rueckwirkende-anpassung.md."
                ) from fehler
            if fehler.code == 429:
                raise EodhdError(
                    f"Tageslimit erschöpft (HTTP 429): {körper}\n"
                    "Der Free-Plan erlaubt 20 Aufrufe pro Tag."
                ) from fehler
            # Token nie in die Meldung — die landet im Log.
            raise EodhdError(f"HTTP {fehler.code} bei /{pfad}: {körper}") from fehler
        except urllib.error.URLError as fehler:
            raise EodhdError(f"Netzwerkfehler bei /{pfad}: {fehler.reason}") from fehler

        try:
            return json.loads(rohdaten)
        except json.JSONDecodeError as fehler:
            raise EodhdError(f"Antwort war kein gültiges JSON: {rohdaten[:200]}") from fehler

    @staticmethod
    def _pruefe_jahresgrenze(zeilen: list[dict[str, Any]], symbol: str) -> None:
        """Bricht ab, wenn EODHD die Antwort still gekürzt hat.

        Absichtlich eine Ausnahme statt einer Log-Warnung: Die Kürzung ist
        genau die Sorte Fehler, die monatelang unbemerkt bleibt und jede
        darauf gebaute Auswertung entwertet.
        """
        for zeile in zeilen:
            warnung = zeile.get("warning")
            if warnung and _WARNUNG_JAHRESGRENZE in str(warnung).lower():
                raise FreiPlanGrenzeError(
                    f"EODHD hat die Antwort für {symbol} still gekürzt.\n"
                    f"Meldung des Anbieters: {warnung!r}\n"
                    "Der Free-Plan liefert maximal zwölf Monate — die Anfrage kam "
                    "mit HTTP 200 zurück, aber mit weniger Daten als verlangt. "
                    "Entweder das Ladefenster auf zwölf Monate verkleinern oder "
                    "die Historie aus einer anderen Quelle holen."
                )

    # -- Tagesbars --------------------------------------------------------

    def tagesbars(
        self,
        symbol: str,
        start: dt.date,
        end: dt.date,
        *,
        boersenschluss: dt.time = dt.time(22, 0),
    ) -> list[Bar]:
        """Lädt Tagesbars und gibt sie als geprüfte ``Bar``-Objekte zurück.

        Args:
            symbol: EODHD-Kürzel, z. B. ``AAPL.US`` oder ``SAP.XETRA``.
            start: Erster Handelstag (einschließlich).
            end: Letzter Handelstag (einschließlich).
            boersenschluss: Schlusszeit in UTC. Vorgabe 22:00 ≈ US-Schluss.
                Für Xetra 16:30 UTC setzen.

        Returns:
            Bars nach ``event_time`` aufsteigend, mit ``adjusted_close``.

        Raises:
            FreiPlanGrenzeError: Wenn die Antwort still gekürzt war.
            EodhdError: Bei HTTP- oder Netzfehlern.
        """
        if start > end:
            raise ValueError(f"start ({start}) liegt nach end ({end})")

        zeilen = self._hole(
            f"eod/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        if not isinstance(zeilen, list):
            raise EodhdError(f"Unerwartete Antwortform für {symbol}: {type(zeilen).__name__}")

        self._pruefe_jahresgrenze(zeilen, symbol)

        bars: list[Bar] = []
        for zeile in zeilen:
            tag = dt.date.fromisoformat(zeile["date"])
            ereignis = dt.datetime.combine(tag, boersenschluss, tzinfo=UTC)
            bars.append(
                Bar(
                    symbol=symbol,
                    bar_size="1d",
                    event_time=ereignis,
                    available_at=ereignis + self._puffer,
                    open=float(zeile["open"]),
                    high=float(zeile["high"]),
                    low=float(zeile["low"]),
                    close=float(zeile["close"]),
                    adjusted_close=(
                        float(zeile["adjusted_close"])
                        if zeile.get("adjusted_close") is not None
                        else None
                    ),
                    volume=float(zeile.get("volume") or 0.0),
                    source="eodhd",
                )
            )
        bars.sort(key=lambda b: b.event_time)
        return bars

    # -- Splits und Dividenden -------------------------------------------

    def splits(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        """Split-Historie als Liste von ``{date, split}``.

        ``split`` steht als Text da, etwa ``"4.000000/1.000000"`` für den
        AAPL-Split vom 31.08.2020.
        """
        zeilen = self._hole(
            f"splits/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        return zeilen if isinstance(zeilen, list) else []

    def dividenden(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        """Dividendenhistorie, einschließlich ``declarationDate``.

        Der Grund, warum EODHD trotz Free-Plan im Projekt bleibt: Das
        Ankündigungsdatum ist der korrekte ``available_at``-Zeitpunkt für
        jedes Dividendensignal. ``yfinance`` liefert es nicht, und ohne das
        Feld wird aus einer Dividendenstrategie unbemerkt Hellseherei.
        """
        zeilen = self._hole(
            f"div/{symbol}",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        return zeilen if isinstance(zeilen, list) else []

    def kontostand(self) -> dict[str, Any]:
        """Plan und Restkontingent. Kostet selbst einen Aufruf."""
        antwort = self._hole("user")
        return antwort if isinstance(antwort, dict) else {}
