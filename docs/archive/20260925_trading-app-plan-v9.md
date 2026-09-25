---
title: Trading-Analyse-App – Projektplan
date: 20260925
status: Entwurf v9 (ersetzt v8; Grundlagen: 20260925_anlage-spezifikation.md, 20260924_trading-app-qualitaetsstandards.md, 20260925_rechenkern-spezifikation-v1.4.md, 20260925_strategie-katalog.md (v1.2), 20260924_trading-app-research.md)
owner: Henri
superseded_by: ../20260925_trading-app-plan-v9_en.md
binding: no (superseded German original, archived 20260925)
---

# Trading-Analyse-App – Projektplan v9

> **Superseded German original — not binding.** Since 20260925 the English text `../20260925_trading-app-plan-v9_en.md` is binding. This file is kept for reference only. Do not implement from it.

## Änderungen gegenüber v8

- **Neues Kernmodul "Anlegen"** (Anlageberater für langfristige und mittel- bis langfristige Anlagen), vollständig spezifiziert in `20260925_anlage-spezifikation.md`: Profil und Ziele, Reihenfolge der Finanzen, Aktienquote je Ziel, Bausteine, konkrete ETF-Auswahl, Sparplan und steueroptimierte Umschichtung, deutsche Steuer-Engine, Projektion, Monatsempfehlung, Anlagerichtlinie, Verhaltens-Leitplanken, Altersvorsorge-Hinweise
- Das bisherige Langfrist-Modul (L1–L4) wird Teil von "Anlegen": L1 ist das Basisportfolio, L2–L4 und S1 sind optionale Overlays mit zusätzlichem Nachsteuer-Gate
- Informationsarchitektur: "Anlegen" ist der erste Hauptbereich; die Übersicht führt mit der Monatsempfehlung
- Konsistenz bereinigt: Architekturdiagramm auf die v9-Bereiche, Freischaltung von Hebel (Phase 5) und Optionen (Phase 7), Bereich der Prediction Engine (Trading)
- Roadmap: Die erste nutzbare Version (Phasen 1, 2, 3) ist der Anlageberater; Trading, Simulator, Optionen und Prediction Engine folgen **in unveränderter Tiefe**

## Änderungen von v7 zu v8

- Neu: **Prediction Engine** für Aktien (Rangliste mit kalibrierter Wahrscheinlichkeit, den Median des Universums zu schlagen), Abschnitt 4.16; vollständige Rechenregeln in der Spezifikation v1.3, Abschnitt 13
- Roadmap: neue Phase 8b; Tech-Stack um LightGBM und scikit-learn ergänzt

## Änderungen von v6 zu v7

- Neu: **Simulator** mit zwei Modi, Live-Übungsdepot auf aktuellen Kursen und Zeitreise durch historische Kurse (Abschnitt 4.15). Ersetzt das bisherige "Paper-Portfolio aus den Signalen"
- Rechenkern-Spezifikation v1.2 um Ausführungsregeln für Orders ergänzt (Abschnitt 12 der Spezifikation)
- Roadmap: neue Phase 3b

## Änderungen von v5 zu v6

- Kein bestehendes Depot: Die App startet im **Signalmodus** ohne Portfolio. Depot-Erfassung (manuell, CSV, optional IBKR) ist von Anfang an vorhanden und wird genutzt, sobald du ein Depot hast
- Optik: **eigenes, sachliches Design**, nicht Henri Glass
- Alle offenen Fragen geklärt

## Änderungen von v4 zu v5

- Broker-Anbindung ist **optional**: Die App läuft vollständig ohne Broker-Konto, IBKR ist ein zuschaltbares Modul
- Neu: **UI-Design** (Abschnitt 4.14) mit Informationsarchitektur, Designprinzipien und einer eigenen Design-Phase vor dem ersten Dashboard

## Änderungen von v3 zu v4

- Neu: **Qualitätsstandards** als verbindliches Begleitdokument (Sicherheit, Rechenkern, Look-ahead-Bias, Intraday)
- Neu: **Phase 0b Rechenkern-Spezifikation**: Alle Bewertungsformeln werden vor dem Programmieren mit Quellen, Konventionen und Referenzwerten festgelegt
- Neu: **Intraday** zusätzlich zu Swing, mit eigener Datenaufzeichnung ab Phase 1
- Sicherheit: Prüfprotokoll pro Abhängigkeit, Hash-gepinnte Installation, IB Gateway im Read-Only-Modus
- Look-ahead-Bias: bitemporale Datenhaltung, Point-in-time-Zugriff als einzige Schnittstelle, automatische Leckage-Tests bei jedem Build
- Entfernt: PMG/Factiva und WMP-Bezug; Sperrliste bleibt als optionale, allgemeine Funktion

## Änderungen von v2 zu v3

- Neu: **Lernmodul**. Das Tool erklärt jedes Signal, führt durch einen Lernpfad und schaltet Funktionen erst nach abgeschlossenen Lektionen frei (Abschnitt 4.11)
- Budget auf **0 €** festgelegt: verzögerte bzw. Tagesschlussdaten, LLM nur lokal, keine kostenpflichtigen Optionshistorien
- Kapital wird im Tool eingegeben, nicht im Plan festgelegt
- Optionen: Modul wird gebaut, bleibt aber gesperrt, bis der Options-Lernpfad abgeschlossen ist
- Medienquellen auf Deutsch und Englisch

## Änderungen von v1 zu v2

- Neu: **Markt-Intelligenz-Modul** (Medien, Experten, Insider, Filings, Makro), ausgelegt als Kontext- und Risikomodul mit kleinen Tilts, nicht als Empfehlungsgenerator
- Neu: **Options-Modul** mit eigener Bewertungslogik
- Tech-Stack korrigiert: `pandas-ta` raus (Sicherheitsbedenken), TA-Lib, `bt`, `skfolio`, `edgartools`, `py_vollib`, `QuantLib` rein
- Langfrist-Universum auf **UCITS-ETFs** festgelegt (EU-Privatanleger können US-ETFs nicht kaufen)
- Roadmap um zwei Phasen erweitert, offene Fragen aktualisiert

## 1. Ziel und Abgrenzung

Ein privates Analysewerkzeug mit einem klaren Kern: **Es sagt dir jeden Monat, was du mit deinem Geld langfristig und mittel- bis langfristig tun solltest, und warum.** Dazu kommen evidenzbasierte Trading-Signale mit Trefferquote, Unsicherheit und Risiko, und die App bringt dir Anlegen und Trading bei. Die Verbindung zu einem Broker-Konto ist optional. Module auf einer gemeinsamen Engine, nach Priorität:

