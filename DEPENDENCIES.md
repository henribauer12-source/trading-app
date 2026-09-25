# Prüfprotokoll Abhängigkeiten

Verbindliche Grundlage: `docs/20260924_trading-app-qualitaetsstandards.md`, Abschnitt 1.1.
Jede Bibliothek kommt nur über dieses Protokoll ins Projekt. Ohne Eintrag hier wird nichts installiert.

**Stand der Prüfung:** 2026-09-25
**Geprüft von:** automatisiert gegen PyPI JSON-API, PyPI Simple-API (PEP 691, Feld `provenance`) und OSV-Datenbank (api.osv.dev). Nichts wurde installiert.
**Freigabe:** offen — Henri gibt Charge 1 frei oder lehnt einzelne Pakete ab.

## Bewertungsmaßstab

| Prüfpunkt | Anforderung | Wie hier geprüft |
|---|---|---|
| Herkunft | PyPI-Projektseite verlinkt auf genau das offizielle Repo | `project_urls.source` / `.repository` aus der PyPI-JSON-API gelesen, nicht getippt |
| Maintainer | Organisation oder langjähriger, bekannter Maintainer | Repo-Eigentümer aus derselben URL |
| Historie | Mehrjährige Release-Historie ohne Lücken oder gelöschte Versionen | Anzahl Releases mit Dateien + Datum des ersten Release |
| Aktivität | Letztes Release ≤ 12 Monate | Upload-Datum der neuesten Version |
| Schwachstellen | OSV ohne offene kritische Befunde | `POST api.osv.dev/v1/query` je Paket und exakter Version |
| Signatur | PyPI-Attestation (Trusted Publishing), wenn vorhanden | Feld `provenance` in der Simple-API, gezählt über die Dateien der exakten Version |
| Lizenz | Kompatibel mit privater Nutzung | `license_expression`, sonst Trove-Classifier |
| Notwendigkeit | Mit ≤ 50 Zeilen eigenem Code ersetzbar? Dann eigener Code | Begründung je Paket unten |

**Fehlende Attestation ist kein Ausschlussgrund** (Trusted Publishing ist erst seit 2024 verbreitet), sondern senkt die Stufe von „signiert" auf „unsigniert, dafür Hash-gepinnt".

## Charge 1 — Phase 1 (Fundament)

Nur Pakete, die Phase 1 wirklich braucht: bitemporale Datenschicht, `PointInTimeView`, Instrument-Modell, DuckDB, Leckage-Tests, Intraday-Recorder.

| Paket | Version | Lizenz | Releases | Erstes | Letztes | OSV | Attestation |
|---|---|---|---|---|---|---|---|
| `duckdb` | 1.5.5 | MIT | 141 | 2019-05-08 | 2026-09-23 | keine Befunde | 34/34 Dateien |
| `pandas` | 3.0.6 | BSD-3-Clause | 118 | 2009-12-25 | 2026-09-17 | keine Befunde | 57/57 Dateien |
| `numpy` | 2.5.3 | BSD-3-Clause u. a. | 137 | 2006-12-02 | 2026-09-06 | keine Befunde | 65/65 Dateien |
| `pyarrow` | 25.0.1 | Apache-2.0 | 64 | 2017-03-16 | 2026-08-10 | keine Befunde | 0/42 Dateien |
| `pydantic` | 2.13.5 | MIT | 206 | 2017-05-03 | 2026-09-09 | keine Befunde | 1/1 Datei |
| `exchange-calendars` | 4.13.2 | Apache-2.0 | 48 | 2021-02-02 | 2026-03-10 | keine Befunde | 0/1 Datei |
| `pytest` | 9.1.1 | MIT | 192 | 2010-11-25 | 2026-06-19 | keine Befunde | 1/1 Datei |
| `hypothesis` | 6.168.1 | MPL-2.0 | 1569 | 2013-03-10 | 2026-09-23 | keine Befunde | 0/84 Dateien |
| `apscheduler` | 3.11.3 | MIT | 59 | 2009-08-01 | 2026-06-28 | keine Befunde | 1/1 Datei |
| `yfinance` | 1.7.0 | Apache-2.0 | 150 | 2019-05-26 | 2026-08-26 | keine Befunde | 0/1 Datei |

