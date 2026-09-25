# Rückwirkende Anpassung — was das heißt und warum es zählt

**Datum:** 2026-09-25
**Anlass:** Henris Frage „What does *adjust retrospectively* mean?"
**Kurzfassung:** Kurshistorie ist nicht fest. Bei Splits und Dividenden werden **alte** Kurse nachträglich umgerechnet. Wer das ignoriert, misst Renditen falsch — und zwar systematisch, nicht zufällig.

---

## 1. Das Problem in einem Satz

Der Kurs, den eine Aktie am 28. August 2020 hatte, ist heute nicht mehr derselbe Kurs, der damals auf dem Bildschirm stand.

Nicht weil jemand geschummelt hat, sondern weil die Aktie sich seither geteilt hat.

## 2. Splits: der Kurs halbiert sich, ohne dass jemand Geld verliert

Apple hat am **31.08.2020** einen **4:1-Split** gemacht — belegt durch den Splits-Endpunkt von EODHD, den ich gestern abgefragt habe:

```
2014-06-09  7.000000/1.000000
2020-08-31  4.000000/1.000000
```

Aus einer Aktie wurden vier. Wer 100 Stück zu ~500 $ hatte, hatte danach 400 Stück zu ~125 $. **Das Vermögen hat sich nicht geändert.** Nur die Stückelung.

Der Chart aber macht einen Sprung von 500 auf 125 — minus 75 % an einem Tag. Für jedes Programm, das stumpf `heute / gestern - 1` rechnet, sieht das aus wie ein Crash.

**Rückwirkende Anpassung** heißt: Der Datenanbieter geht in die Vergangenheit und teilt **alle** Kurse vor dem 31.08.2020 durch 4. Aus den 500 $ von damals werden nachträglich 125 $. Der Sprung verschwindet, die Kurve wird stetig, prozentuale Renditen stimmen wieder.

Der Preis dafür: **Die Zahl in deiner Datenbank ist nicht mehr die Zahl, die damals gehandelt wurde.** Wer prüfen will, ob eine Order von 2019 ausführbar gewesen wäre, braucht den *unangepassten* Kurs. Wer Renditen rechnet, braucht den *angepassten*. Beide werden gebraucht, für verschiedene Fragen.

## 3. Dividenden: der leisere Fall

Zahlt eine Firma 0,25 $ Dividende, fällt der Kurs am Ex-Tag um ungefähr diesen Betrag. Für den Aktionär ist nichts weg — das Geld ist nur vom Kurs aufs Konto gewandert. Für ein Programm, das nur Kurse sieht, ist es ein Verlust.

Rückwirkende Anpassung rechnet alle früheren Kurse um einen kleinen Faktor herunter, sodass die Rendite die Dividende mit einschließt.

### Gemessen, nicht behauptet

Ich habe heute 251 Tages-Bars von AAPL über EODHD geholt (25.09.2025 bis 24.09.2026) und `close` gegen `adjusted_close` gestellt:

```
Bars mit close != adjusted_close : 218 von 251

2025-09-25   close = 256.87   adj = 255.9246   diff = +0.9454
2026-09-24   close = 335.92   adj = 335.9200   diff =  0.0000

Rendite aus close          : +30.774 %
Rendite aus adjusted_close : +31.257 %
Fehler der naiven Rechnung : -0.483 Prozentpunkte
```

**In einem einzigen Jahr, bei einer Aktie mit magerer Dividendenrendite, ohne jeden Split: fast ein halber Prozentpunkt.** Bei zehn Jahren, bei Dividendenwerten, über ein ganzes Portfolio wird daraus ein Betrag, der jede Strategiebewertung wertlos macht.

Und die Richtung ist verräterisch: Die naive Rechnung liegt **zu niedrig**. Der Fehler ist keine Streuung, die sich über viele Titel ausmittelt — er zeigt konsequent in dieselbe Richtung. Genau solche Fehler halten Backtests am Leben, die sie eigentlich töten müssten.

## 4. Warum das bei EODHD-Intraday zum Problem wird

