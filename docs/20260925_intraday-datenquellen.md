# Intraday-Daten: gekauft statt selbst gesammelt

**Status:** ENTSCHEIDUNG offen — Henri wählt.
**Datum:** 2026-09-25
**Frage:** Welche kostenpflichtigen, gehosteten Quellen ersparen die eigene Aufzeichnung?

> **Nachtrag 2026-09-25: Henris EODHD-Token ist verifiziert — Plan „Free".**
> Gemessen, nicht vermutet: Intraday-Endpunkt antwortet **HTTP 403 „Only EOD data allowed for free users"**. EOD-Historie ist auf **1 Jahr** beschränkt (die API hängt an jeden Bar eine `warning`-Zeile). 20 Calls/Tag, 500 Extra.
> Heißt: **Für die Intraday-Uhr taugt der Token nicht.** Was er kann, steht in Abschnitt „Was der vorhandene Token wirklich leistet" am Ende.

## Warum die Frage überhaupt zählt

Der Plan v8 stellt den Intraday-Recorder in Phase 1, weil kostenlose Quellen nur ~8 Tage Minutenbars liefern und jeder Tag ohne Aufzeichnung ein Tag ist, den das Intraday-Modul später startet. Diese Uhr läuft nur, solange es keine gekaufte Historie gibt. **Kaufst du Historie, verschwindet der Zeitdruck** — die 12-Monats-Sperre aus dem Plan ist dann sofort erfüllt, weil die Historie schon existiert.

Das ändert die Reihenfolge des Projekts spürbar: Intraday-Arbeit kann in Phase 5b bleiben, statt in Phase 1 einen Recorder zu erzwingen.

## Die vier realistischen Optionen

Preise vom 2026-09-25 von den Anbieterseiten, nicht aus zweiter Hand.

### 1. FirstRate Data — einmalig kaufen, Historie gehört dir

| | |
|---|---|
| Preis | **399,95 $ einmalig** (ETF-Bundle, 5.140 Ticker) oder **599,95 $** (Stocks+ETFs, 16.309 Aktien + 5.140 ETFs + 7.000 delistete) |
| Abdeckung | Jan 2000 – Sep 2026, 1-min / 5-min / 30-min / 1-h / 1-Tag |
| Updates | 1 Monat frei, danach 59,95 $/Monat (ETF) bzw. 79,95 $/Monat (Bundle) |
| Form | ZIP-Download, keine API |
| Split/Dividende | angepasst **und** unangepasst enthalten |
| Out-of-hours | enthalten |

**Der entscheidende Punkt: 7.000 delistete Ticker.** Das ist der einzige Anbieter in dieser Preisklasse, der Survivorship-Bias ernst nimmt — und Plan v8 erklärt einen Zeitraum bei > 5 % fehlender Marktkapitalisierung für ungültig. Ohne delistete Ticker ist jeder Intraday-Backtest über mehrere Jahre systematisch zu optimistisch.

Nachteil: ein Download-Stand, kein laufender Feed. Für Research genau richtig, für den täglichen Betrieb brauchst du zusätzlich etwas Laufendes — entweder das Abo oder deinen eigenen Recorder ab Kaufdatum.

### 2. EODHD — Abo mit API, europäisch

| | |
|---|---|
| Preis | **29,99 €/Monat** (EOD+Intraday All World Extended), jährlich 24,99 €/Monat. **50 % Studentenrabatt für 12 Monate** → ~15 €/Monat |
| Abdeckung US | 1-min **seit 2004**, inkl. Pre-Market und After-Hours |
| Abdeckung sonst | 5-min und 1-h erst ab Oktober 2020; 1-min „nicht garantiert, variiert je Ticker" |
| Grenzen | 100.000 Calls/Tag, 1.000/min; je Request max. 120 Tage bei 1m, 600 Tage bei 5m |
| Verzug | Intraday final 2–3 h nach Handelsschluss |
| Lizenz | Private Nutzung; kommerziell separat |

**Die Falle steht im Kleingedruckten:** EODHD passt Intraday-Bars **nicht** rückwirkend für Splits und Dividenden an. Ein Bar von 2019 behält seinen Preis, auch nach einem 4:1-Split. Nur die EOD-API hat `adjusted_close`. Du müsstest die Anpassung also selbst über die Splitt-Historie rechnen — machbar, aber genau die Art stiller Fehler, die ein Backtest nicht meldet.