### Einzelbewertung

**`duckdb` 1.5.5** — Repo `github.com/duckdb/duckdb-python`, Organisation DuckDB Labs. Sieben Jahre Historie, Release vor zwei Tagen, alle 34 Wheels der Version tragen eine PyPI-Attestation. Analytische Engine für die bitemporale Schicht; nicht ersetzbar.
**Bewertung: freigegeben.**

**`pandas` 3.0.6** — Repo `github.com/pandas-dev/pandas`, Organisation pandas-dev. Seit 2009, vollständig attestiert. Basis für Zeitreihen und den `PointInTimeView`-Adapter.
**Bewertung: freigegeben.**

**`numpy` 2.5.3** — Repo `github.com/numpy/numpy`. Seit 2006, vollständig attestiert. Transitiv ohnehin durch pandas gezogen; hier explizit gepinnt.
**Bewertung: freigegeben.**

**`pyarrow` 25.0.1** — Repo `github.com/apache/arrow`, Apache Software Foundation. Keine Attestation (ASF baut außerhalb von PyPI Trusted Publishing), dafür Release-Signaturen im ASF-Prozess und neun Jahre lückenlose Historie. Parquet-Speicher für Intraday-Aufzeichnungen und DuckDB-Austausch.
**Bewertung: freigegeben, Stufe „unsigniert, Hash-gepinnt".**

**`pydantic` 2.13.5** — Repo `github.com/pydantic/pydantic`, Organisation Pydantic. Validierung des Instrument-Modells und der Datenverträge an den Rändern. Alternative wäre handgeschriebene Validierung, die deutlich über 50 Zeilen läge.
**Bewertung: freigegeben.**

**`exchange-calendars` 4.13.2** — Repo `github.com/gerrymanoim/exchange_calendars`, Einzel-Maintainer Gerry Manoim, hervorgegangen aus Quantopians `trading_calendars`. Letztes Release 2026-03-10, innerhalb der 12-Monats-Grenze. **Risiko: Einzel-Maintainer** — gleiche Klasse wie `edgartools` im Research-Report. Börsenkalender inklusive Feiertagen, Halbtagen und historischen Änderungen selbst zu pflegen ist ein Vielfaches von 50 Zeilen und genau die Sorte Detail, die Leckage-Tests stillschweigend falsch macht.
**Bewertung: freigegeben mit Auflage** — Kalenderausgaben für die tatsächlich genutzten Börsen gegen eine zweite Quelle gegenprüfen (Prüfebene 2 aus Qualitätsstandards 2.2), und die Version einfrieren, bis ein Gegentest vorliegt.

**`pytest` 9.1.1** — Repo `github.com/pytest-dev/pytest`, Organisation pytest-dev. Testinfrastruktur, ohne die es keine Prüfebenen gibt.
**Bewertung: freigegeben.**

**`hypothesis` 6.168.1** — Repo `github.com/HypothesisWorks/hypothesis`, Organisation HypothesisWorks. Keine Attestation, dafür 1569 Releases seit 2013 und Release vor zwei Tagen. Property-based Testing ist in den Qualitätsstandards als Prüfebene 3 fest vorgeschrieben (Put-Call-Parität, Monotonie, Arbitragegrenzen).
**Bewertung: freigegeben, Stufe „unsigniert, Hash-gepinnt".**

**`apscheduler` 3.11.3** — Repo `github.com/agronholm/apscheduler`, Maintainer Alex Grönholm, seit 2009. **Version 3.x ist Pflicht**, 4.x ist Alpha und laut Research-Report gesperrt. Treibt den Intraday-Recorder und die Ingest-Jobs.
**Bewertung: freigegeben, hart auf `>=3.11.3,<4` gepinnt.**