| Modul | Zweck | Takt |
|---|---|---|
| **Anlegen (Kern)** | Anlageberater: Profil und Ziele, Aktienquote je Ziel, konkrete ETFs, Sparplan, steueroptimierte Umschichtung, Projektion, Monatsempfehlung, Anlagerichtlinie; Basisportfolio L1 plus optionale Overlays L2–L4, S1 (`20260925_anlage-spezifikation.md`) | Monatlich und bei Ereignissen |
| Trading | Swing- und Intraday-Signale für Gold/Rohstoffe, Aktien, ETFs/ETCs, Futures, CFDs | Swing: stündlich bis täglich; Intraday: Minuten-Bars |
| Markt-Intelligenz | Medien, Experten, Insider, Filings, Makro als Kontext, Warnungen und kleine Tilts | Täglich/wöchentlich |
| Optionen | Bewertung einzelner Kontrakte und Defined-Risk-Strategien (gesperrt bis Lernpfad abgeschlossen) | Auf Abruf und täglich |
| Lernen | Erklärung jedes Signals, Lernpfad, Quiz, Trading-Journal, Freischaltung von Funktionen, **Simulator** (Übungsdepot auf echten Kursen) | Laufend |
| Prediction Engine | Aktien-Rangliste mit kalibrierter Wahrscheinlichkeit, sich über 1–3 Monate besser zu entwickeln als der Median der großen Aktien (Bereich Trading, Unterseite Aktien-Ranking) | Monatlich |

Nicht im Scope: Krypto, Weitergabe an Dritte (würde BaFin-relevant), vollautomatische Orderausführung. Die Ausführung ist vorbereitet, aber deaktiviert (Abschnitt 4.10).

**Leitprinzip:** Die Benchmark für jedes Modul ist ein günstiger, breit gestreuter ETF. Was ihn nach Kosten und risikoadjustiert nicht schlägt, wird nicht als Signal angezeigt.

## 2. Getroffene Entscheidungen

| Punkt | Entscheidung | Konsequenz |
|---|---|---|
| Produkte | Möglichst alle handelbaren Produkte, inkl. Optionen | Instrument-Modell mit eigenem Kosten- und Risikoprofil pro Klasse; Hebelprodukte (Futures, CFDs) erst ab Phase 5 mit Lernstufe 5, Optionen erst ab Phase 7 mit Lernstufe 6 |
| Broker | Optional: Interactive Brokers | Ohne Broker: kostenlose Datenquellen, Portfolio manuell oder per CSV-Import. Mit IBKR: Depot-Sync, IBKR-Daten, Optionsketten, später optional Orders |
| Plattform | Python + lokales Streamlit-Dashboard | Läuft auf deinem Mac, gebaut mit Claude Code |
| Ausführung | v1 nur Signale, Orders als spätere Option | Execution-Adapter per Feature-Flag aus |
| Medien/Experten | Kontext + Warnungen + gedeckelte Tilts | Keine primären Kauf-/Verkaufssignale (Evidenzlage, siehe Research Abschnitt 3) |
| LLM-Einsatz | Zusammenfassen und Klassifizieren, keine Renditeprognose | Schützt vor Look-ahead-Bias und Scheinpräzision |
| Zeithorizont Trading | Swing und Intraday | Swing ist mit kostenlosen Daten voll validierbar. Intraday zeichnet ab Phase 1 eigene Daten auf und gibt erst nach ≥ 12 Monaten eigener Historie Signale (Qualitätsstandards Abschnitt 4) |
| Budget | 0 € pro Monat | Nur kostenlose Datenquellen; LLM lokal (FinBERT); Optionslogik wird vorwärts validiert statt mit gekauften Historien |
| Kapital | Wird im Tool eingegeben | Risikomodul rechnet Positionsgrößen daraus; Futures und Optionen werden bei zu kleinem Kapital automatisch ausgeblendet. Ohne Eingabe zeigt die App Risiko in % statt in Euro |
| Depot | Noch keins; Erfassung von Anfang an eingebaut | Signalmodus ohne Portfolio: Signale und Empfehlungen für eine Watchlist, Risiko pro Signal auf Basis des eingegebenen Kapitals. Sobald ein Depot existiert: manuelle Eingabe, CSV-Import oder optional IBKR-Sync; dann kommen Soll-Ist-Vergleich, Klumpenrisiko und Umschichtungsvorschläge dazu |
| Optik | Eigenes, sachliches Design | Kein Henri Glass; ruhige, datenorientierte Gestaltung (Abschnitt 4.14) |
| Optionen | Modul gebaut, aber gesperrt | Freischaltung erst nach Options-Lernpfad und Quiz |
| Medienquellen | Deutsch und Englisch | FinBERT ist englisch; deutsche Texte brauchen ein deutsches Finanz-Sentimentmodell oder werden nur zusammengefasst, nicht bewertet |
| Sperrliste | Optional, standardmäßig leer | Du kannst beliebige Titel ausschließen; für diese zeigt das Tool nichts an |
| Qualität | Qualitätsstandards sind verbindlich | Sicherheit, Rechenkern und Look-ahead-Schutz sind Gates in jeder Phase |


## 3. Broker und Daten

**Standardbetrieb ohne Broker:** Kurse aus kostenlosen Quellen (Tabelle unten), Portfolio per manueller Eingabe oder CSV-Import aus einem beliebigen Depot. Alle Module außer Depot-Sync und Orderausführung funktionieren so. Einschränkungen: Optionsketten kommen dann aus yfinance (inoffiziell, nur US-Optionen, ohne Eurex), Intraday-Aufzeichnung nur mit verzögerten Daten.

**Optional mit Broker:** **Interactive Brokers** über `ib_async` (Nachfolger von `ib_insync`, BSD-2) mit lokal laufendem IB Gateway, zuerst im Paper-Konto. In den Einstellungen zuschaltbar; der Broker-Adapter ist ein austauschbares Modul, sodass später auch andere Broker mit offizieller API ergänzt werden können.

| Datenart | Quelle | Kosten |
|---|---|---|
| Kurse live + historisch | IBKR | Verzögerte Daten kostenlos; Echtzeit-Abos nicht nötig für Swing (genaue Konditionen vor Kontoeröffnung prüfen) |
| Lange Historien für Research | `yfinance` als gecachter Fallback | Kostenlos, rate-limitiert, nur privat |
| Optionsketten, IV, Greeks | IBKR (`reqSecDefOptParams` + Marktdaten) | Verzögert kostenlos; ob Options-Marktdaten ohne Abo nutzbar sind, vor Freischaltung prüfen |
| Historische Optionsketten für Backtests | – | Bei 0 € Budget entfällt das. Die Optionslogik wird vorwärts validiert: jede Bewertung loggen, nach Verfall auswerten |
| News | GDELT, Finnhub Free Tier, RSS-Feeds von Pressemitteilungen, Zentralbanken und Aufsichtsbehörden | Kostenlos |
| Insider, 13F | SEC EDGAR über `edgartools`; deutsche Directors' Dealings über BaFin-Datenbank bzw. Emittenten-Meldungen | Kostenlos |
| Makro | FRED (`fredapi`), EZB (`sdmx1`) | Kostenlos |