Für dich relevant: **Du bist Student.** 15 €/Monat trifft „ein bisschen was kosten" ziemlich genau, und die API passt zur geplanten Ingest-Schicht besser als ZIP-Dateien.

Zweite Einschränkung: Für deutsche/europäische Titel (Xetra) gibt es 1-Minuten nur „vielleicht". Wenn dein Universum US-lastig ist, egal. Wenn nicht, ist das ein echtes Loch.

### 3. Polygon.io — API-first, US-Aktien

| | |
|---|---|
| Preis | **29 $/Monat** Starter (Stocks), 79 $ Developer, 199 $ Advanced |
| Abdeckung | US-Aktien, **20 Jahre** Historie, unbegrenzte API-Calls |
| Starter-Grenze | 15 Minuten verzögert, keine Echtzeit |
| Format | REST + Flat Files (S3), gut dokumentiert |

Sauberste API der vier, korrekte Split-/Dividendenanpassung, Aggregates direkt als Minutenbars. Nur US. Der 15-Minuten-Verzug ist für dich irrelevant — du baust kein Echtzeitsystem, und Plan v8 verbietet Live-Orders ohnehin bis nach dem Paper Trading.

### 4. Databento — nach Verbrauch, Tick-Ebene

| | |
|---|---|
| Preis | Pay-as-you-go nach GB, kein Mindestabo; 125 $ Startguthaben |
| Abdeckung | Roh-Nachrichten von den Börsen, `ohlcv-1m` als abgeleitetes Schema |
| Stärke | Point-in-time korrekt, Nanosekunden-Zeitstempel, keine stillen Korrekturen |

Technisch die ehrlichste Quelle — und die einzige, die zum Point-in-time-Anspruch aus Plan v8 wirklich passt. Aber: Preis skaliert mit Datenmenge, und ein breites Universum über viele Jahre auf Minutenebene ist schnell teurer als die 600 $ von FirstRate. Für ein enges Universum (20–50 Titel) dagegen günstig.

## Vergleich auf einen Blick

| | FirstRate | EODHD | Polygon | Databento |
|---|---|---|---|---|
| Kosten Jahr 1 | 600 $ einmal | ~180 € (Student) | ~350 $ | variabel |
| Danach | 0 $ oder 80 $/Mon. | gleich | gleich | variabel |
| Historie 1-min | ab 2000 | ab 2004 (US) | ~20 J. | ab Börsenstart |
| Delistete Ticker | **ja, 7.000** | nein | teilweise | ja |
| Split-angepasst | **ja** | **nein (intraday)** | ja | roh |
| API | nein (ZIP) | ja | ja | ja |
| Europa | nein | eingeschränkt | nein | ja |
| Daten gehören dir | **ja** | nein | nein | ja |

## Meine Empfehlung

**FirstRate „Stocks and ETFs" für 599,95 $ einmalig** — wenn du das Geld einmal ausgeben willst.

Der Grund sind nicht die Minutenbars, die bekommst du überall. Es sind die **7.000 delisteten Ticker** plus die **angepasst/unangepasst-Doppelung**. Beides adressiert exakt die zwei Fehlerquellen, vor denen Plan v8 am lautesten warnt, und beides fehlt bei den Abos. Dazu: du kaufst einmal, die Dateien liegen bei dir, und es läuft kein Abo weiter, wenn das Projekt drei Monate ruht.

**Falls 600 $ zu viel sind: EODHD mit Studentenrabatt, ~15 €/Monat.** Dann aber mit offenen Augen — du musst die Split-Anpassung für Intraday selbst bauen, und das gehört als eigenes, getestetes Modul in die Datenschicht, nicht als Nebenbei-Korrektur.

**Nicht empfehlenswert für den Einstieg:** Databento. Technisch am besten, aber unvorhersehbare Kosten sind das Letzte, was ein Projekt braucht, das noch keine erste Zeile Code hat.

## Was sich am Plan ändert, sobald gekauft wird

