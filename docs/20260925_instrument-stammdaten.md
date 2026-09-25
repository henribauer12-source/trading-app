# Instrument-Stammdaten für die ETF-Auswahl

**Datum:** 2026-09-25
**Stand:** umgesetzt und geprüft, nicht committet
**Spezifikation:** Anlage-Spezifikation v1.3, A5.1 und A5.2 (Ergänzungen v1.3 noch nicht unabhängig geprüft)
**Code:** `src/trading_app/stammdaten.py`, `src/trading_app/harte_filter.py`, `src/trading_app/sources/dokumente.py`
**Tests:** `tests/test_stammdaten.py`, `tests/test_harte_filter.py`, `tests/test_dokumente.py` — zusammen mit dem Bestand 266 grün

---

## Worum es geht

Die Datenschicht, auf der A5 später die Produktauswahl rechnet: TER, Tracking-Differenz,
Fondsvolumen und die übrigen Merkmale von ETFs und ETCs, dazu die harten Filter A5.2. Nicht
enthalten: die Bewertung A5.3, die Indexwahl A5.4, der Produktwechsel A5.6 und echte ISINs.

## Entwurf: eine Zeile je Feldwert

A5.1 verlangt die Herkunft **je Feld**. Die TER stammt aus dem KID vom Februar, das Fondsvolumen aus
dem Factsheet vom August. Gewählt ist deshalb eine schmale Tabelle `instrument_felder` mit einer
Zeile je Wert:
`isin, feld, periode, wert, einheit, quelle_url, quelle_typ, status, stand, abgerufen_am, ingested_at`.

- Ein neues Feld ist ein Eintrag in `FELDER`, keine Schemamigration.
- Jahreswerte (Tracking-Differenz) sind Zeilen mit `periode`, keine Spalten je Jahr.
- `wert` steht als Text in der Tabelle und wird in Python zu `Decimal`, `bool`, `date` oder einem
  Auswahlwert. Verworfen wurde eine DuckDB-`DECIMAL`-Spalte, weil sie still rundet (gemessen:
  `0.12345678901` → `0.1235` in `DECIMAL(18,4)`) und `.df()` sie in `float64` umwandelt.
- Verworfen wurde auch eine breite Tabelle mit einer Spalte je Feld: Für die Herkunft bräuchte sie
  vier Begleitspalten je Feld, oder eine Zeile je Dokument mit wieder nur einem Stand-Datum.

## Zeitachsen

| Spalte | Rolle wie in `bars` | Bedeutung |
|---|---|---|
| `stand` | `event_time` | Datum des Dokuments |
| `abgerufen_am` | `available_at` | ab wann die App den Wert kannte, Point-in-time-Schlüssel |
| `ingested_at` | `ingested_at` | wann die Zeile geschrieben wurde |

Unter mehreren bekannten Werten gilt der jüngste `stand`, bei gleichem Stand der spätere Abruf. Ein
Abruf vor dem Stand wird abgewiesen (in Python und als CHECK in der Tabelle, verglichen in UTC).

## Unverifizierte Werte

Jede Prüfung in `pruefe_harte_filter` endet mit *erfüllt*, *verletzt* oder *offen*. Ein fehlender
oder UNVERIFIZIERT-Wert ergibt *offen*; das Produkt ist dann nicht zulässig. Das ist weder eine
Ausnahme (die würde bei einem einzigen ungeprüften Wert die Auswertung aller Kandidaten abbrechen)
noch eine bloße Warnung (die ließe das Produkt durch).

## Rechtliche Grenzen im Code

Es gibt keinen Scraper. Die Werte kommen aus einer von Hand gepflegten JSON-Datei
(`lade_quelldatei`; das Format steht im Modul-Docstring). `sources/dokumente.lade_dokument` lädt
genau ein PDF und nimmt dabei nur https-Adressen, deren Pfad auf `.pdf` endet und die keine Query
haben. Adressen mit einem Host-Label, das mit `justetf` oder `vanguard` beginnt, werden vor jeder
Verbindung abgewiesen, auch als Weiterleitungsziel.

Die Quelldatei gehört ins Repo, weil sie versioniert werden soll, aber **nicht nach `data/`**: Dieser
Pfad steht in `.gitignore`.

## Mutationsprüfung