**Nicht genutzt:** PMG und Factiva.

## 4. Architektur

```
┌──────────────────────────── Dashboard (Streamlit, localhost) ────────────────────────────┐
│ Übersicht │ Anlegen │ Trading │ Portfolio │ Markt │ Optionen │ Lernen │ Evidenz            │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
┌──────────────┐   ┌────────────────────────┴───────────────────────┐   ┌──────────────────┐
│ Datenschicht │──▶│ Anlage- und Signal-Engine                      │──▶│ Risikomodul      │
│ IBKR         │   │ Anlegen │ Trading │ Options-Bewertung          │   │ Sizing, Limits,  │
│ yfinance     │   └───────▲────────────────────────▲───────────────┘   │ Exposure, Stress │
│ EDGAR, FRED  │           │ Tilts / Warnungen      │                   └────────┬─────────┘
│ News-APIs    │   ┌───────┴────────────────┐  ┌────┴─────────────────┐   ┌───────┴─────────┐
└──────┬───────┘   │ Markt-Intelligenz      │  │ Strategie-Bibliothek │   │ Execution-      │
       │           │ Ingest → Klassifikation│  │ (YAML)               │   │ Adapter (AUS)   │
       ▼           │ → Scorecard → Tilts    │  └────┬─────────────────┘   └─────────────────┘
┌──────────────┐   └───────┬────────────────┘  ┌────┴─────────────────────────┐
│ DuckDB       │◀──────────┴───────────────────│ Backtest- & Validierungs-    │
│ (Point-in-   │                               │ Engine (Walk-forward, DSR,   │
│  time)       │                               │ PBO, Kosten)                 │
└──────────────┘                               └──────────────────────────────┘
```

### 4.1 Datenschicht
Adapter-Muster: Jede Quelle implementiert dasselbe Interface, damit Quellen austauschbar bleiben. Alle Daten werden **point-in-time** gespeichert, also mit dem Zeitpunkt, zu dem sie verfügbar waren (Veröffentlichungszeit, nicht Ereigniszeit). Das ist die Voraussetzung dafür, dass News- und Filing-Signale ohne Look-ahead getestet werden können.

### 4.2 Instrument-Modell

| Klasse | Besonderheiten |
|---|---|
| Aktien, UCITS-ETFs, ETCs | Gebühren, Spread, Handelszeiten, Währung |
| Futures | Multiplikator, Rollen, Margin, Verfall |
| CFDs | Hebel (ESMA-Grenze Gold 1:20), Übernachtfinanzierung, Spread |
| Optionen | Stil (europäisch/amerikanisch), Multiplikator, Verfall, Ausübung/Zuteilung, Margin, Dividendentermine |
| Minenaktien | Wie Aktien, plus Goldpreis-Korrelation |

### 4.3 Strategie-Bibliothek
Strategien als YAML-Konfiguration: Einstieg, Ausstieg, Stop, Timeframe, zulässige Produktklassen, Evidenzquelle und Evidenzgrad.

### 4.4 Backtest- und Validierungs-Engine
Eine Strategie oder ein Tilt geht nur live, wenn alle Prüfungen bestanden sind:
- Realistische Kosten je Produktklasse (Gebühren, Spread, Slippage, Finanzierung, Rollkosten)
- Walk-forward und Combinatorial Purged CV (`skfolio`)
- Deflated Sharpe Ratio und PBO, selbst implementiert nach Bailey & López de Prado
- Kein Look-ahead: nur point-in-time verfügbare Daten
- **Publikationsabschlag:** Bei publizierten Signalen wird die erwartete Wirkung um ≥ 50 % reduziert (McLean & Pontiff, 2016)
- Benchmark: günstiger breiter ETF, nach Kosten und risikoadjustiert

### 4.5 Kernmodul Anlegen und Trading-Modul

**Anlegen (Kern)** ist vollständig in `20260925_anlage-spezifikation.md` spezifiziert. Kurzfassung des Ablaufs:
1. **Profil und Ziele** nach der Struktur der ESMA-Geeignetheitsleitlinien, mit Verlustfrage in Euro statt Selbsteinschätzung
2. **Reihenfolge der Finanzen:** teure Schulden, Notgroschen, dann Investieren
3. **Aktienquote je Ziel** = Minimum aus Horizont-, Kapazitäts- und Toleranzgrenze
4. **Bausteine:** Welt-Aktien im Marktgewicht plus Sicherheitsbaustein; Satelliten (Gold, Faktoren, Einzelaktien, Taktik) zusammen höchstens 20 % des Risikobudgets
5. **Konkrete ETFs** über harte Filter und eine transparente Bewertung (Tracking-Differenz vor TER), aus einer regelkonform gepflegten Kandidatenliste
6. **Sparplan** mit Cashflow-Rebalancing, jährliche Prüfung, steueroptimierte Verkäufe, Nutzung des Sparer-Pauschbetrags
7. **Steuer-Engine** für Deutschland (Abgeltungsteuer, Günstigerprüfung, NV-Bescheinigung, Teilfreistellung, Vorabpauschale, Gold nach § 23, Verlusttöpfe)
8. **Projektion** per Block-Bootstrap aus Mehr-Länder-Historie, zentriert auf konservative Annahmen, in heutigen Euro
9. **Monatsempfehlung**, **Anlagerichtlinie (IPS)**, **Verhaltens-Leitplanken**, **Altersvorsorge-Hinweise**

Das Basisportfolio entspricht Strategie L1; L2–L4 und S1 sind optionale Overlays, die zusätzlich ein Nachsteuer-Gate bestehen müssen und die Aktienquote nur senken, nie erhöhen dürfen.

**Trading** bleibt in voller Tiefe wie im Strategie-Katalog (S1–S3, I1, Kontrollgruppe) und in der Rechenkern-Spezifikation beschrieben.

| | Trading | Anlegen |
|---|---|---|
| Strategiefamilien | Time-Series-Momentum, Aktien-Momentum, 52-Wochen-Hoch, Intraday-Momentum | Basisportfolio L1; Overlays L2 (Trendfilter), L3 (Rotation), L4 (Volatilität), S1 (Trendfolge) |
| Output | Richtung, Einstieg, Stop, Ziel, Trefferquote mit Konfidenzintervall | Monatsempfehlung mit konkreten Käufen, Sparplan-Aufteilung, Umschichtung, Steuerwirkung, Projektion |