Für **Tages**-Daten liefert EODHD `adjusted_close` frei Haus — die Zahlen oben stammen daraus.

Für **Intraday**-Daten nicht. Aus der Anbieterdokumentation, geprüft am 24.09.2026:

> Intraday-Bars werden **nicht** um Splits und Dividenden bereinigt.

Ein 1-Minuten-Bar von AAPL aus dem Juli 2020 zeigt also heute noch ~380 $, während der Tages-Bar desselben Tages auf ~95 $ angepasst ist. Wer beide in dieselbe Tabelle schreibt, hat **zwei verschiedene Preiswelten in einer Spalte** — und merkt es erst, wenn eine Strategie unerklärlich gut aussieht.

Deshalb stand in meiner Empfehlung, dass beim Upgrade auf das Intraday-Abo ein eigenes Anpassungsmodul dazugehört. Das ist kein Kleinkram: Man braucht die Splits (hat EODHD), die Dividenden mit `declarationDate` (hat EODHD), und eine getestete Rechnung, die den kumulierten Faktor rückwärts durch die Historie zieht.

## 5. Was das für den Aufbau bedeutet

Drei Regeln, die ab Phase 1 in der Datenschicht verankert gehören:

**Beides speichern, nie nur eines.** Jeder Bar bekommt `close` *und* `adjusted_close`, plus den Anpassungsfaktor. Aus angepasst lässt sich unangepasst nicht zurückrechnen, wenn der Faktor fehlt.

**Renditen aus angepassten, Ausführbarkeit aus unangepassten Kursen.** Zwei Fragen, zwei Spalten. Eine Funktion, die beide vermischt, ist ein Bug — auch wenn sie nie crasht.

**Die Anpassung selbst ist bitemporal.** Ein Split vom Mai ändert die Bedeutung aller Kurse davor. Die Datenschicht muss beantworten können: *Wie sah diese Zeitreihe am 3. Mai aus, bevor der Split bekannt war?* Genau dafür ist `PointInTimeView` aus dem Plan da. Ohne diese Frage kann ein Backtest nicht ehrlich sein, denn die Strategie von damals kannte den Split noch nicht.

## 6. Antwort auf die eigentliche Frage

> „I might upgrade to the subscription later. But if that works for now, then we'll do it that way."

**Ja, das trägt.** Phase 1 baut die Datenschicht, und die braucht Tages-Daten — die liefert der Free-Token, inklusive `adjusted_close` und `declarationDate`.

Zwei Grenzen, die du kennen solltest:

**Ein Jahr Historie.** Heute nachgemessen: Eine Anfrage für Januar 2015 kam mit Daten von September 2025 zurück, ohne Fehler, mit dem Hinweis versteckt in einem `warning`-Feld pro Bar. Bei exakt einem Jahr fehlt das Feld. **Der Loader muss auf dieses Feld prüfen und abbrechen**, sonst hältst du irgendwann einen 10-Jahres-Backtest für gültig, der auf 12 Monaten steht. Das ist als Prüfebene-1-Test eingeplant.

**Kein Intraday.** Die Uhr aus Plan v8 bleibt stehen, bis du aufrüstest oder der eigene Recorder läuft.

Beim Upgrade (~15 €/Monat mit Studentenrabatt) ändert sich am Code nichts außer dem Plan-Feld — **wenn** die Datenschicht von Anfang an beide Preiswelten getrennt hält. Genau darum die drei Regeln oben. Sie jetzt einzuziehen kostet fast nichts; später nachzurüsten heißt, jede gespeicherte Zeitreihe neu zu laden.

---

## Quellen

- EODHD Splits-Endpunkt, Abruf 2026-09-25: AAPL 7:1 (2014-06-09), 4:1 (2020-08-31)
- EODHD EOD-Endpunkt, Abruf 2026-09-25: 251 Bars AAPL, Rechnung oben reproduzierbar
- EODHD-Doku zu Intraday: keine Split-/Dividendenbereinigung
- `docs/20260925_intraday-datenquellen.md` — Anbietervergleich
- `docs/20260925_trading-app-plan-v8.md` — `PointInTimeView`, Bitemporalität