**`yfinance` 1.7.0** — Repo `github.com/ranaroussi/yfinance`, Maintainer Ran Aroussi. Apache-2.0, keine OSV-Befunde. **Zwei Auflagen:** nur als gecachter Fallback nach Research-Report Abschnitt 2, und der Paketname wird kopiert, nie getippt (`yfinnace` war Malware). Das README erlaubt ausdrücklich nur private Nutzung — passt, ist aber der Grund, warum das Repo privat bleibt.
**Bewertung: freigegeben mit Auflagen.**

### Nicht in Charge 1

Bewusst zurückgestellt, kommen mit ihrer Phase durch ein eigenes Protokoll:

| Paket | Phase | Grund der Zurückstellung |
|---|---|---|
| `polars` | – | Überschneidet sich mit pandas + DuckDB. Kein zweites DataFrame-Framework ohne belegten Engpass. |
| `pandas-market-calendars` | – | Direkte Alternative zu `exchange-calendars`. Nur eine Kalenderbibliothek, sonst zwei Wahrheiten. |
| `vectorbt`, `bt` | 2 | Backtest-Engine |
| `skfolio` | 3 | Validierung und Portfolio |
| `py_vollib`, `QuantLib` | 6 | Optionsbewertung |
| `TA-Lib` | 2 | Indikatoren |
| `edgartools`, `fredapi`, `sdmx1` | 4 | Filings und Makro |
| `transformers`, FinBERT | 4 | News und Sentiment |
| `streamlit`, `plotly` | 5 | Dashboard |
| `ib_async` | 7 | Broker, erst nach Paper-Trading-Entscheidung |

### Dauerhaft gesperrt

Aus Research-Report Abschnitt 2 und Qualitätsstandards 1.1. Diese Liste ist nicht verhandelbar:

| Paket | Grund |
|---|---|
| `pandas-ta` | Original-Repo gelöscht, PyPI-Historie bereinigt, keine Lizenz in den Metadaten |
| `ibapi`, `ibapi-stable`, `ibapi-latest` (PyPI) | Geben sich als IBKR aus, Platzhalter-Repo. Offizielle API nur von der IBKR-Website |
| `ib_insync` | Eingefroren, Nachfolger ist `ib_async` |
| `py_vollib_vectorized` | Seit 2021 verwaist |
| `mlfinlab` | Proprietär |
| `pypbo` | AGPL, veraltet |
| `NewsAPI` (Free) | Produktive Nutzung nicht erlaubt |

## Installationsregeln

Gelten für jede Charge, ohne Ausnahme:

1. Eigene virtuelle Umgebung, nie `sudo pip`.
2. Lockfile mit Hashes: `uv lock` oder `pip-compile --generate-hashes`.
3. Installation nur mit `--require-hashes`, wo möglich `--only-binary :all:` — dann läuft beim Installieren kein fremder Setup-Code.
4. Paketnamen aus dieser Datei kopieren, nie tippen.
5. Updates nie automatisch: Changelog lesen, 7 Tage Wartezeit, dann `pip-audit`, dann Eintrag hier aktualisieren.
6. Neue Abhängigkeiten schlage ich vor, Henri gibt sie frei.

## Reproduzierbarkeit

Die Prüfung ist als Skript wiederholbar und soll vor jeder neuen Charge und vor jedem Versionssprung erneut laufen:

- PyPI-Metadaten: `GET https://pypi.org/pypi/{paket}/json`
- Attestation: `GET https://pypi.org/simple/{paket}/` mit `Accept: application/vnd.pypi.simple.v1+json`, Feld `provenance` je Datei
- Schwachstellen: `POST https://api.osv.dev/v1/query` mit `{"version": "...", "package": {"name": "...", "ecosystem": "PyPI"}}`

