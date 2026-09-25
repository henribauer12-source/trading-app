# Die bitemporale Datenschicht

**Datum:** 2026-09-25
**Stand:** Phase 1, umgesetzt und geprüft
**Code:** `src/trading_app/bitemporal.py`, `src/trading_app/sources/eodhd.py`
**Tests:** `tests/test_bitemporal.py` (41), `tests/test_eodhd.py` (36)

---

## Worum es geht

Jede Bar trägt zwei Zeitstempel statt einem:

| Feld | Bedeutung | Beispiel |
|---|---|---|
| `event_time` | Wann ist es passiert? | AAPL-Schlusskurs vom 22.09., 22:00 UTC |
| `available_at` | Ab wann konnte man es wissen? | 22.09., 23:00 UTC |

Mit nur einem Zeitstempel lässt sich die entscheidende Frage nicht stellen:
*Was wusste ich an jenem Tag tatsächlich?* Genau diese Frage muss ein
Backtest beantworten, sonst rechnet er mit Wissen, das damals noch niemand
hatte — und liefert Ergebnisse, die in der Realität nicht eintreten.

Der Abstand zwischen beiden Feldern ist kein Detail. Eine Quartalszahl wird
für den 31. März ausgewiesen, veröffentlicht aber am 28. April. Wer sie ab
dem 31. März einrechnet, handelt vier Wochen lang mit Zahlen, die noch nicht
publiziert waren. Das ist der häufigste Weg, wie ein Backtest sich selbst
belügt.

---

## Die drei Regeln

### 1. Append-only

`BitemporalStore` hat kein `update()`, kein `delete()`, kein `upsert()`. Eine
geschriebene Zeile bleibt für immer.

Korrekturen sind neue Zeilen mit späterem `available_at`. Kommt für den 05.01.
zuerst ein Kurs von 100,00 und am 09.01. die Korrektur auf 101,50, stehen
danach **beide** in der Datenbank. Eine Abfrage per 06.01. sieht 100,00 — den
damals gültigen Wert, nicht den heute bekannten.

Das ist der Unterschied zwischen „was heute in den Büchern steht" und „was ich
damals wusste". Nur die zweite Frage taugt für einen Backtest.

Ein Test hält das mechanisch fest:

```python
for verboten in ("update", "delete", "upsert", "remove", "truncate"):
    assert not hasattr(store, verboten)
```

### 2. Jeder Zugriff geht über einen Stichtag

Es gibt keine Methode, die „alle Daten" liefert. Der einzige Weg zu Bars ist:

```python
sicht = store.view(dt.datetime(2026, 8, 15, tzinfo=UTC))
frame = sicht.bars("AAPL.US")
```

`PointInTimeView` hält den Stichtag fest und hängt ihn an jede Abfrage. Look-ahead
ist damit nicht eine Frage der Disziplin, sondern strukturell ausgeschlossen:
Die API bietet den Fehler gar nicht erst an.

Der Stichtag zählt einschließlich (`available_at <= as_of`) — eine Bar, die
exakt zum Stichtag verfügbar wurde, ist sichtbar.

### 3. Zeitstempel ohne Zeitzone werden abgewiesen

`Bar` lehnt naive `datetime`-Objekte ab. Grund: Ein naiver Zeitstempel wird
irgendwo stillschweigend als lokale Zeit gedeutet, und je nach Rechner
verschiebt sich derselbe Handelstag um Stunden. Dieser Fehler fällt nie
sofort auf.

---

## Die Eingangsprüfung

Sieben Regeln, bevor eine Bar überhaupt in die Datenbank darf. Jede hat einen
konkreten Anlass:

| Regel | Warum |
|---|---|
| Zeitzone verpflichtend | sonst tageweiser Versatz je nach Rechner |
| `available_at >= event_time` | nichts ist bekannt, bevor es passiert |
| `low <= open, close <= high` | unmögliche Bar = kaputte Quelle |
| Preise > 0 | negative Kurse gibt es bei Aktien nicht |
| Volumen >= 0 | ditto |
| kein NaN | rutscht sonst durch die Vergleiche |
| Symbol/Quelle nicht leer | sonst ist die Herkunft später nicht rekonstruierbar |

Die Prüfung sitzt bewusst im `Bar`-Objekt, nicht im Store: Es soll keinen Weg
geben, eine ungeprüfte Bar zu bauen. Rohe Tupel lehnt `append()` ausdrücklich
ab, sonst ließe sich die Prüfung umgehen.

---

## Die Leckage-Tests

Aus Abschnitt 3.3 der Qualitätsstandards. Sie prüfen die eine Eigenschaft,
an der alles hängt.

**Abschneide-Test.** Zu jedem beliebigen Stichtag gilt: keine sichtbare Bar hat
`available_at > Stichtag`. Geprüft über 2.000 zufällige Kombinationen aus
Stichtagen und Datenlagen (`hypothesis`) — nicht an drei handverlesenen
Beispielen.