### 4.6 Markt-Intelligenz-Modul (neu)

**Pipeline:**
1. **Ingest** (zeitgesteuert per APScheduler): News (GDELT, Finnhub), SEC Form 4 und 13F, Makrodaten, optional ausgewählte Research-Quellen. Jeder Eintrag bekommt einen Veröffentlichungszeitstempel.
2. **Klassifikation:** FinBERT lokal für englische Stimmung; für deutsche Texte ein lokales deutschsprachiges Finanzmodell (Auswahl in Phase 4 prüfen) oder nur Zusammenfassung ohne Stimmungswert. Zusammenfassungen über ein lokales Open-Weight-LLM (kostenlos, läuft auf dem Mac) oder manuell mit Claude im Chat. Eine bezahlte LLM-API ist bei 0 € Budget nicht vorgesehen. Firmennamen werden vor der Stimmungsbewertung anonymisiert.
3. **Aggregation:** Wöchentlicher Nachrichtenton je Titel/Asset, Cluster opportunistischer Insiderkäufe (nicht-routinemäßige Käufe, Methode nach Cohen et al., 2012), 13F-Positionen ausgewählter Fonds.
4. **Einordnung nach Evidenzgrad** (aus Research Abschnitt 3):

| Kategorie | Inhalte | Wirkung in der App |
|---|---|---|
| Tilt (klein, gedeckelt) | Opportunistische Insiderkäufe, wöchentlicher negativer Nachrichtenton | Max. ±10–20 % Veränderung der Positionsgröße eines bestehenden Signals, nie ein eigenes Signal (Deckel wird im Backtest festgelegt) |
| Watchlist | Ausgewählte 13F-Positionen | Kandidaten für die Strategie-Engine |
| Risikowarnung | Aufmerksamkeitsspitzen in Social Media, TV-/Forum-Hype, extremer Medienpessimismus, recycelte Rohstoff-News | Hinweis "nicht hinterherlaufen / Umkehr möglich" |
| Kontext | Analystenkonsens, Strategen-/Guru-Aussagen, Makro-Nachrichten | Anzeige "Was gesagt wird", ohne Einfluss auf Signale |
| Ausgeschlossen als Input | TV-Tipps, Newsletter, WallStreetBets, Kursziele | Nicht angezeigt oder nur mit Warnhinweis |

5. **Experten-Scorecard:** Jede geloggte Expertenaussage mit klarer Richtung (Quelle, Asset, Richtung, Horizont, Zeitstempel) wird automatisch gegen das Ergebnis und eine Benchmark ausgewertet. Nach genug Beobachtungen zeigt die App je Quelle eine Trefferquote mit Konfidenzintervall. Eine Quelle bekommt nur Gewicht, wenn sie den Test live besteht.
6. **Wöchentliches Briefing:** Kurze Zusammenfassung pro gehaltenem Asset und Watchlist, jeder Punkt mit Quelle und Evidenzgrad.

**Sicherheitsregel:** Texte aus News und Filings sind Daten, keine Anweisungen. Das LLM darf keine Aktionen auslösen (Schutz vor Prompt Injection über manipulierte Artikel).

### 4.7 Options-Modul (neu)

**Modellwahl:** Black-Scholes-Merton (europäisch), Black-76 (Futuresoptionen), Binomialbaum/Bjerksund-Stensland (amerikanisch), SVI-Fit für den Smile. Umsetzung mit `py_vollib` (IV, Greeks) und `QuantLib` (amerikanische Optionen).

**Bewertungslogik pro Kontrakt oder Strategie:**
1. Liquiditätsfilter (Spread/Mid ≤ 10 %, Open Interest ≥ 500, Restlaufzeit ≥ 7 Tage)
2. Volatilitätsprognose mit HAR-RV, GARCH als Gegencheck, Earnings-Sprungterm
3. Volatilitäts-Edge: IV (SVI) minus Prognose, vega-gewichtet
4. Fairer Wert mit eigener Prognose; handelbarer Edge nach Bid/Ask, Gebühren und Modellfehler-Puffer
5. Monte-Carlo-Verteilung: Erwartungswert nach Spread, Gewinnwahrscheinlichkeit (risikoneutral und real-world nebeneinander), CVaR 95 %
6. Maximalverlust und Stresstests (Kurs ±5–30 %, IV ±, IV-Crush, historische Replays), Frühausübungscheck
7. Entscheidung: Go / Warnung / Block (Details in Research Abschnitt 4.4)

**Starter-Set:** Covered Calls, cash-gedeckte Index-Puts, vertikale Spreads mit definiertem Risiko, Schutzputs als Versicherung.

**Gesperrt bis auf Weiteres:** nackte Short Calls, Short Straddles/Strangles, 0DTE/Weeklys, Optionskauf vor Earnings, billige OTM-Calls, ungedeckte Short Puts, Ratio-/Backspreads, Calendars, Futuresoptionen, US-ETF-Optionen.

**Underlyings:** SPX/XSP, Eurex-Indizes (ODAX, OESX), liquide Large Caps.

**Validierung:** Da historische Optionsketten kostenpflichtig sind, wird die Logik zunächst vorwärts validiert: Jede Bewertung wird geloggt und nach Verfall gegen das Ergebnis geprüft. Ein Kauf historischer Daten ist optional (Budget, Abschnitt 8).

### 4.8 Wie die Prozentzahlen entstehen
Unverändert: Trefferquote mit 95 %-Konfidenzintervall und n, Kalibrierungsstatus (Reliability-Diagramm, Brier-Score), Erwartungswert nach Kosten. Bei Optionen zusätzlich die Trennung risikoneutral vs. real-world.

### 4.9 Risikomodul
- Positionsgröße aus Stop-Abstand, max. 1 % Kapitalrisiko pro Trade
- Optionen: Maximalverlust ≤ 2 % des Portfolios pro Position, Stressverlust muss ohne Zwangsverkauf tragbar sein
- Hebel-Limit pro Klasse, strenger als das Broker-Limit
- Gesamt-Exposure und Korrelationscheck, inkl. Options-Deltas (z. B. Gold-ETC + Gold-Future + Minenaktie + Short Put auf Minenaktie = ein Klumpenrisiko)
- Tägliches Verlustlimit mit Signal-Stopp

### 4.10 Execution-Adapter (vorbereitet, deaktiviert)
Aktivierung erst nach ≥ 3 Monaten erfolgreichem Paper Trading, zuerst im Paper-Konto, jede Order mit deiner Bestätigung, harte Limits und Kill-Switch, Zugangsdaten nur in `.env`. Optionen zusätzlich nur innerhalb des Starter-Sets und der IBKR-Berechtigungsstufen 1–3.