1. **Ticket 01b (Intraday-Recorder) entfällt als Phase-1-Zwang.** Er wird optional und rutscht zu Phase 5b, wo der Rest der Intraday-Arbeit liegt.
2. **Die 12-Monats-Sperre ist sofort erfüllt** — die Historie existiert ja. Die restlichen Gates aus Spec §S1–S10 gelten unverändert: Kostenmodell, DSR ≥ 0,95, PBO ≤ 0,05, Paper Trading vor allem anderen.
3. **Neue Abhängigkeit in der Datenschicht:** ein Loader für das gekaufte Format, mit Prüfung gegen eine zweite Quelle auf Tagesebene (Prüfebene 2). Gekaufte Daten sind nicht automatisch richtige Daten.
4. **`apscheduler` bleibt trotzdem in Charge 1** — für Ingest-Jobs gebraucht, nicht nur für den Recorder.

## Was der vorhandene Token wirklich leistet

Am 2026-09-25 gegen die Live-API gemessen, Token liegt in `~/claude-local/trading-app/.env` (Rechte 600, außerhalb Git und iCloud).

**Konto:** Henri Bauer, `subscriptionType: free`, 20 Calls/Tag + 500 Extra-Limit.

| Endpunkt | Ergebnis | Belegt durch |
|---|---|---|
| `/api/intraday` 1m | **HTTP 403** | „Only EOD data allowed for free users" |
| `/api/intraday` 1h | **HTTP 403** | dieselbe Meldung |
| `/api/eod` US (AAPL, MSFT) | HTTP 200 | echte Bars mit `adjusted_close` |
| `/api/eod` Xetra (SAP.XETRA) | HTTP 200 | echte Bars — **europäische Titel gehen** |
| `/api/eod` älter als 1 Jahr | stillschweigend gekürzt | Abfrage für Jan 2015 lieferte 2025-09-25, mit `"warning": "Data is limited by one year as you have free subscription"` |
| `/api/splits` | HTTP 200 | AAPL 7:1 (2014), 4:1 (2020) |
| `/api/div` | HTTP 200 | mit `declarationDate` **und** `recordDate` |

### Die zwei Befunde, die zählen

**1. Intraday ist gesperrt.** Kein Minutenbar, kein Stundenbar, keine Umgehung. Die Uhr aus Plan v8 bleibt also stehen, und der Recorder bleibt vorerst in Phase 1.

**2. Die 1-Jahres-Grenze ist eine Leckage-Falle.** Die API wirft keinen Fehler, wenn du ältere Daten anforderst — sie gibt still einen kürzeren Zeitraum zurück und versteckt den Hinweis in einem `warning`-Feld pro Bar. Ein naiver Loader merkt davon nichts und hält einen 10-Jahres-Backtest für gültig, der in Wahrheit auf 12 Monaten steht. **Der Loader muss dieses Feld prüfen und hart abbrechen** — das gehört in Prüfebene 1, nicht in einen Kommentar.

### Wofür er trotzdem gut ist

- **`declarationDate` bei Dividenden.** Das ist der Tag, an dem eine Dividende öffentlich wurde — genau der Zeitstempel, den `PointInTimeView` braucht, um Lookahead zu vermeiden. Yahoo liefert das nicht.
- **Splits als saubere Zeitreihe** — Grundlage für eigene Anpassungsrechnung.
- **Xetra funktioniert**, im Gegensatz zu den meisten US-lastigen Gratisquellen.
- **Referenzquelle für Prüfebene 2:** Tages-Bars gegen `yfinance` gegenprüfen. Zwei unabhängige Quellen, die sich widersprechen, sind ein Fund; eine Quelle allein ist eine Annahme.

20 Calls/Tag reichen dafür — solange der Ingest cacht und nicht bei jedem Lauf neu zieht.

### Wenn Intraday gebraucht wird

Der Token lässt sich auf **„EOD+Intraday All World Extended", 29,99 €/Monat** hochstufen — mit dem 50 % Studentenrabatt ~15 €/Monat. Dann greift alles aus Option 2 oben, inklusive der Split-Falle: EODHD passt Intraday-Bars **nicht** rückwirkend an.

**Solange nicht hochgestuft wird, bleibt der Recorder in Phase 1.** Die Uhr läuft.

## Offene Entscheidung

Henri wählt eine Option. Bis dahin bleibt der Recorder in Phase 1 stehen, damit die Uhr im ungünstigsten Fall trotzdem läuft.