Jede Sabotage lief in einer frischen Kopie von `src/` und `tests/` mit `PYTHONDONTWRITEBYTECODE=1`
(siehe `wiki/python-pyc-invalidation.md`). Der Arbeitsbaum blieb dabei unberührt. Eine Kontrolle
ohne Mutation ergab 0 rote Tests.

| # | Sabotage | rot |
|---|---|---|
| M1a | PIT-Filter entfernt (`feld`/`reihe`) | 9 |
| M1b | PIT-Filter entfernt (`isins`) | 3 |
| M2a | Stichtag `<=` → `<` (`feld`/`reihe`) | 2 |
| M2b | Stichtag `<=` → `<` (`isins`) | **0**, nach neuem Test 1 |
| M3 | Volumen-Filter 100 Mio. → 10 Mio. | 4 |
| M4 | Historie-Filter 3 → 1 Jahr | 2 |
| M5a | Domain-Sperrliste leer | 13 |
| M5b | Weiterleitungsprüfung ausgebaut | 1 |
| M6a | `Decimal` → `float` beim Speichern | 2 |
| M6b | `float` als Eingabe zugelassen | 1 |
| M6c | Quelldatei liest `float` statt `Decimal` | 4 |
| M7 | UNVERIFIZIERT besteht still | 4 |
| M8 | Vorrang ignoriert das Stand-Datum | 1 |
| M9 | K1-/Geldmarkt-Schwelle 500 → 100 Mio. | 3 |
| M10 | Abruf vor Stand zugelassen | 1 |
| M11 | ISIN-Prüfziffer ignoriert | 1 |
| M12 | Wert aus zweiter Hand darf VERIFIZIERT sein | 1 |
| M13 | „nicht an Xetra“ → verletzt statt offen | 1 |
| M14 | Jahreswert vor Jahresende zugelassen | 1 |
| M15 | Duplikatprüfung beim Anhängen entfernt | 1 |
| M16 | Auflage am 1. Januar zählt nicht | 2 |
| M17 | Gold prüft UCITS statt Lieferanspruch | 1 |
| M18 | Tabellen-CHECK Abruf ≥ Stand entfernt | **0**, nach neuem Test 2 |
| M19 | Tabellen-CHECK ohne UTC-Umrechnung | 2 |

Ergebnis: 24 Sabotagen, am Ende alle erkannt. Zwei blieben zunächst unbemerkt:

- M2b fand der erste Lauf.
- M18 fand die unabhängige Prüfung.

Für beide kam ein Test hinzu, danach wurden sie erkannt. M19 fällt nur auf einem Rechner östlich
von UTC auf (hier Europe/Berlin); auf einem UTC-Rechner ist diese Mutation gleichwertig mit dem
Original.

## Offen in der Spezifikation

Die Stellen, die v1.3 geregelt hat, stehen in A5.1 und A5.2. Offen sind noch:

1. **Filter 2 für Anleihen, Gold und Faktor:** A5.5 nennt dort nur Indexfamilien. Diese Prüfung
   bleibt *offen*, bis A5.5 konkrete Indexnamen nennt, und damit ist bis dahin kein Produkt dieser
   Bausteine zulässig.
2. **Schreibweise des Index:** Für A5.3 („derselbe Index“) muss die Variante (Net/Gross,
   Währung) eindeutig sein. v1.3 legt nur für K1 und den Geldmarkt die Schreibweise von A5.5 fest.
3. **Fondsvolumen in Fremdwährung:** Viele Factsheets nennen USD. Ungeklärt sind Kurs und Stichtag
   der Umrechnung, und ob das Volumen des Fonds oder das der Anteilsklasse zählt. Das Feld nimmt
   nur EUR an.
4. **Schließungsankündigung:** A5.6 nennt sie als Verletzung eines harten Filters, A5.2 enthält
   dafür aber keinen Filter.
5. **Replikation „synthetisch, mehrere Gegenparteien“:** A5.3 vergibt 75 Punkte nur bei
   *transparenten Sicherheiten*. Wie ein Fonds mit mehreren Gegenparteien ohne transparente
   Sicherheiten zu werten ist, bleibt offen.
6. **„Jahre seit Auflage“ (A5.3, Historie) gegen „volle Kalenderjahre“ (A5.2 Nr. 4):** zwei
   verschiedene Altersmaße.
7. **„Niedrige Frequenz“ (A5.1):** Es gibt keine Zahl; der Download setzt kein Tempolimit durch.
8. **Filter 7 (sparplanfähig, P15):** nutzerbezogen, nicht in dieser Schicht.