### 4.11 Lernmodul (neu)

Das Tool soll dir Trading und langfristiges Anlegen beibringen. Es wird so gebaut, dass Lernen und Nutzen ineinandergreifen:

**1. Jedes Signal erklärt sich selbst.** Neben jedem Signal steht ein "Warum?"-Panel: welche Regel ausgelöst hat, die Evidenz dahinter (Studie, Evidenzgrad), das Risiko in Euro bei deinem Kapital und was das Signal *nicht* weiß. Fachbegriffe sind mit einem Glossar verlinkt.

**2. Lernpfad mit Freischaltung.** Funktionen werden erst nach der passenden Lektion und einem kurzen Quiz freigeschaltet:

| Stufe | Inhalt | Schaltet frei |
|---|---|---|
| 1: Fundament | Rendite und Risiko, Reihenfolge der Finanzen (Schulden, Notgroschen), Diversifikation, Kosten und Tracking-Differenz, Zinseszins, Sparplan, Weltportfolio mit UCITS-ETFs, Steuern (Abgeltungsteuer, Sparer-Pauschbetrag, Teilfreistellung, Vorabpauschale, Anlage KAP), Anlagerichtlinie | Kernmodul Anlegen (Basisportfolio, Sparplan, Projektion) |
| 2: Wie man Evidenz liest | Backtest vs. Realität, Overfitting, Konfidenzintervalle, Publikationseffekt, warum Gurus nicht funktionieren, Lebenszyklus- vs. Vollaktien-Sicht, Faktoren und Einzelaktien (Bessembinder) | Evidenz- und Backtest-Ansicht; Overlays und Satelliten im Kernmodul |
| 3: Swing-Trading | Trendfolge, Momentum, Mean Reversion, Positionsgröße, Stops, Erwartungswert | Trading-Modul (Aktien, ETFs, ETCs) |
| 4: Markt-Intelligenz | Wie News eingepreist werden, Insidersignale, Hype erkennen | Tilts und Scorecard |
| 5: Hebelprodukte | Futures, CFDs, Margin, Nachschusspflicht, Finanzierungskosten | Futures und CFDs im Trading-Modul |
| 6: Optionen | Payoffs, Greeks, implizite Volatilität, Volatilitätsprämie, Starter-Set, Steuern auf Termingeschäfte | Options-Modul (nur Starter-Set) |

**3. Trading-Journal.** Jeder Paper- oder Echttrade bekommt vorab eine kurze Begründung (Signal, Erwartung, Stop). Das Tool wertet das Journal aus und zeigt dir typische Verhaltensfehler mit Belegen aus deinen eigenen Daten: Überhandeln, zu frühes Gewinnmitnehmen und zu langes Verlusthalten (Dispositionseffekt), Abweichen von Signalen.

**4. Wöchentlicher Rückblick.** Was die Signale gesagt haben, was passiert ist, was du daraus lernst. Dazu eine Quizfrage zum Stoff der Woche (Spaced Repetition).

**5. Inhalte kostenlos erstellt.** Lektionen und Quizfragen werden beim Bauen mit Claude Code als statische Inhalte geschrieben, mit Quellen. Zur Laufzeit ist keine bezahlte API nötig.

### 4.12 Sperrliste (optional)

Eine selbst gepflegte Liste von Titeln, die das Tool vollständig ausblendet: keine Signale, keine Analysen, Orders werden blockiert. Standardmäßig leer.

### 4.13 Qualitätsstandards

Sicherheit, Rechenkern und Look-ahead-Schutz sind in `20260924_trading-app-qualitaetsstandards.md` festgelegt und gelten für jedes Modul. Kurzfassung:
- **Sicherheit:** Prüfprotokoll pro Abhängigkeit, Allowlist, Hash-gepinnte Installation, Read-Only-API bis zur Ausführungsfreigabe
- **Rechenkern:** Spezifikation vor Code; vier Prüfebenen (Referenzwerte, zwei unabhängige Implementierungen, Invarianten, Datenprüfung); unabhängige Zweitprüfung jedes Rechenmoduls
- **Look-ahead:** bitemporale, append-only Datenhaltung; Strategien sehen Daten nur über `PointInTimeView(t)`; Abschneide-, Stör- und Verzögerungstests bei jedem Build; versiegelter Holdout

### 4.15 Simulator (neu)

Ein Übungsdepot mit virtuellem Geld auf echten Kursen. Es nutzt dieselbe Datenschicht, dasselbe Kostenmodell und dieselben Ausführungsregeln wie das echte Tool, damit das Geübte sich auf echtes Handeln überträgt.

**Zwei Modi:**

| Modus | Was passiert | Wofür |
|---|---|---|
| **Live-Übungsdepot** | Du handelst auf aktuellen (kostenlos um ca. 15 Minuten verzögerten) Kursen; das Depot läuft in Echtzeit weiter | Routine aufbauen, Signale der App nachhandeln, Swing und Intraday üben |
| **Zeitreise** | Du startest an einem Datum in der Vergangenheit und handelst Tag für Tag (oder Bar für Bar) vorwärts; die App zeigt nur, was bis zu diesem Zeitpunkt bekannt war | Jahre in Stunden üben, Crashs und Seitwärtsphasen erleben, Langfrist-Anlegen trainieren |

**Funktionen:**
- Ordertypen: Market, Limit, Stop, Stop-Limit, Stop-Loss und Gewinnziel am Einstieg
- Mehrere Übungsdepots parallel (z. B. "Swing", "Langfrist-Sparplan", "Gold"), jeweils mit eigenem Startkapital
- Dividenden, Splits, Kosten und eine grobe Steuerschätzung werden wie im echten Tool berücksichtigt
- **Szenarien** für die Zeitreise: Finanzkrise 2008, Corona-Crash 2020, Zinswende 2022, Seitwärtsmarkt, zufälliger Startpunkt
- **Auswertung** nach jeder Sitzung: Rendite gegen Benchmark (Buy-and-Hold) und gegen das, was die Signale der App gemacht hätten; dazu das Trading-Journal mit deinen typischen Fehlern
- Optionen im Simulator erst nach Lernstufe 6, wie im echten Tool

