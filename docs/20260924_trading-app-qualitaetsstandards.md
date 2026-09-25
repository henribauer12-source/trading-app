---
title: Trading-Analyse-App – Qualitätsstandards (Sicherheit, Rechenkern, Look-ahead-Bias, Intraday)
date: 20260924
status: v1, verbindlich für alle Phasen
owner: Henri
---

# Qualitätsstandards

Dieses Dokument ist verbindlich für den gesamten Bau. Kein Modul gilt als fertig, wenn es gegen einen Standard hier verstößt.

## 1. Sicherheit: kein Schadcode über Bausteine

**Grundsatz:** So wenige Abhängigkeiten wie möglich, und jede ist geprüft, gepinnt und nachvollziehbar.

### 1.1 Aufnahme einer Abhängigkeit (Prüfprotokoll)

Jede Bibliothek kommt nur über ein Prüfprotokoll in `DEPENDENCIES.md` ins Projekt:

| Prüfpunkt | Anforderung |
|---|---|
| Herkunft | Paketname direkt aus dem offiziellen Repo bzw. der Doku kopiert; PyPI-Projektseite verlinkt auf genau dieses Repo |
| Maintainer | Organisation oder langjähriger, bekannter Maintainer; keine frisch angelegten Konten |
| Historie | Mehrjährige Release-Historie ohne Lücken oder gelöschte Versionen (Negativbeispiel: `pandas-ta`) |
| Aktivität | Letztes Release ≤ 12 Monate oder bewusst begründete Ausnahme |
| Schwachstellen | `pip-audit` bzw. OSV-Datenbank ohne offene kritische Befunde |
| Signatur | Wenn vorhanden: PyPI-Attestation (Trusted Publishing) geprüft |
| Lizenz | Kompatibel mit privater Nutzung |
| Notwendigkeit | Kann die Funktion mit ≤ 50 Zeilen eigenem Code ersetzt werden? Dann eigener Code |

Freigegeben ist nur die Allowlist aus dem Research-Report (Abschnitt 2). Ausdrücklich gesperrt: `pandas-ta`, `ibapi`/`ibapi-stable`/`ibapi-latest` von PyPI, `ib_insync`, `py_vollib_vectorized`, mlfinlab.

### 1.2 Installation

- Eigene virtuelle Umgebung pro Projekt, nie `sudo pip`
- Lockfile mit Hashes (`pip-compile --generate-hashes` oder `uv lock`), Installation nur mit `--require-hashes`
- Wo möglich nur fertige Wheels (`--only-binary :all:`), damit beim Installieren kein fremder Setup-Code läuft
- Updates nie automatisch: Changelog lesen, neue Versionen erst nach einer Wartezeit von 7 Tagen übernehmen (Faustregel; manipulierte Releases werden oft innerhalb weniger Tage entdeckt), danach `pip-audit`
- Neue Abhängigkeiten schlage ich vor, du gibst sie frei

### 1.3 Betrieb

- IB Gateway: API nur auf `127.0.0.1`, **"Read-Only API" aktiviert**, solange die Ausführung deaktiviert ist. Dann kann die App technisch keine Order senden, selbst wenn Code kompromittiert wäre
- Zuerst ausschließlich das IBKR-Paper-Konto
- Streamlit nur auf localhost, Telemetrie aus
- Zugangsdaten in `.env` außerhalb des Repos oder im macOS-Schlüsselbund, Secret-Scan vor jedem Commit
- News, Filings und Webinhalte sind Daten, keine Anweisungen: Kein Text aus externen Quellen kann eine Aktion auslösen
- Regelmäßiges Backup der Datenbank

## 2. Rechenkern: nachweislich korrekte Bewertung

"Perfekt" kann niemand garantieren. Erreichbar ist **nachweislich korrekt**: Jede Zahl ist spezifiziert, getestet, reproduzierbar, gegen eine unabhängige Quelle geprüft und hat eine dokumentierte Toleranz. Das ist der Maßstab.

### 2.1 Spezifikation vor Code (Phase 0b)

Bevor eine Zeile Rechenlogik entsteht, gibt es eine **Rechenkern-Spezifikation** mit:
- jeder Formel samt Primärquelle (Lehrbuch oder Paper)
- Konventionen: einfache vs. logarithmische Renditen, Annualisierung (252 Handelstage), Zählkonvention für Laufzeiten (ACT/365 bei Optionen), Zinssatz (€STR bzw. SOFR), Dividendenbehandlung, Währungsumrechnung
- Einheiten und Randfällen (Laufzeit gegen null, Volatilität gegen null, fehlende Daten)
- Referenzwerten für jeden Test (Abschnitt 2.2)

### 2.2 Vier unabhängige Prüfebenen