Ein Ergebnis gilt nur für die exakt geprüfte Version. Version geändert = Protokoll neu.

## Vollzug Charge 1 — 2026-09-25

Freigabe erteilt. Umgesetzt und gemessen, nicht angenommen.

### Was installiert wurde

`pyproject.toml` deklariert exakt die 10 freigegebenen Pakete. `uv.lock` löst daraus **44 Pakete** auf: 10 direkte, 33 transitive, plus das Projekt selbst.

Die 33 transitiven Pakete standen in keiner Freigabe — das ist der übliche blinde Fleck eines Prüfprotokolls. Deshalb nachgeholt:

**OSV-Abfrage über alle 43 Fremdpakete: null Befunde.**

Die Kette, die am meisten mitbringt, ist `yfinance` (13 direkte Abhängigkeiten, darunter `curl-cffi`, `protobuf`, `peewee`, `lxml`). Das bestätigt die Einstufung als Fallback: Ein Paket, das ein Viertel des Abhängigkeitsbaums stellt, gehört nicht auf den kritischen Pfad.

### Installationsregeln in Konfiguration übersetzt

| Regel | Umsetzung | Nachweis |
|---|---|---|
| Kein `sudo pip` | Venv unter `~/claude-local/trading-app/.venv` | `sys.prefix` bestätigt |
| Lockfile | `uv.lock`, 44 Pakete mit Hashes | eingecheckt |
| Kein fremder Setup-Code | `no-build = true` | `uv sync` lief in 2,4 s ohne Build |
| Kein Env in iCloud/Git | `UV_PROJECT_ENVIRONMENT` | `.venv/` in `.gitignore` |

Zu `no-build = true`: Der erste `uv sync` **scheiterte** daran, dass das Projekt sich selbst bauen wollte. Statt die Regel aufzuweichen, ist `package = false` gesetzt — `src/` kommt über `pytest pythonpath` herein. Die Regel steht, der Bau entfällt.

### Prüfebene 0: das Environment prüft sich selbst

`tests/test_environment.py`, 15 Tests, alle grün:

- 9 Versions-Pins gegen die tatsächlich importierte Version
- APScheduler bleibt unter 4.x
- `polars` und `pandas-market-calendars` sind nicht installiert
- `pyproject` deckt sich mit `uv.lock` **und** mit dem Environment
- jede direkte Abhängigkeit hat eine Zeile in dieser Datei

**Die Tests wurden gegen eine echte Sabotage geprüft.** Erster Versuch: `duckdb`-Pin auf 1.5.4 verfälscht — die Suite blieb grün. Der Test las die installierte Version und verglich sie gegen eine Konstante im Test selbst, nicht gegen `pyproject.toml`. Ein Test, der eine Drift nicht bemerkt, ist schlimmer als kein Test: Er erzeugt Vertrauen ohne Deckung.

Nachgebessert um zwei Tests, die `pyproject` gegen Lockfile und Environment stellen. Sabotage wiederholt: **2 Tests rot, mit brauchbarer Meldung.** Zurückgesetzt: wieder grün.

### Abweichungen von der Planung

| Geplant | Tatsächlich | Grund |
|---|---|---|
| Python ≥3.12 | 3.13.15 | uv lädt eigenes CPython, unabhängig vom System-3.9.6 |
| Hatchling-Build | kein Build | kollidierte mit `no-build`; `package = false` ist strenger |
| 10 Pakete geprüft | 43 geprüft | transitive Abhängigkeiten nachgezogen |

## Änderungshistorie

| Datum | Änderung |
|---|---|
| 2026-09-25 | Charge 1 geprüft (10 Pakete), Freigabe durch Henri ausstehend |
| 2026-09-25 | Charge 1 freigegeben und installiert; 43 Pakete OSV-geprüft; Prüfebene 0 (15 Tests) gegen Sabotage verifiziert |