**Regeln gegen Selbsttäuschung:**
1. **Blindmodus für die Zeitreise (Standard):** Titel und Datum sind verborgen, Kurse auf 100 normiert. Wer weiß, dass es März 2020 ist, "übt" mit Wissen um die Erholung. Aufgelöst wird am Ende der Sitzung
2. **Kein Zurückspulen:** Entscheidungen sind endgültig; eine Sitzung kann nur neu gestartet werden, das wird im Journal vermerkt
3. **Realistische Ausführung:** Orders werden frühestens auf der nächsten Bar ausgeführt, mit Spread, Slippage und Kommission (Spezifikation Abschnitt 12). Im Live-Übungsdepot mit verzögerten Daten wird eine Order zu dem Kurs ausgeführt, der zum Zeitpunkt der Order tatsächlich galt, sobald dieser Kurs sichtbar wird, nicht zum veralteten angezeigten Kurs
4. **Klare Trennung:** Simulationsmodus ist in der gesamten Oberfläche durch ein farbiges Band und die Beschriftung "Simulation" markiert, damit du echte und simulierte Depots nie verwechselst. Ein späterer Orderversand an einen Broker ist aus dem Simulator technisch unmöglich
5. **Keine Vermischung mit der Evidenz:** Ergebnisse aus dem Simulator fließen nie in die Bewertung von Strategien ein (sonst würde die Zeitreise, in der du Daten gesehen hast, den versiegelten Holdout kontaminieren). Der Zeitraum des versiegelten Holdouts ist in der Zeitreise gesperrt, bis er für die Strategieprüfung geöffnet wurde

**Aufwand:** Der Simulator nutzt die ohnehin geplanten Bausteine (`PointInTimeView` für die Zeitreise, Kostenmodell, Depotverwaltung). Neu sind im Wesentlichen die Ausführungslogik für Ordertypen, die Sitzungssteuerung und die Auswertung.

### 4.16 Prediction Engine (neu)

**Was sie tut:** Einmal im Monat ordnet sie die großen, liquiden Aktien (USA: Top 500; Europa: größte Werte) nach ihrer Chance, sich über 1 bzw. 3 Monate besser zu entwickeln als der Median dieser Aktien. Je Aktie zeigt sie Rang, Quintil, eine kalibrierte Wahrscheinlichkeit mit Intervall, ein Prognoseintervall der Rendite und die drei wichtigsten Gründe für die Bewertung. Daneben, klar getrennt, steht als Kontext, wie oft Aktien historisch den Index geschlagen haben.

**Was sie nicht tut:** Kursziele oder Kursprognosen. Die Forschung zeigt einen kleinen, aber messbaren Vorteil. Korrekt kalibrierte Wahrscheinlichkeiten liegen deshalb fast immer zwischen 45 und 55 %. Die App zeigt diese Einordnung direkt neben der Rangliste.

**Wie sie so genau wie möglich wird** (Details in der Spezifikation, Abschnitt 13):
- Saubere point-in-time-Daten (EDGAR mit Einreichungszeitpunkt, Veröffentlichungssperre für Merkmale)
- Merkmale aus der Literatur statt aus dem eigenen Backtest, rangnormiert je Stichtag
- Kontinuierliche, rangbasierte Zielgröße; Wahrscheinlichkeiten erst über Kalibrierung auf einem später liegenden, strikt getrennten Zeitblock
- Gleichgewichtetes Ensemble (Ridge + LightGBM mit mehreren Seeds) statt eines einzelnen "optimierten" Modells
- Expandierendes Training, jährliche Neuschätzung, Embargo, jede Variante für die Overfitting-Tests gezählt
- Harte Gates: Die Engine muss eine einfache Momentum-Rangliste statistisch schlagen und nach Kosten besser sein als der Index **und** als ein gleichgewichtetes Portfolio aller Aktien, sonst geht sie nicht live
- Laufende Überwachung mit automatischem Status "Beobachtung" bei Leistungsverlust

**Grenzen:** Kostenlose Kursdaten enthalten kaum delistete Aktien (Survivorship-Bias). Die App bildet das historische Universum deshalb aus SEC-Meldepflichtigen, setzt für verschwundene Aktien eine Delisting-Rendite an und erklärt Zeiträume mit zu vielen Lücken für ungültig. Für europäische Aktien fehlen kostenlose point-in-time-Fundamentaldaten; dort arbeitet die Engine nur mit Kurs- und Volumenmerkmalen.

**Lernmodul:** Stufe 2 ("Wie man Evidenz liest") bekommt eine Lektion zur Prediction Engine: warum 55 % viel sind, was Kalibrierung bedeutet und warum eine Rangliste keine Kaufliste ist.

### 4.14 UI-Design

**Ziel:** Übersichtlich und anschaulich, wenige Schaltflächen, aufgeräumt. Lieber Untermenüs als alles auf einer Fläche, aber maximal zwei Ebenen tief.

**Informationsarchitektur (max. 2 Ebenen):**

| Hauptbereich | Unterseiten | Beantwortet die Frage |
|---|---|---|
| Übersicht | – | Was ist heute wichtig? Führt mit der **Monatsempfehlung** (Kernaussage in einem Satz, Aktionen), danach Portfolio-Stand, Trading-Signale, Warnungen, Lernimpuls |
| **Anlegen** | Empfehlung · Ziele & Portfolio · Projektion · Anlagerichtlinie | Was soll ich mit meinem Geld tun, wie stehe ich zu meinen Zielen, womit kann ich rechnen? |
| Trading | Swing · Intraday · Aktien-Ranking | Was sagen die Trading-Strategien und die Prediction Engine, und warum? |
| Portfolio | Positionen · Risiko · Journal | Wo stehe ich, wie viel Risiko trage ich? Ohne Depot: Einstieg "Depot anlegen" (manuell, CSV, IBKR). Im Simulationsmodus zeigt dieser Bereich das Übungsdepot |
| Markt | Briefing · Insider & Filings · Experten-Scorecard | Was passiert, und was davon ist belastbar? |
| Optionen | Kette & Bewertung · Strategien (gesperrt bis Lernstufe 6) | Ist dieser Kontrakt fair bewertet, was kann ich verlieren? |
| Lernen | Lernpfad · Simulator · Glossar · Quiz | Was muss ich verstehen und üben, bevor ich das nutze? |
| *Unten, abgesetzt* | Evidenz & Backtests · Datenqualität · Einstellungen | Stimmt die Basis? (Broker optional, Kapital, Sperrliste, Sicherheit) |