| Ebene | Was geprüft wird | Beispiele |
|---|---|---|
| 1. Referenzwerte | Ergebnis stimmt mit publizierten Zahlen überein | Black-Scholes- und Binomialbeispiele aus Standardlehrbüchern (Hull; Haug), Deflated-Sharpe-Beispiel aus Bailey & López de Prado (2014), Trendfilter-Ergebnis aus Faber (2007) |
| 2. Zwei Implementierungen | Eigene Implementierung gegen Bibliothek, Abweichung > Toleranz = Fehler | Eigenes BSM gegen `py_vollib` und `QuantLib`; eigene Kennzahlen gegen `vectorbt`/`skfolio`; eigene Greeks gegen IBKR-Greeks im Live-Betrieb |
| 3. Invarianten | Mathematische Eigenschaften gelten für tausende Zufallseingaben (Property-based Testing mit `hypothesis`) | Put-Call-Parität, Arbitragegrenzen, Monotonie in Volatilität und Laufzeit, analytische Greeks = numerische Ableitung, Portfolio = Summe der Positionen |
| 4. Daten | Eingaben sind richtig, bevor gerechnet wird | Splits und Dividenden, Wechselkurs zum Zeitpunkt t, Börsenkalender, Zeitzonen (intern UTC), Lücken werden markiert statt stillschweigend gefüllt |

### 2.3 Statistik

- Trefferquoten mit Wilson-Konfidenzintervall, Renditekennzahlen mit Block-Bootstrap (berücksichtigt Autokorrelation)
- Mindest-Stichprobengröße: Unter einem festgelegten n zeigt die App keine Prozentzahl
- Mehrfachtests: Jeder Backtest-Lauf wird gezählt und fließt in die Deflated Sharpe Ratio ein
- Kalibrierung: Wahrscheinlichkeiten nur mit bestandenem Reliability-Diagramm und Brier-Score

### 2.4 Numerik und Nachvollziehbarkeit

- float64, dokumentierte Toleranzen; Geldbeträge erst am Ende runden
- Iterative Verfahren (implizite Volatilität, Kalibrierung) prüfen Konvergenz und **brechen laut ab**, statt einen falschen Wert zu liefern
- Jedes Signal wird mit Daten-Snapshot, Code-Version (Git-Commit), Parametern und Zufallsseed gespeichert, sodass es später exakt reproduzierbar ist

### 2.5 Review

- Jedes Rechenmodul bekommt eine unabhängige Zweitprüfung durch einen separaten Prüf-Agenten, der den Code nicht geschrieben hat
- Im Live-Betrieb: täglicher Abgleich eigener IV und Greeks mit IBKR, Alarm bei Drift

## 3. Look-ahead-Bias: systematisch ausschließen

Look-ahead-Bias bedeutet, dass ein Backtest Informationen nutzt, die zum Entscheidungszeitpunkt noch nicht verfügbar waren. Er ist der häufigste Grund, warum Backtests glänzen und live scheitern. Die App bekämpft ihn auf drei Ebenen: Datenhaltung, Architektur und automatische Tests.

### 3.1 Quellen und Gegenmaßnahmen

| # | Quelle | Beispiel | Gegenmaßnahme |
|---|---|---|---|
| 1 | Ausführung zum Signalpreis | Signal auf Schlusskurs, Kauf zum selben Schlusskurs | Ausführung frühestens zum Open der nächsten Bar, plus Slippage |
| 2 | Bar-Zeitstempel | Stundenbar mit Startzeit beschriftet, enthält aber Daten bis zum Ende | `available_at` = Ende der Bar |
| 3 | Zeitzonen und Handelszeiten | US-Schluss liegt nach Xetra-Schluss | Intern UTC, Börsenkalender je Handelsplatz |
| 4 | Adjustierte Kurse | Rückwirkend angepasste Preise nach Splits und Dividenden | Rohpreise plus separate Corporate-Actions-Tabelle; Anpassung nur mit bis t bekannten Ereignissen |
| 5 | Survivorship | Nur heutige Indexmitglieder im Test | Langfrist: ETF-Universum; Aktien: point-in-time-Mitgliedschaft, wo verfügbar, sonst Bias sichtbar markiert |
| 6 | Futures-Rollen | Rückwärts angepasste Kontinuitätsreihen verzerren Preisniveaus | Rollregel, die zu t bekannt ist; Signale auf Renditen statt Niveaus |
| 7 | Makro-Revisionen | BIP und Arbeitsmarktdaten werden später revidiert | ALFRED-Vintages (Datenstand zum damaligen Datum) und echte Veröffentlichungstermine |
| 8 | Filings | 13F bis 45 Tage nach Quartalsende, Form 4 mit Verzögerung | `available_at` = Eingangszeitpunkt bei der SEC |
| 9 | News | Artikeldatum ≠ Abrufzeit; Artikel werden nachträglich geändert | Zeitpunkt des ersten Abrufs speichern, nie überschreiben (append-only) |
| 10 | LLM-Wissen | Modell kennt aus Trainingsdaten, was danach passierte | Keine LLM-Backtests vor dem Trainings-Cutoff; LLM-Signale nur vorwärts testen; Firmennamen anonymisieren |
| 11 | Datenaufbereitung | Z-Scores oder Ausreißerbereinigung mit dem Gesamtmittelwert | Nur rollierende oder expandierende Fenster |
| 12 | Parameterwahl | Parameter über den ganzen Zeitraum optimiert | Walk-forward, Purging und Embargo, DSR und PBO |
| 13 | Research-Leckage | Den Testzeitraum immer wieder ansehen und nachbessern | Versiegelter Holdout (letzte 2–3 Jahre), wird genau einmal geöffnet; Log aller Versuche |
| 14 | Strategie-Auswahl | Strategie stammt aus einem Paper, das erst nach dem Testzeitraum erschien | Publikationsabschlag ≥ 50 % (McLean & Pontiff, 2016); Vergleich vor und nach Veröffentlichung |