**Zukunfts-Störtest.** Der eigentliche Beweis. Der Test schreibt zusätzliche
Bars mit absurden Kursen (Faktor 1.000) und späterem `available_at` in die
Datenbank und fragt dieselbe Sicht erneut ab. Das Ergebnis muss **Zeile für
Zeile identisch** sein. Wenn Daten aus der Zukunft das Ergebnis der
Vergangenheit verändern, leckt die Sperre — und dieser Test merkt es.

---

## Der EODHD-Adapter

Zwei Eigenheiten des Free-Plans, die beide still zu falschen Ergebnissen
führen:

**Die stille Kürzung.** Eine Anfrage ab Januar 2015 kommt mit Daten ab
September 2025 zurück. HTTP 200, keine Fehlermeldung. Der einzige Hinweis
steckt in einem `warning`-Feld an jeder Bar:

> „Data is limited by one year as you have free subscription"

Der Client **bricht hart ab**, statt zu warnen. Begründung: Eine Log-Warnung
übersieht man ein halbes Jahr lang, und in dieser Zeit steht jede Auswertung
auf zwölf statt zehn Jahren Daten. Eine Ausnahme übersieht man nicht.

Live geprüft am 25.09.2026 — Anfrage ab 2015 löst den Abbruch aus.

**Intraday gesperrt.** `/api/intraday` antwortet mit HTTP 403. Der Client
meldet das mit dem Hinweis auf den Abo-Pfad und die Anpassungsfalle, statt
einen nackten HTTP-Fehler durchzureichen.

**Zum `available_at`:** EODHD sagt nicht, wann genau Tagesdaten erscheinen.
Der Client setzt Börsenschluss plus Puffer (Vorgabe 1 Stunde). Zu spät kostet
Signalqualität, zu früh erzeugt Look-ahead. Im Zweifel zu spät — ein zu
vorsichtiger Backtest ist unangenehm, ein zu optimistischer wertlos.

---

## Warum die Tests geprüft wurden, bevor sie als Sicherung gelten

Ein Test, der eine bewusste Sabotage nicht rot meldet, ist wertlos. Also
wurden zehn gezielte Fehler in den Code gebaut und gemessen, ob die Suite
anschlägt:

| Sabotage | Ergebnis |
|---|---|
| PIT-Sperre entfernt | 6 Tests rot |
| Stichtag exklusiv statt einschließlich | 1 rot |
| Korrektur-Rangfolge umgedreht | 1 rot |
| Prüfung `available_at >= event_time` entfernt | 1 rot |
| naive Zeitstempel durchgelassen | 3 rot |
| Kürzungs-Abbruch zu Log-Warnung abgeschwächt | 3 rot |
| nur erste Bar auf `warning` geprüft | 1 rot |
| Verfügbarkeitspuffer entfernt | 3 rot |
| 403 generisch durchgereicht | 1 rot |
| Token in Fehlermeldung geschrieben | 1 rot |

**10 von 10 erkannt.** Danach alles zurückgesetzt, 77 Tests grün.

Dieselbe Prüfung hatte in Charge 1 eine echte Lücke aufgedeckt
(`test_lockfile_deckt_sich_mit_pyproject` blieb trotz Sabotage grün). Sie
bleibt deshalb Pflicht, bevor Tests als Sicherung gelten.

---

## Zeitzonen-Falle

DuckDB gibt Zeitstempel in der lokalen Zone zurück. Eine Bar, die als
14.08. 22:00 UTC hineingeht, kommt in Berlin als 15.08. 00:00+02:00 heraus.

Derselbe Augenblick, andere Schreibweise — aber es *sieht* nach einem Tag
Versatz aus und verleitet dazu, „korrigierend" einen echten Fehler
einzubauen. Zwei Tests in `TestZeitzonen` halten fest, worauf es ankommt:
der Augenblick zählt, nicht seine Darstellung.

---

## Was noch nicht da ist

- **Handelskalender.** `exchange-calendars` ist installiert, aber nicht
  angebunden. Die Frage „ist dieser Tag ein Handelstag" wird noch nicht
  gestellt.
- **Intraday.** Zurückgestellt bis Realtime-Daten bezahlbar sind. Die
  Datenschicht kennt bereits `bar_size`, Minutenbars bräuchten keine
  Schemaänderung.
- **Split-Anpassung für Intraday.** Erst relevant beim Upgrade, dann aber
  zwingend — siehe `20260925_rueckwirkende-anpassung.md`.
- **Lücken-Erkennung.** Fehlende Handelstage werden noch nicht gemeldet.

---

## Zahlen

| | |
|---|---|
| Produktivcode | 459 Zeilen (`bitemporal.py`) + 254 (`eodhd.py`) |
| Tests | 77, Laufzeit 1,8 s |
| Mutationstest | 10 Sabotagen, 10 erkannt |
| Live geprüft | 60 AAPL-Bars, Juli–September 2026 |