**Designprinzipien:**
- **Eine Kernaussage pro Seite.** Jede Seite beantwortet genau eine Frage aus der Tabelle; alles andere liegt eine Ebene tiefer.
- **Progressive Offenlegung:** Karte mit Kernzahl → Klick öffnet Details (Chart, "Warum?", Evidenz, Risiko). Keine Tabellen mit 20 Spalten auf der ersten Ebene.
- **Höchstens 1–2 Primäraktionen pro Seite.** Filter und Einstellungen in ausklappbaren Bereichen.
- **Signalkarte als Grundbaustein:** Titel, Richtung, Trefferquote mit Konfidenzintervall, Risiko in Euro, Status (neu/aktiv/abgelaufen), "Warum?"-Link. Überall gleich aufgebaut.
- **Unsicherheit sichtbar, nicht versteckt:** Konfidenzintervalle als Balken, "kein Signal" als gleichwertiger, ruhiger Zustand statt als Fehlermeldung.
- **Farbe mit Bedeutung:** zurückhaltende Grundfläche, Farbe nur für Richtung und Warnungen; nie nur Rot/Grün (Farbfehlsichtigkeit), immer mit Symbol oder Text.
- **Zahlen gut lesbar:** Tabellenziffern, deutsches Zahlenformat, Einheiten immer dabei.
- **Hell- und Dunkelmodus.**

**Designprozess:**
1. **Recherche** vor dem ersten Dashboard: Mobbin (über den verbundenen Connector) für Muster aus Finanz-, Portfolio- und Trading-Apps, insbesondere Übersichtsseiten, Watchlists, Detailansichten und Onboarding; dazu die Frontend-Design-Skill für eine eigenständige ästhetische Richtung statt Standard-Dashboard-Optik.
2. **Mockups** der sechs Kernseiten (Übersicht mit Monatsempfehlung, Anlegen: Ziele & Portfolio, Projektion, Signaldetail, Briefing, Lernpfad) sowie des Onboardings (Profil, Verlustfrage, Anlagerichtlinie) als Design-Artefakt zum Durchklicken und Kommentieren, bevor Code entsteht.
3. **Umsetzung** erst nach deiner Freigabe der Mockups.
4. **Design-Review** vor jeder Freigabe: Prüfung gegen die Prinzipien oben, Screenshots in beiden Modi und auf kleiner Fensterbreite.

**Technische Grenze, die du kennen solltest:** Streamlit ist schnell und kommt ohne JavaScript-Abhängigkeiten aus, was gut zu den Sicherheitsstandards passt. Gestalterisch ist es aber begrenzt (Layout, Animationen, eigene Komponenten). Empfehlung: **v1 mit Streamlit** (seitenbasierte Navigation mit Abschnitten, eigenes Theme, sparsames CSS). Weil Engine und Oberfläche getrennt sind, kann die Oberfläche später auf ein eigenes Web-Frontend umziehen, falls Streamlit das Design nicht trägt. Das würde allerdings ein JavaScript-Ökosystem mit eigenem Supply-Chain-Risiko mitbringen und muss dann bewusst entschieden werden.

## 5. Tech-Stack

| Bereich | Tool | Hinweis |
|---|---|---|
| Sprache | Python 3.12+ | |
| Broker | `ib_async` + IB Gateway | Nicht `ibapi`-Pakete von PyPI |
| Daten | pandas, DuckDB; `yfinance` als Fallback | |
| Indikatoren | TA-Lib oder eigene Funktionen | **Nicht** `pandas-ta` |
| Backtest | `vectorbt` (Swing), `bt` (Allokation) | |
| Validierung/Portfolio | `skfolio` + eigene DSR/PBO | |
| News/Sentiment | `transformers` + ProsusAI/FinBERT, GDELT, Finnhub | Lokales Open-Weight-LLM für Zusammenfassungen, keine bezahlte API |
| Filings/Makro | `edgartools`, `fredapi`, `sdmx1` | |
| Optionen | `py_vollib`, `QuantLib` | |
| Prediction Engine | `lightgbm` (MIT, Microsoft), `scikit-learn` (BSD-3) | Vor Aufnahme in die Allowlist prüfen: Das LightGBM-Repository ist laut Recherche in eine neue GitHub-Organisation umgezogen (lightgbm-org); bestätigen, dass die PyPI-Seite dorthin verweist und der Umzug von den bisherigen Maintainern angekündigt wurde |
| Dashboard | Streamlit + Plotly | Telemetrie aus, nur localhost |
| Scheduling | APScheduler 3.x | |
| Entwicklung | Claude Code, Git | |

**Installationshygiene:** siehe Qualitätsstandards Abschnitt 1 (Prüfprotokoll, Allowlist, `--require-hashes`, nur Wheels, 7 Tage Wartezeit bei Updates, `pip-audit`).

## 6. Roadmap