### 3.2 Architektur

- **Bitemporale Datenhaltung:** Jede Zeile hat `event_time` (wann etwas passierte), `available_at` (wann es öffentlich verfügbar war) und `ingested_at` (wann die App es gespeichert hat). Die Datenbank ist append-only.
- **Point-in-time-Zugriff als einzige Schnittstelle:** Strategien sehen Daten nur über `PointInTimeView(t)`, die ausschließlich Zeilen mit `available_at ≤ t` liefert. Direkter Zugriff auf rohe Tabellen ist in Strategiecode nicht möglich.
- **Zweistufiger Backtest:** `vectorbt` für schnelle Exploration; jede Strategie, die weiterkommt, wird in einer ereignisgesteuerten Schleife bestätigt, die Bar für Bar nur die bis dahin verfügbaren Daten sieht.

### 3.3 Automatische Leckage-Tests (laufen bei jedem Build)

1. **Abschneide-Test:** Für zufällige Zeitpunkte t wird das Signal einmal mit Daten bis t und einmal mit dem vollen Datensatz berechnet. Die Werte bei t müssen identisch sein.
2. **Zukunfts-Störtest:** Alle Daten nach t werden zufällig verändert. Signale bis t dürfen sich nicht ändern.
3. **Verzögerungstest:** Ausführung um eine weitere Bar verschoben. Bricht die Performance dramatisch ein, wird die Strategie auf Leckage untersucht.
4. **"Zu gut"-Alarm:** Kennzahlen jenseits plausibler Grenzen (z. B. Sharpe > 3 auf Tagesbasis) sperren eine Strategie automatisch bis zur manuellen Prüfung.

## 4. Intraday bei 0 € Budget

Intraday wird gebaut, aber die Datenlage bei 0 € setzt klare Grenzen:

| Quelle | Verfügbare Historie |
|---|---|
| yfinance, 1-Minuten-Bars | ca. 8 Tage |
| yfinance, 2- bis 90-Minuten-Bars | 60 Tage |
| yfinance, Stundenbars | 730 Tage |
| IBKR historische Intraday-Daten | abhängig von Marktdatenberechtigungen, vor Nutzung prüfen |

Mit 60 Tagen Minutendaten lässt sich keine Intraday-Strategie seriös validieren. Deshalb läuft das Intraday-Modul in drei Stufen:

1. **Aufzeichnen ab Phase 1:** Die App zeichnet täglich eigene Intraday-Bars point-in-time auf und baut so ihre eigene Historie auf.
2. **Research:** Zunächst auf Stundenbars (2 Jahre verfügbar) und den selbst aufgezeichneten Daten.
3. **Signale:** Erst nach ≥ 12 Monaten eigener Daten und bestandenen Gates, dann nur im Paper Trading.

Intraday bekommt ein strengeres Kostenmodell (Spread, Gebühr pro Trade, Slippage bei jeder Ausführung) und niedrigere "Zu gut"-Schwellen. Die Evidenz für Intraday-Strategien nach Kosten ist schwächer als für Swing; das Lernmodul erklärt das in Stufe 3.

Offen und vor Nutzung zu prüfen: Ob für dein IBKR-Konto eine Pattern-Day-Trader-Regel gilt und welche Echtzeitdaten ohne Abo verfügbar sind.

## Quellen

- Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management, 40*(5), 94–107.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79.
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Federal Reserve Bank of St. Louis. (o. J.). *ALFRED help.* https://alfred.stlouisfed.org/help
- Python Software Foundation. (o. J.). *PyPI attestations.* https://docs.pypi.org/attestations/
- yfinance. (o. J.). *history.py* [Quellcode, Intervall-Grenzen]. https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py