| Phase | Inhalt | Gate |
|---|---|---|
| 0: Research | Tools, Bausteine, Evidenz (erledigt, 20260924); Strategien formalisieren (erledigt, 20260925: `20260925_strategie-katalog.md`) | ≥ 8 formalisierte Strategien mit Evidenzgrad (erfüllt: 8 Kern-/Kandidatenstrategien, 4 Optionsstrategien, 11 Kontrollregeln, unabhängig geprüft) |
| 0b: Rechenkern-Spezifikation | Alle Formeln mit Primärquellen, Konventionen, Randfällen und Referenzwerten für Tests; eigener Research-Schritt | Jede Formel hat mindestens einen publizierten Referenzwert und eine unabhängige Zweitprüfung |
| 1: Fundament | Bitemporale Datenschicht, `PointInTimeView`, Instrument-Modell, DuckDB, Leckage-Tests, Start der Intraday-Aufzeichnung | 20 Jahre Tagesdaten für Gold, 10 UCITS-ETFs, 20 Aktien sauber geladen; Leckage-Tests grün |
| 2: Backtest-Engine | Kosten, Walk-forward, DSR, PBO; ereignisgesteuerte Bestätigungsschleife | Exakte Tests auf synthetischen Reihen mit analytisch bekanntem Ergebnis; qualitative Reproduktion des Faber-Trendfilters im frei verfügbaren Zeitraum (exakte Reproduktion wegen lizenzierter Originaldaten nicht möglich, siehe Rechenkern-Spezifikation Abschnitt 11); alle Rechenkern-Tests grün |
| 2b: UI-Konzept | Mobbin-Recherche, ästhetische Richtung, Mockups der sechs Kernseiten und des Onboardings | Mockups von dir freigegeben |
| 3: **Anlegen (Kernmodul) + Lernstufen 1–2** — erste nutzbare Version | Anlage-Spezifikation A1–A13: Onboarding (Profil, Verlustfrage, Ziele), Vorbedingungen, Aktienquote, Bausteine, ETF-Auswahl mit kuratierter Kandidatenliste, Sparplan und Umschichtung, Steuer-Engine, Projektion, Monatsempfehlung, Anlagerichtlinie, Leitplanken; Basisportfolio L1; Overlays L2–L4 (standardmäßig aus); erstes Dashboard nach freigegebenem UI-Konzept, "Warum?"-Panels, Glossar | Alle Tests TA1–TA22 grün; Steuer-Engine und Projektion unabhängig geprüft; Monatsempfehlung wird aus echten Daten erzeugt; Overlays nur aktiv, wenn sie die Gates und das Nachsteuer-Gate bestehen; Lektionen 1–2 fertig; Design-Review bestanden |
| 3b: Simulator | Zeitreise (mit Blindmodus und Szenarien) und Live-Übungsdepot, Ordertypen, Auswertung; parallel zu Phase 3 möglich | Alle Ausführungstests aus Spezifikation Abschnitt 12 grün; Simulator und Backtest liefern bei identischen Orders identische Ergebnisse; Holdout-Sperre wirksam |
| 4: Markt-Intelligenz v1 | Ingest, Klassifikation, Briefing, Scorecard-Logging; parallel zu Phase 3 möglich | Pipeline läuft 4 Wochen stabil, alle Einträge mit Zeitstempel und Quelle |
| 5: Trading-Modul Swing + Lernstufe 3, Journal | Gold & Co., danach Futures/CFDs mit Lernstufe 5 | Wie Phase 3, plus Finanzierungs- und Rollkosten |
| 5b: Trading-Modul Intraday | Research auf Stundenbars und eigenen Aufzeichnungen, strengeres Kostenmodell | ≥ 12 Monate eigene Intraday-Daten; Gates wie Phase 3 mit niedrigeren "Zu gut"-Schwellen |
| 6: Broker-Anbindung (optional) | IBKR-Paper-Konto, Depot-Sync, IBKR-Daten, Optionsketten; entfällt, wenn du ohne Broker arbeitest | Live-Signale entsprechen dem Backtest-Verhalten |
| 7: Options-Modul + Lernstufe 6 | Bewertungslogik, Starter-Set, Vorwärts-Logging; bleibt gesperrt bis Quiz bestanden | Logik reproduziert IBKR-Greeks und -IV innerhalb enger Toleranz |
| 8: Tilts aktivieren | Markt-Intelligenz-Tilts durch die Validierungs-Engine | Tilt verbessert Walk-forward-Ergebnis nach Kosten und Abschlag |
| 8b: Prediction Engine | EDGAR-Fundamentaldaten point-in-time, Merkmale, Basislinien, LightGBM-Ensemble, Kalibrierung, Prognoseintervalle, Überwachung | Alle Gates aus Spezifikation PE10 im Walk-forward erfüllt (Rank-IC signifikant, schlägt Momentum-Basislinie, Top-Quintil schlägt nach Kosten sowohl den kapitalgewichteten als auch den gleichgewichteten Benchmark mit DSR ≥ 0,95, PBO ≤ 0,05); Kalibrierung besteht S9; alle Tests T32–T40 grün |
| 9: Paper Trading | ≥ 3 Monate alle Module ohne echtes Geld | Live-Ergebnisse im Backtest-Konfidenzbereich |
| 10: Execution (optional) | Adapter aktivieren, zuerst Paper-Konto | Sicherheitsregeln aus 4.10 umgesetzt |

Alle Phasen laufen mit kostenlosen Daten. Kosten entstehen erst, wenn du später echte Trades machst (Gebühren) oder dich bewusst für ein Datenabo entscheidest.

## 7. Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Overfitting | Walk-forward, DSR, PBO, Paper-Trading-Gate |
| Look-ahead-Bias | Bitemporale Daten, `PointInTimeView`, automatische Leckage-Tests, versiegelter Holdout, keine LLM-Backtests vor dem Trainings-Cutoff (Qualitätsstandards Abschnitt 3) |
| Keine Strategie oder kein Tilt überlebt | Valides Ergebnis; App zeigt "kein Signal", Basisportfolio L1 des Kernmoduls Anlegen bleibt Basis |
| Hebel und Optionen | Futures/CFDs erst ab Phase 5 mit Lernstufe 5, Optionen erst ab Phase 7 mit Lernstufe 6; Starter-Set, Maximalverlust-Regeln, Stresstests |
| Scope zu groß | Strikte Reihenfolge; jedes Modul ist erst "fertig", wenn sein Gate erreicht ist |
| Manipulierte Inhalte (Prompt Injection, Pump-Artikel) | LLM ohne Aktionsrechte, Quellen-Whitelist, Hype als Warnung statt Signal |
| Datenkosten wachsen | Budget 0 €; jede kostenpflichtige Quelle braucht eine explizite Entscheidung |
| Supply-Chain-Angriffe | Prüfprotokoll, Allowlist, Hash-Pinning, Read-Only-API (Qualitätsstandards Abschnitt 1) |
| Rechenfehler in der Bewertung | Spezifikation vor Code, vier Prüfebenen, unabhängige Zweitprüfung (Qualitätsstandards Abschnitt 2) |
| Intraday mit zu wenig Daten | Eigene Aufzeichnung, Signale erst nach ≥ 12 Monaten Historie |
| Steuerliche Fehler | IBKR behält keine deutsche Steuer ein; Trades exportieren, Anlage KAP; bei Optionen ggf. Steuerberater |
| Scheinsicherheit durch Lernfortschritt | Freischaltung heißt "verstanden", nicht "profitabel"; Paper-Trading-Gate gilt trotzdem |
| Scheinpräzision der Prediction Engine | Kalibrierung auf zurückgehaltenem Zeitblock, Plausibilitätsgrenze aus dem gemessenen Rank-IC, Status "Beobachtung" bei Leistungsverlust, keine Prozentzahl ohne bestandene Kalibrierung |
| Survivorship-Bias in kostenlosen Kursdaten | Universum aus SEC-Meldepflichtigen, Delisting-Rendite, Ungültigkeitsregel, Hinweis bei jedem Ergebnis; nicht vollständig behebbar |
| Überladene Oberfläche | Informationsarchitektur mit max. 2 Ebenen, Mockup-Freigabe vor Code, Design-Review pro Phase |
| Scheinlernen im Simulator (Rückschaufehler, zu optimistische Ausführung) | Blindmodus, kein Zurückspulen, konservative Ausführungsregeln, Vergleich mit Benchmark |
| Verwechslung von Simulation und echtem Depot | Durchgehende Kennzeichnung, kein Orderweg aus dem Simulator |

## 8. Offene Fragen

Keine. Alle Entscheidungen stehen in Abschnitt 2.

## Quellen

Siehe `20260925_anlage-spezifikation.md` (Quellen zum Kernmodul), `20260924_trading-app-research.md` (vollständige Quellenliste) und `20260924_trading-app-qualitaetsstandards.md`. Zusätzlich:
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance, 20*(4), 39–69.
- Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management, 40*(5), 94–107.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79.
- Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics, 104*(2), 228–250.
