---
title: Trading-Analyse-App – Strategie-Katalog (Phase 0)
date: 20260925
status: v1.1, unabhängig geprüft, Befunde eingearbeitet
owner: Henri
basis: 20260925_trading-app-plan-v8.md, 20260925_rechenkern-spezifikation-v1.4.md
---

# Strategie-Katalog v1.1 (Phase 0)

## 0. Kurzfassung

Der Katalog formalisiert **8 Kern- und Kandidatenstrategien**, **4 Optionsstrategien für Phase 7** und eine **Kontrollgruppe von 11 populären Regeln**. Jede Strategie hat eine exakte Regel mit Parametern aus der Primärquelle, einen Evidenzgrad, die erklärten Abweichungen von der Quelle und eine YAML-Definition. Reproduktionsziele und Look-ahead-Fallen stehen gesammelt in Abschnitt 9. Damit ist das Gate von Phase 0 erfüllt (mindestens 8 formalisierte Strategien mit Evidenzgrad).

**Was die Research ergeben hat:**
- **Robust und mit kostenlosen Daten umsetzbar:** passives Weltportfolio mit Rebalancing; Faber-Trendfilter (vor allem als Drawdown-Schutz); Trendfolge auf ETFs und Gold-ETCs
- **Mit deutlichen Einschränkungen:** Momentum über Anlageklassen (anders konstruiert als in der Quelle), Aktien-Momentum und 52-Wochen-Hoch (Survivorship-Bias, nur Long-Seite, zunächst nur USA), volatilitätsgesteuerter Aktienanteil (gemischte Out-of-sample-Evidenz)
- **Nach Kosten oder seit Veröffentlichung tot:** kurzfristige Umkehr und Post-Earnings-Drift bei großen Aktien; sie bleiben als Lernbeispiele in der Kontrollgruppe
- **Populäre Retail-Regeln** (gleitende Durchschnitte, Golden Cross, RSI, Bollinger, Kerzenmuster): seit 1987 nach Kosten und Mehrfachtests keine Evidenz. Die App testet sie trotzdem, damit du es an echten Daten siehst
- **Intraday:** Nur Intraday-Momentum in der letzten halben Stunde hat begutachtete Evidenz, und selbst die ist in einer Out-of-sample-Studie verschwunden. Die bekanntesten Intraday-Strategien stammen aus nicht begutachteten Papieren von Autoren mit kommerziellem Interesse. **I1 kann frühestens nach etwa 3 Jahren eigener Daten die Gates bestehen**
- **Nicht umsetzbar bei 0 €:** Rohstoff-Carry (braucht Futures-Kurven)

| ID | Strategie | Modul | Rolle | Evidenz | Daten 0 € |
|---|---|---|---|---|---|
| L1 | Passives Weltportfolio mit Rebalancing | Langfrist | Kern und Benchmark | A | Ja |
| L2 | Faber-Trendfilter (GTAA 5) | Langfrist | Kern | B (Drawdown), C (Rendite) | Ja |
| L3 | Anlageklassen-Rotation nach Momentum | Langfrist | Kandidat | C | Ja |
| L4 | Volatilitätsgesteuerter Aktienanteil | Langfrist | Kandidat | C | Ja |
| S1 | Trendfolge (TSMOM 1/3/12), long/flat | Swing | Kern | B | Ja |
| S2 | Aktien-Momentum 12-1, long-only, USA | Swing | Kandidat | C | Teilweise |
| S3 | 52-Wochen-Hoch-Momentum, long-only, USA | Swing | Kandidat | C | Teilweise |
| I1 | Intraday-Momentum letzte halbe Stunde | Intraday | Kandidat | C | Nur eigene Aufzeichnung |
| O1–O4 | Put-Credit-Spread, Covered Call, Vertikal-Spreads, Schutzput | Optionen | Kandidaten Phase 7 | C | Teilweise |
| K1–K11 | Populäre Regeln, Kosten- und Zerfallsbeispiele | Kontrolle | Kontrolle | D | Ja |

**Prüfstatus der Zahlen:** Die meisten Werte wurden von zwei Seiten geprüft (Recherche im Volltext, unabhängige Prüfung). Nur von einer Seite geprüft sind: Jegadeesh & Titman (1993), Barroso & Santa-Clara (2015), Daniel & Moskowitz (2016), Sullivan et al. (1999), Chague et al. (2020). Sie sind im Text mit "einfach geprüft" markiert.

---

## 1. Evidenzskala und Rollen

| Grad | Bedeutung |
|---|---|
| **A** | Mehrere begutachtete Studien, verschiedene Märkte und Zeiträume, hält nach realistischen Retail-Kosten |
| **B** | Begutachtete Evidenz mit Out-of-sample-Bestätigung, aber kostenempfindlich, zerfallend oder nur teilweise mit Retail-Instrumenten umsetzbar |
| **C** | Einzelstudie, gemischte Out-of-sample-Evidenz, nur brutto belegt, oder so weit von der Quelle abgewandelt, dass deren Evidenz nur eingeschränkt gilt |
| **D** | Keine Evidenz, negative Evidenz nach Kosten, seit Veröffentlichung verschwunden, oder nur nicht begutachtete Behauptungen von Anbietern |

| Rolle | Bedeutung in der App |
|---|---|
| Kern | Wird zuerst gebaut und getestet; zeigt nach bestandenen Gates Signale |
| Kandidat | Wird getestet; zeigt Signale nur, wenn alle Gates bestanden sind |
| Kontrolle | Wird mit derselben Engine getestet, um zu zeigen, dass die Prüfung Unsinn verwirft; Ergebnisse erscheinen im Bereich Evidenz und im Lernmodul, **nie** als Signal. Besteht eine Kontrollregel wider Erwarten alle Gates, wird das als möglicher Fehler der Engine untersucht |
| Nicht umsetzbar | Dokumentiert, aber nicht gebaut |

---

## 2. Allgemeine Regeln für alle Strategien

**G1 Parameter aus der Quelle.** Jede Strategie startet mit den Parametern ihrer Primärquelle. Varianten sind nur erlaubt, wenn sie in der Quelle selbst oder in begutachteter Folgeliteratur vorkommen; sie werden vorab im Katalog gelistet. Nachträgliche Parametersuche ist verboten.

**G2 Ausführung.** Signale auf abgeschlossenen Bars, Ausführung frühestens zum Eröffnungskurs der nächsten Bar (C4, E1–E13). Viele Quellen handeln zum Signalkurs; diese Abweichung ist gewollt und macht die App konservativer.

**G3 Instrumente.** Fonds nur als UCITS-ETFs oder ETCs. Keine Leerverkäufe und kein Hebel in Langfrist und Swing, solange Lernstufe 5 nicht abgeschlossen ist (R4). Long/Short-Varianten sind als "Phase-5-Variante" markiert. **Ausnahme Kontrollgruppe:** Kontrollregeln werden auf den Instrumenten der Quelle getestet (z. B. US-ETFs), weil sie nie Signale erzeugen und nur die Prüfung demonstrieren.

**G4 Datenproxies und Währung.**
- Für Backtests vor Auflage eines UCITS-Produkts wird die Indexhistorie über einen US-gelisteten ETF gleicher Indexbasis verlängert. Die Übergangsstelle wird im Ergebnis markiert. Proxies dienen **nur** dem Backtest
- **Anpassungen des Proxys:** Die Ausschüttungen des US-Proxys werden um 15 % gekürzt (Quellensteuer eines irischen UCITS-Fonds auf US-Dividenden laut Doppelbesteuerungsabkommen; Satz UNVERIFIZIERT, vor Implementierung prüfen), und die Differenz der laufenden Kosten (TER) wird täglich abgezogen
- **Umrechnung in EUR:** EZB-Referenzkurs desselben Tages (veröffentlicht gegen 16:00 MEZ, also vor dem US-Schlusskurs; kein Look-ahead, aber bis zu 6 Stunden älter als der Schlusskurs, was tägliche Statistiken verrauscht). An TARGET-Feiertagen ohne Referenzkurs wird der letzte Kurs fortgeschrieben und markiert (K12). Vor 19990104 wird ein synthetischer EUR-Kurs aus dem DM/USD-Kurs (FRED) und dem festen Umrechnungskurs 1,95583 DM/EUR gebildet
- **Bewertungskalender:** je Strategie ein Kalender, und zwar der des Handelsplatzes des gehaltenen UCITS-Produkts (in der Regel Xetra). "Letzter Handelstag des Monats" bezieht sich auf diesen Kalender
- ENTSCHEIDUNG

**G5 Cash und Zinsen.** Nicht investiertes Kapital verzinst sich mit dem risikofreien Zins:
- ab 20191001 €STR; von 19990104 bis 20190930 EONIA − 8,5 Basispunkte (die EZB hat EONIA ab Oktober 2019 als €STR + 8,5 Basispunkte definiert; der Abstand wird als Näherung auch rückwirkend verwendet); vor 1999 der Frankfurter Tagesgeldsatz der Bundesbank (Verfügbarkeit als kostenlose Zeitreihe UNVERIFIZIERT)
- **Veröffentlichung:** €STR wird am folgenden Geschäftstag veröffentlicht. Zum Bewertungszeitpunkt t werden nur Zinssätze mit available_at ≤ t verwendet; für den letzten Tag gilt der Vortagessatz

**G6 Veröffentlichungseffekt und Stichprobe.**
- Jede Strategie hat im YAML das **Ende der Stichprobe ihrer Quelle** (`stichprobenende`), nicht nur das Veröffentlichungsjahr
- **Die Gates (G7) werden ausschließlich auf Daten nach dem Stichprobenende geprüft.** In diesem Zeitraum hat die Quelle ihre Parameter nicht gewählt. Der Gesamtzeitraum wird nur zur Information gezeigt
- Reicht der Zeitraum nach dem Stichprobenende nicht für MinTRL (S4), gilt die Strategie als "nicht ausreichend belegt" und zeigt keine Signale
- **Erwartete Live-Wirkung** in der Anzeige: die aktive Rendite gegenüber dem Benchmark (G8) nach dem Stichprobenende; liegt dafür weniger als MinTRL vor, die aktive Rendite des Gesamtzeitraums mit **60 % Abschlag** (McLean & Pontiff, 2016: 58 % Rückgang nach Veröffentlichung). Der Abschlag gilt nur für die aktive Rendite, nicht für die Marktrendite
- ENTSCHEIDUNG

**G7 Gates (alle müssen erfüllt sein, bevor eine Strategie Signale zeigt):**
1. Alle Leckage-Tests grün (Qualitätsstandards Abschnitt 3.3)
2. **Aktive Rendite** (Strategie minus Gate-Benchmark nach G8, beide nach Kosten) mit DSR ≥ 0,95 über alle gezählten Versuche nach G9; PSR, DSR und MinTRL werden auf der aktiven Rendite berechnet (SR* = 0 für die aktive Rendite)
3. t-Wert der mittleren aktiven Rendite (Newey-West) ≥ 3,0 (Harvey, Liu & Zhu, 2016, empfehlen diese Schwelle wegen der Vielzahl getesteter Faktoren; nicht eingesehen)
4. Mit doppelten Kosten bleibt die aktive Rendite positiv, sonst Kennzeichnung "kostensensitiv"; im Intraday-Modul dann keine Signale
5. Verfügbarer Zeitraum nach dem Stichprobenende ≥ MinTRL
6. Kein "Zu gut"-Alarm (S10) offen
7. **PBO ≤ 0,05 nur, wenn die App eine Variante statt der Quellenregel verwendet.** Die Quellenregel selbst wird nicht per PBO geprüft, weil sie nicht aus den Varianten ausgewählt wurde; die Varianten dienen dann nur als Robustheitsbericht
8. **Risiko-Gate für L2 und L4** (Strategien, deren Nutzen laut Quelle im Risiko liegt), ersetzt Gate 2 und 3:
   - Benchmark: statische Mischung mit der **durchschnittlichen Investitionsquote der Strategie je Anlageklasse** über den Prüfzeitraum, monatlich rebalanciert, Rest in Cash. So kann bloßes Weniger-Risiko-Nehmen das Gate nicht bestehen
   - Kriterium: Calmar-Ratio (CAGR / maximaler Drawdown) der Strategie minus der der statischen Mischung > 0, einseitig 95 %, gepaarter stationärer Bootstrap (S6) über dieselben Zeitblöcke
   - Hinweis: Die durchschnittliche Investitionsquote wird aus dem gesamten Prüfzeitraum berechnet. Das ist für eine Bewertung nach dem Test zulässig, weil der Benchmark nicht handelt
- ENTSCHEIDUNG

**G8 Benchmarks.** Der **erste** Benchmark im YAML ist der Gate-Benchmark; weitere werden informativ gezeigt. Ausnahme: Bei S2 und S3 müssen beide Benchmarks bestanden werden (wie PE10).

| Modul | Gate-Benchmark |
|---|---|
| Langfrist | L1 mit gleicher Aktienquote (Aktienquote der Strategie = Durchschnitt ihres Aktienanteils über den Prüfzeitraum); bei L2 und L4 das Risiko-Gate aus G7 |
| Swing Multi-Asset (S1) | Dasselbe Universum, immer long, mit denselben inversen Volatilitätsgewichten, monatlich rebalanciert |
| Swing Aktien (S2, S3) | Kapitalgewichtetes **und** gleichgewichtetes Universum (PE2), gleiche Umschichtungstermine und Kosten |
| Intraday (I1) | "Immer long in der letzten halben Stunde" auf demselben Instrument |

**G9 Zählung der Versuche.**
- Ein **Versuch** ist eine eindeutige Konfiguration (Hash der YAML-Datei samt Daten- und Kostenversion). Wiederholte Läufe derselben Konfiguration zählen nicht erneut
- **Ein gemeinsames N über alle Familien, die Signale erzeugen können** (Langfrist, Swing, Intraday, Optionen). Die Kontrollgruppe hat ein eigenes N, weil sie nie Signale erzeugt
- Die Auswahl dieser Strategien aus der Literatur ist selbst eine Selektion, die sich nicht sauber zählen lässt; Gate 3 (t ≥ 3) und Gate 7 dienen als Ausgleich
- ENTSCHEIDUNG

---

## 3. YAML-Schema der Strategie-Bibliothek

```yaml
id: S1
name: "Trendfolge TSMOM 1/3/12, long/flat"
modul: swing                     # langfrist | swing | intraday | optionen | kontrolle
rolle: kern                      # kern | kandidat | kontrolle | nicht_umsetzbar
evidenz: B                       # oder {drawdown: B, rendite: C}
quellen: [MOP2012, HOP2017]
stichprobenende: 2009-12         # Ende der Quellenstichprobe (G6)
freischaltung: lernstufe_3
universum: {typ: liste, elemente: [GOLD_ETC, SILBER_ETC, ROHSTOFFE_BREIT]}   # oder {typ: regel, regel: PE2}
daten: [tagesschluss_total_return, zins_eur]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung # C4, E1
aufwaermphase: {handelstage: 600}
signal: tsmom_kombiniert         # Funktion im Rechenkern
parameter: {}                    # fest aus der Quelle
bindungen: {regel: hoehere_marktkapitalisierung}
varianten: []                    # nur aus Quelle oder begutachteter Folgeliteratur (G1)
kosten_profil: etf_etc
benchmark: [gate_benchmark, info_benchmark]
gates: standard                  # oder risiko_gate (G7 Punkt 8)
abweichungen: []                 # Liste der erklärten Abweichungen von der Quelle
phase5_variante: null
```

---

## 4. Modul Langfrist

### L1 Passives Weltportfolio mit Rebalancing (Kern, Benchmark)

**Evidenz A.** Bei 66.465 US-Haushalten (1991–1996) erzielte das aktivste Fünftel 11,4 % pro Jahr netto, der Markt 17,9 %, das am wenigsten aktive Fünftel 18,5 % (Barber & Odean, 2000). In Taiwan verloren Privatanleger durch Handel 3,8 Prozentpunkte pro Jahr (Barber et al., 2009).

**Regel:**
- Bausteine: Welt-Aktien (UCITS-ETF auf einen breiten Weltindex) und EUR-Staatsanleihen (UCITS-ETF, Laufzeitmix)
- Zielgewichte nach Risikoprofil, Standard **70 / 30**, einstellbar in 10er-Schritten
- Monatliche Prüfung am letzten Handelstag; weicht ein Baustein mehr als 5 Prozentpunkte vom Ziel ab, wird **auf die Zielgewichte** umgeschichtet; unabhängig davon jährlich am letzten Handelstag des Jahres
- Sparplan (nur Simulator und Betrieb): Einzahlungen gehen zuerst in den untergewichteten Baustein. Backtests rechnen zeitgewichtet ohne Zahlungsflüsse
- Rebalancing-Parameter: **ENTSCHEIDUNG** (keine begutachtete Evidenz für eine optimale Frequenz oder Schwelle gefunden)

```yaml
id: L1
name: "Passives Weltportfolio mit Rebalancing"
modul: langfrist
rolle: kern
evidenz: A
quellen: [BO2000, BLLO2009]
stichprobenende: 1996-12
freischaltung: keine
universum: {typ: liste, elemente: [AKTIEN_WELT, ANLEIHEN_STAAT_EUR]}
daten: [tagesschluss_total_return]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {handelstage: 0}
signal: rebalancing_schwelle
parameter: {zielgewichte: {AKTIEN_WELT: 0.70, ANLEIHEN_STAAT_EUR: 0.30}, schwelle_prozentpunkte: 5, ziel: zielgewichte, pflicht: jaehrlich}
varianten: []
kosten_profil: etf
benchmark: [selbst]
gates: keine                      # ist der Benchmark
abweichungen: ["Rebalancing-Regel ist eigene Festlegung, keine Quellenregel"]
```

### L2 Faber-Trendfilter, GTAA 5 (Kern)

**Evidenz B für geringeren Drawdown, C für höhere Rendite.**
- Faber (2007), Update 2013: 1973–2012 Buy-and-hold 9,92 % Rendite, 10,28 % Volatilität, Sharpe 0,44, maximaler Drawdown −46,00 %; mit Trendfilter 10,48 %, 6,99 %, 0,73, −9,54 %. Nach der Originalstichprobe (2006–2012): 3,94 % / 0,16 / −46,00 % gegenüber 6,01 % / 0,61 / −9,42 %. Robustheit über 3/6/9/12-Monats-Durchschnitt: Sharpe 0,60/0,72/0,77/0,73
- Zakamulin (2014): Leistung von Trendfiltern mit realistischen Kosten und Out-of-sample-Tests "stark überzeichnet". Clare et al. (2016): Trendfolge über mehrere Anlageklassen risikoadjustiert besser als Buy-and-hold

**Regel:**
- Fünf Anlageklassen zu je 20 %: US-Aktien, Aktien Industrieländer ohne USA, Staatsanleihen, breite Rohstoffe, globale Immobilienaktien
- Je Klasse unabhängig am letzten Handelstag des Monats: Monatsschlusskurs (Total Return) > Durchschnitt der letzten 10 Monatsschlusskurse einschließlich des aktuellen → investiert; < → Cash; Gleichstand → vorheriger Zustand; **Startzustand Cash**, bis das erste eindeutige Signal vorliegt
- Ausführung zur nächsten Eröffnung

**Abweichungen von der Quelle:** UCITS-Produkte in EUR statt US-Indizes in USD, EUR- statt US-Staatsanleihen, Signal auf der EUR-Kursreihe (Wechselkurse fließen ein), Ausführung zur nächsten Eröffnung statt zum Schlusskurs, Kosten berücksichtigt, Cash mit EUR-Zins statt T-Bills.

**Bekannte Schwächen:** Fehlsignale in V-förmigen Märkten; hinkt in starken Haussen hinterher (2006–2012 nur in 3 von 7 Jahren besser); jeder Ausstieg realisiert in Deutschland Abgeltungsteuer (nicht im Backtest, nur in der Anzeige nach C8).

```yaml
id: L2
name: "Faber-Trendfilter GTAA 5"
modul: langfrist
rolle: kern
evidenz: {drawdown: B, rendite: C}
quellen: [FABER2007, FABER2013, ZAKAMULIN2014, CLARE2016]
stichprobenende: 2005-12
freischaltung: lernstufe_2
universum: {typ: liste, elemente: [AKTIEN_USA, AKTIEN_INDUSTRIE_EXUS, ANLEIHEN_STAAT_EUR, ROHSTOFFE_BREIT, IMMOBILIEN_GLOBAL]}
daten: [tagesschluss_total_return, zins_eur]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {monate: 10}
signal: sma_trendfilter
parameter: {sma_monate: 10, gewicht_je_klasse: 0.20, gleichstand: vorheriger_zustand, startzustand: cash}
varianten:                        # Faber 2013, Abb. 15
  - {name: sma_3, sma_monate: 3}
  - {name: sma_6, sma_monate: 6}
  - {name: sma_9, sma_monate: 9}
  - {name: sma_12, sma_monate: 12}
kosten_profil: etf
benchmark: [risiko_gate_statische_mischung, buy_and_hold_gleiche_klassen, L1]
gates: risiko_gate
abweichungen: [ucits_eur, anleihen_eur, naechste_eroeffnung, kosten, cash_eur]
```

### L3 Anlageklassen-Rotation nach Momentum (Kandidat)

**Evidenz C.** Die Quelle (Asness, Moskowitz & Pedersen, 2013, Tab. I) zeigt Momentum **innerhalb** von Anlageklassen: Länderindizes 8,7 % pro Jahr (t = 4,14, Sharpe 0,73), Rohstoffe 12,4 % (t = 3,29), Anleihen 0,4 % (t = 0,35, kein Effekt); über alle Klassen einschließlich Einzelaktien 5,0 % (t = 4,18, Sharpe 0,67). L3 vergleicht dagegen verschiedene Anlageklassen **miteinander** (Aktien gegen Anleihen gegen Gold). Das ist eine andere Strategie, für die die Quelle nur eingeschränkt gilt; daher Grad C.

**Regel:**
- Universum: 10 Anlageklassen: Aktien USA, Europa, Japan, Pazifik ohne Japan, Schwellenländer; EUR-Staatsanleihen, EUR-Unternehmensanleihen; Gold; breite Rohstoffe; globale Immobilienaktien
- Signal MOM_2-12 = kumulierte Total-Return-Rendite von Monatsende t−12 bis t−1 (letzter Monat ausgelassen)
- Berücksichtigt werden nur Klassen mit mindestens 13 Monaten Historie; gehalten werden die ⌈n/3⌉ Klassen mit dem höchsten Signal, gleichgewichtet. Bindungen: die Klasse mit der geringeren 12-Monats-Volatilität zuerst
- Bewertung am letzten Handelstag des Monats, Ausführung zur nächsten Eröffnung

**Varianten (aus der Quelle):** ohne Auslassen des letzten Monats (die Autoren nennen stärkere Ergebnisse ohne Auslassung für Nicht-Aktien). Der absolute Filter nach Antonacci ("Dual Momentum") ist **nicht begutachtet** und daher nach G1 keine Variante; er wird nur im Lernmodul erklärt.

```yaml
id: L3
name: "Anlageklassen-Rotation nach Momentum"
modul: langfrist
rolle: kandidat
evidenz: C
quellen: [AMP2013, MP2016]
stichprobenende: 2011-12
freischaltung: lernstufe_2
universum: {typ: liste, elemente: [AKTIEN_USA, AKTIEN_EUROPA, AKTIEN_JAPAN, AKTIEN_PAZIFIK_EXJP, AKTIEN_EM, ANLEIHEN_STAAT_EUR, ANLEIHEN_UNTERNEHMEN_EUR, GOLD_ETC, ROHSTOFFE_BREIT, IMMOBILIEN_GLOBAL]}
daten: [tagesschluss_total_return]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {monate: 13}
signal: querschnitt_momentum
parameter: {lookback_monate: 12, auslassen_monate: 1, anteil_halten: 0.3333, rundung: aufrunden, gewichtung: gleich}
bindungen: {regel: geringere_volatilitaet_12m}
varianten:
  - {name: ohne_auslassen, auslassen_monate: 0}
kosten_profil: etf
benchmark: [L1, buy_and_hold_gleiche_klassen]
gates: standard
abweichungen: [vergleich_zwischen_klassen_statt_innerhalb, long_only, ucits_eur]
```

### L4 Volatilitätsgesteuerter Aktienanteil (Kandidat)

**Evidenz C (gemischt).**
- Moreira & Muir (2017), Marktportfolio 1926–2015: Alpha 4,86 % pro Jahr; mit 10 Basispunkten Kosten 3,98 %; **ohne Hebel (Gewicht ≤ 1): Alpha 2,12 %, Break-even-Kosten 110 Basispunkte, Sharpe 0,52 gegenüber 0,42 für den Markt** (in der JF-Fassung bestätigt)
- Cederburg et al. (2020): Über 103 Strategien schlagen gesteuerte Portfolios die ungesteuerten nicht systematisch; Echtzeit-Versionen meist schlechter
- Barroso & Detzel (2021): Nach Kosten bleibt nur die Steuerung des Marktportfolios robust, und nur bei hoher Anlegerstimmung

**Regel:**
- Anteil Welt-Aktien-ETF w_t = min(1; c_t / σ̂²_t), Rest in Cash; kein Hebel
- σ̂²_t = Summe der quadrierten Abweichungen der einfachen Tagesrenditen vom Monatsmittel über die Handelstage des Monats t
- c_t: so gewählt, dass die **ungedeckelte** gesteuerte Reihe auf allen Daten bis Monatsende t dieselbe Volatilität hat wie der ungesteuerte Markt (expandierendes Fenster). Die Quelle bestimmt c über den Gesamtzeitraum, was Look-ahead enthält; genau das kritisieren Cederburg et al.
- Aufwärmphase: 120 Monate Daten vor dem ersten Signal (Stabilität von c_t)
- Bewertung am letzten Handelstag, Ausführung zur nächsten Eröffnung; das Gewicht für Monat t+1 nutzt nur Daten bis t (kein Look-ahead)

**Abweichungen:** Welt-Aktien in EUR statt US-Markt in USD; Cash mit EUR-Zins statt T-Bills; c in Echtzeit statt über den Gesamtzeitraum; Deckel bei 1.

```yaml
id: L4
name: "Volatilitätsgesteuerter Aktienanteil"
modul: langfrist
rolle: kandidat
evidenz: C
quellen: [MM2017, COWY2020, BD2021]
stichprobenende: 2015-12
freischaltung: lernstufe_2
universum: {typ: liste, elemente: [AKTIEN_WELT]}
daten: [tagesschluss_total_return, zins_eur]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {monate: 120}
signal: vol_managed
parameter: {varianz: monat_t_einfache_tagesrenditen, c: expandierend_echtzeit_ungedeckelt, max_gewicht: 1.0, rest: cash}
varianten: []
kosten_profil: etf
benchmark: [risiko_gate_statische_mischung, L1, buy_and_hold_AKTIEN_WELT]
gates: risiko_gate
abweichungen: [welt_eur_statt_usa, cash_eur, c_echtzeit, deckel_1]
```

---

## 5. Modul Swing

### S1 Trendfolge, Time-Series-Momentum 1/3/12, long/flat (Kern)

**Evidenz B.**
- Moskowitz, Ooi & Pedersen (2012): 58 Futures, Signal = Vorzeichen der 12-Monats-Überschussrendite; Alpha 1,58 % pro Monat (t = 7,99); Out-of-sample 1966–1985 Sharpe 1,1
- Hurst, Ooi & Pedersen (2017): 67 Märkte 1880–2016, Kombination aus 1-, 3- und 12-Monats-Signalen: 11,0 % pro Jahr Überschussrendite nach geschätzten Kosten (vor Gebühren); Sharpe nach Kosten und hypothetischen Gebühren 0,76, **2010–2016 nur 0,41**
- Kritik: Huang et al. (2020) finden bei Einzeltests je Anlage kaum Evidenz; Kim, Tse & Wald (2016) führen das Alpha vor allem auf die Volatilitätsskalierung zurück

**Regel:**
- Universum (7): Gold-ETC, Silber-ETC, breite Rohstoffe, Aktien USA, Aktien Europa, Aktien Schwellenländer, EUR-Staatsanleihen
- Überschussrendite je Anlage und Horizont k ∈ {1, 3, 12} Monate: Total Return minus kumulierter EUR-Zins (G5) über denselben Zeitraum
- s_k = +1, wenn Überschussrendite > 0, sonst −1; s = (s_1 + s_3 + s_12) / 3; long/flat: s⁺ = max(s; 0) ∈ {0; ⅓; 1}
- Gewicht w_i = s⁺_i · (1/σ̂_i) / Σ_j (1/σ̂_j), Summe über **alle** 7 Anlagen, σ̂ nach I7 (EWMA, Schwerpunkt 60 Tage, annualisiert mit 252). Sind alle Anlagen voll long, ist das Portfolio zu 100 % investiert; der Anteil flacher Anlagen liegt in Cash
- Bewertung am letzten Handelstag, Ausführung zur nächsten Eröffnung; Aufwärmphase 600 Handelstage (10 × Schwerpunkt, rekursiver Filter)

**Abweichungen:** Die Quellen handeln Futures long und short mit Hebel über Dutzende Märkte und skalieren das Portfolio auf 10 % Volatilität. Ohne Hebel ist dieses Ziel nicht erreichbar (mit allen 7 Anlagen long läge die Volatilität bei etwa 5–8 %); die App verwendet deshalb inverse Volatilitätsgewichte ohne Portfolio-Ziel. Nur 7 UCITS-Produkte statt breiter Diversifikation. Die erwartete Wirkung ist deutlich kleiner als publiziert.

**Phase-5-Variante:** Futures oder CFDs mit Short-Seite (s statt s⁺) und Portfolio-Volatilitätsziel 10 % unter R4, erst nach Lernstufe 5.

```yaml
id: S1
name: "Trendfolge TSMOM 1/3/12, long/flat"
modul: swing
rolle: kern
evidenz: B
quellen: [MOP2012, HOP2017, HLWZ2020, KTW2016]
stichprobenende: 2009-12
freischaltung: lernstufe_3
universum: {typ: liste, elemente: [GOLD_ETC, SILBER_ETC, ROHSTOFFE_BREIT, AKTIEN_USA, AKTIEN_EUROPA, AKTIEN_EM, ANLEIHEN_STAAT_EUR]}
daten: [tagesschluss_total_return, zins_eur]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {handelstage: 600}
signal: tsmom_kombiniert
parameter:
  lookbacks_monate: [1, 3, 12]
  ueberschuss_gegen: zins_eur
  vol_schaetzer: {typ: ewma, schwerpunkt_tage: 60, annualisierung: 252}
  gewichtung: inverse_vol_ueber_gesamtes_universum
  long_only: true
varianten:
  - {name: nur_12m_signal_mop, lookbacks_monate: [12]}   # Signal nach MOP, Gewichtung wie oben
kosten_profil: etf_etc
benchmark: [immer_long_inverse_vol_gleiches_universum]
gates: standard
abweichungen: [long_flat_statt_long_short, kein_hebel_kein_vol_ziel, sieben_ucits_statt_futures, zins_eur]
phase5_variante: futures_long_short_vol_ziel_10
```

### S2 Aktien-Momentum 12-1, long-only, USA (Kandidat)

**Evidenz C** (die Quelle ist stark, aber die Long-only-Umsetzung auf ein gleichgewichtetes Top-500-Universum weicht deutlich ab).
- Jegadeesh & Titman (1993), NYSE/AMEX 1965–1989: 6/6-Strategie 0,95 % pro Monat (t = 3,07); 12/3 mit einer Woche Abstand 1,49 % (t = 4,28) (einfach geprüft). Fortbestand in den 1990ern (Jegadeesh & Titman, 2001)
- Crash-Risiko: Gewinner minus Verlierer 1927–2013 Schiefe −4,70, April 2009 −45,52 % (Daniel & Moskowitz, 2016; einfach geprüft). Crashs gehen vor allem von der Verlierer-Seite aus, die long-only nicht gehalten wird
- Nach Kosten: 1,33 % brutto, **0,68 % netto pro Monat (t = 2,45)**, kapitalgewichtet über alle Aktien mit NYSE-Grenzen (Novy-Marx & Velikov, 2016). Wirksamste Kostensenkung dort: Kauf erst im obersten Dezil, Verkauf erst nach Austritt aus dem obersten Quintil (10 %/20 %-Regel)

**Regel:**
- Universum: PE2, **zunächst nur USA** (für Europa fehlen kostenlose Aktienzahlen und Kurse delisteter Aktien, eine Rangfolge nach Marktkapitalisierung ist nicht point-in-time möglich)
- Signal: kumulierte Rendite von Monatsende t−12 bis t−1
- Kauf: oberstes Dezil; Halten, bis die Aktie das oberste Quintil verlässt (Novy-Marx & Velikov); gleichgewichtet, jeden Monat auf Gleichgewicht zurückgesetzt
- Bindungen an der Dezil- bzw. Quintilgrenze: höhere Marktkapitalisierung zuerst
- Bewertung am letzten Handelstag, Ausführung zur nächsten Eröffnung; Aktien brauchen 13 Monate Kurshistorie

**Abweichungen:** Long-only statt Gewinner minus Verlierer; gleichgewichtetes Top-500-Universum statt kapitalgewichteter Portfolios über alle Aktien; Survivorship-Behandlung nach PE2. Eine Risikosteuerung nach Barroso & Santa-Clara (2015) wird **nicht** übernommen: Deren Regel skaliert einen Long/Short-Faktor; für ein Long-only-Portfolio gibt es keine Quellenregel, und eine eigene Übertragung verstieße gegen G1. Das bleibt eine offene Research-Frage.

```yaml
id: S2
name: "Aktien-Momentum 12-1 long-only USA"
modul: swing
rolle: kandidat
evidenz: C
quellen: [JT1993, JT2001, DM2016, NMV2016]
stichprobenende: 1989-12
freischaltung: lernstufe_3
universum: {typ: regel, regel: PE2, region: USA}
daten: [tagesschluss_total_return, edgar_aktienzahl]
kalender: NYSE
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {monate: 13}
signal: aktien_momentum_12_1
parameter: {lookback_monate: 12, auslassen_monate: 1, kauf: oberstes_dezil, halten_bis: austritt_oberstes_quintil, gewichtung: gleich}
bindungen: {regel: hoehere_marktkapitalisierung}
varianten:
  - {name: ohne_haltepuffer, halten_bis: austritt_oberstes_dezil}
kosten_profil: aktien_usa
benchmark: [universum_kapitalgewichtet, universum_gleichgewichtet]   # beide müssen bestanden werden
gates: standard
abweichungen: [long_only, gleichgewichtet_top500, keine_risikosteuerung, survivorship_pe2]
phase5_variante: long_short_cfd
```

### S3 52-Wochen-Hoch-Momentum, long-only, USA (Kandidat)

**Evidenz C.** George & Hwang (2004), alle CRSP-Aktien 1963–2001: Maß = Kurs / höchster Kurs der letzten 12 Monate; oberste minus unterste 30 %, (6,6)-Überlappung: 0,45 % pro Monat (t = 2,00), ohne Januar 1,23 % (t = 7,06), im Januar −8,27 %; keine langfristige Umkehr. International in 18 von 20 Märkten profitabel, nach Kosten in den meisten nicht mehr signifikant (Liu, Liu & Ma, 2011).

**Regel:**
- Universum: PE2, zunächst nur USA (wie S2)
- Maß M_i,t = Schlusskurs am Monatsende t / höchster Schlusskurs der 252 Handelstage bis einschließlich Monatsende t (split-bereinigt; die Quelle verwendet Kurse, nicht Total Return)
- Jeden Monat eine Kohorte: oberste 30 % nach M, gleichgewichtet, 6 Monate gehalten; das Portfolio ist der Durchschnitt der 6 laufenden Kohorten
- Bindungen an der 30 %-Grenze: höhere Marktkapitalisierung zuerst; Aktien brauchen 252 Handelstage Historie
- Ausführung zur nächsten Eröffnung

```yaml
id: S3
name: "52-Wochen-Hoch-Momentum long-only USA"
modul: swing
rolle: kandidat
evidenz: C
quellen: [GH2004, LLM2011]
stichprobenende: 2001-12
freischaltung: lernstufe_3
universum: {typ: regel, regel: PE2, region: USA}
daten: [tagesschluss_split_bereinigt, edgar_aktienzahl]
kalender: NYSE
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung
aufwaermphase: {handelstage: 252}
signal: naehe_52w_hoch
parameter: {fenster_handelstage: 252, anteil_oben: 0.30, haltedauer_monate: 6, kohorten: 6}
bindungen: {regel: hoehere_marktkapitalisierung}
varianten: []
kosten_profil: aktien_usa
benchmark: [universum_kapitalgewichtet, universum_gleichgewichtet]
gates: standard
abweichungen: [long_only, top500_statt_alle_aktien, survivorship_pe2]
```

### Nicht aufgenommen im Swing-Modul
- **Rohstoff-Carry** (Koijen et al., 2018; Sharpe 0,62–0,67): braucht historische Kurse einzelner Futures-Kontrakte, dafür gibt es keine vollständige kostenlose Quelle
- **Gold-Timing über Realzinsen oder Inflation:** Erb & Harvey (2013) zeigen, dass Gold über praktikable Horizonte ein unzuverlässiger Inflationsschutz ist; die Korrelation mit realen US-Renditen (−0,82, 1997–2012) belegt keinen kausalen Zusammenhang. Gold steckt in S1 und L3; Realzinsen erscheinen nur als Kontext in der Markt-Intelligenz

---

## 6. Modul Intraday

**Vorab im Lernmodul:**
- Von 1.551 Brasilianern, die mehr als 300 Tage Index-Futures daytradeten, verloren 97 % nach Gebühren; 1,1 % verdienten mehr als den Mindestlohn (Chague et al., 2020; einfach geprüft). In Taiwan konnten weniger als 1 % der Daytrader verlässlich nach Gebühren Gewinne erzielen (Barber et al., 2014)
- Wer abends flach ist, verzichtet auf den Übernacht-Anteil der Aktienprämie: US-Markt 1993–2013 im Schnitt 0,55 % pro Monat über Nacht und 0,38 % tagsüber; bei den größten Aktien fiel praktisch die gesamte Prämie über Nacht an (Lou, Polk & Skouras, 2019)

### I1 Intraday-Momentum in der letzten halben Stunde (Kandidat)

**Evidenz C.**
- Gao, Han, Li & Zhou (2018), SPY 1993–2013: Die Rendite vom Vortagesschluss bis 10:00 ET sagt die letzte halbe Stunde voraus (R² 1,6 %); Regel mit Long bei positiver, Short bei negativer Morgenrendite: 6,67 % pro Jahr, Sharpe 1,08, Trefferquote 54,4 %; nach Spread ab Juli 2001 4,46 % pro Jahr
- Baltussen et al. (2021), 17 Aktienindex-Futures als gleichgewichtetes Long/Short-Portfolio 1974–2020: stärkeres Signal ist die Rendite vom Vortagesschluss bis 30 Minuten vor Schluss; 6,86 % pro Jahr, Sharpe 1,73, brutto. **Ein einzelner Markt long/flat wird deutlich weniger leisten**
- Rosa (2022): Die Vorhersagbarkeit verschwindet im Out-of-sample-Zeitraum und hängt vom Marktregime ab. International gemischt: vorhanden in China und Japan, schwach in Korea, fehlt in Hongkong und Singapur (Limkriangkrai, Chai & Zheng, 2023)

**Regel (Baltussen-Variante):**
- Daten: eigene Aufzeichnung in **1-Minuten-Bars** ab Phase 1
- Test-Markt 1: DAX-UCITS-ETF auf Xetra. Signal r_ROD = Rendite vom Vortagesschluss bis 17:00 MEZ. Bei r_ROD > 0 Kauf in der ersten 1-Minuten-Bar nach 17:00 (E1), Verkauf per Schlusskurs-Order in der Schlussauktion (E12b); sonst flach
- Test-Markt 2: S&P-500-UCITS-ETF an einem Handelsplatz mit Abendhandel. Signal- und Ausstiegszeit richten sich nach der **NYSE-Uhrzeit** (Signal 15:30 ET, Ausstieg zum Kurs um 16:00 ET), nicht nach dem Handelsschluss des deutschen Handelsplatzes; in den Wochen mit unterschiedlicher Sommerzeit verschiebt sich das in MEZ. Liquidität und Spreads zu dieser Zeit UNVERIFIZIERT; vor dem Test prüfen
- Kosten: Spread und Kommission bei Einstieg, Kommission und Slippage bei Ausstieg

**Realistische Erwartung:** Bei einer Sharpe Ratio von 1,08 wie bei Gao et al. verlangt MinTRL (95 %) etwa 2,3 Jahre Daten, bei 0,5 etwa 11 Jahre. **I1 kann frühestens nach etwa 3 Jahren eigener Aufzeichnung die Gates bestehen**, wahrscheinlich später oder nie. Bis dahin läuft I1 nur als Beobachtung im Bereich Evidenz.

```yaml
id: I1
name: "Intraday-Momentum letzte halbe Stunde"
modul: intraday
rolle: kandidat
evidenz: C
quellen: [GHLZ2018, BDLM2021, ROSA2022, LCZ2023]
stichprobenende: 2020-05
freischaltung: lernstufe_3
universum: {typ: liste, elemente: [DAX_ETF_XETRA, SP500_ETF_ABENDHANDEL]}
daten: [eigene_aufzeichnung_1min]
kalender: {DAX_ETF_XETRA: XETRA, SP500_ETF_ABENDHANDEL: NYSE_ZEIT}
bewertung: {frequenz: taeglich, zeitpunkt: schluss_minus_30min_heimatmarkt}
ausfuehrung: erste_bar_nach_signal
ausstieg: schlusskurs_order_E12b
aufwaermphase: {handelstage: 1}
signal: intraday_momentum_rod
parameter: {signal_fenster: vortagesschluss_bis_schluss_minus_30min, long_only: true}
varianten:
  - {name: gao_morgenrendite, signal_fenster: vortagesschluss_bis_eroeffnung_plus_30min}
kosten_profil: etf_intraday
benchmark: [immer_long_letzte_halbe_stunde]
gates: standard
abweichungen: [einzelmarkt_statt_portfolio, long_flat, ucits_statt_futures, einstieg_eine_minute_nach_signal]
phase5_variante: futures_long_short
voraussetzung: mindestens_minTRL_eigene_daten
```

---

## 7. Modul Optionen (Phase 7, gesperrt bis Lernstufe 6)

Jeder Kontrakt wird zusätzlich nach O10 der Spezifikation bewertet (handelbarer Edge, Maximalverlust ≤ 2 % des Kapitals nach R4, Stresstests). Die Regeln hier legen fest, welche Strukturen überhaupt geprüft werden. Alle Strategien haben einen **endlichen, vorab bekannten Maximalverlust**.

| ID | Strategie | Evidenz | Regel (Kurzfassung) |
|---|---|---|---|
| O1 | Put-Credit-Spread auf einen Index | C | Monatlich Put nahe am Geld verkaufen und einen tieferen Put kaufen (europäischer Index, Eurex); Abstand der Strikes so, dass der Maximalverlust ≤ 2 % des Kapitals ist. Grundlage ist die Volatilitätsprämie bei Indexoptionen (Carr & Wu, 2009; Bakshi & Kapadia, 2003; in dieser Phase nicht erneut geprüft). Ein ungesicherter, "cash-gedeckter" Put ist ausgeschlossen: Ein DAX-Kontrakt entspricht bei einem Punktwert von 5 € rund 120.000 € Nominalwert, das verletzt R4 |
| O2 | Covered Call auf einen gehaltenen Index-ETF | C | Monatlich Call leicht aus dem Geld (Delta ≈ 0,30) auf den gehaltenen Bestand; Ertrag überwiegend Aktienbeta, Aufwärtspotenzial gedeckelt (Israelov & Nielsen, 2015) |
| O3 | Bull-Call-Spread als Umsetzung eines Long-Signals | C | Nur bei einem aktiven Long-Signal aus S1 oder L2, Laufzeit 30–60 Tage, Maximalverlust ≤ 2 %. Bear-Put-Spreads nur mit Short-Signalen der Phase-5-Varianten |
| O4 | Schutzput als Versicherung | C (als Rendite negativ) | Nur auf Wunsch, als bepreiste Absicherung eines Bestands; die App zeigt die erwarteten Kosten pro Jahr (Israelov, 2019) |

**Im Simulator** wird für jede Short-Option die volle Verpflichtung (Strike × Kontraktgröße abzüglich der gekauften Absicherung) als gebundenes Kapital geführt, nicht nur die Margin.

Die genaue Formalisierung (Strike-Wahl, Rollregeln, YAML) erfolgt vor Phase 7.

---

## 8. Kontrollgruppe

Getestet auf den Instrumenten und Zeiträumen der jeweiligen Quelle (G3), mit denselben Kosten und Gates; eigenes N (G9). Erwartung aus der Literatur: Keine Regel besteht.

**Befund:** Die Regeln von Brock, Lakonishok & LeBaron (1992) waren im Dow Jones 1897–1986 vor Kosten hoch signifikant. Sullivan, Timmermann & White (1999) prüften 7.846 Regeln mit Korrektur für Data Snooping: Out-of-sample 1987–1996 war die beste Brock-Regel nicht mehr signifikant (White-p = 0,154), die beste Regel des ganzen Universums ebenfalls nicht (p = 0,341) (einfach geprüft). Bajgrowicz & Scaillet (2012): Selbst in der Stichprobe wird die Leistung durch geringe Transaktionskosten vollständig aufgezehrt.

| ID | Regel | Exakte Parameter | Quelle und Befund | Evidenz |
|---|---|---|---|---|
| K1 | Gleitende Durchschnitte (VMA) | Kurs bzw. kurzer gegen langen Durchschnitt: (1,50), (1,150), (5,150), (1,200), (2,200), Band 0 % und 1 %; long, solange kurz > lang × (1 + Band); sonst Cash. Long/flat-Anpassung der Kauf-minus-Verkauf-Messung der Quelle (erklärt) | Brock et al. (1992); Sullivan et al. (1999) | D |
| K2 | Golden Cross | Long ab Kreuzen SMA(50) über SMA(200), Cash ab Kreuzen nach unten | Teil des Sullivan-Gitters; auf ETFs schwächer als Buy-and-hold (Huang & Huang, 2020) | D |
| K3 | Ausbruch aus der Handelsspanne | Kauf, wenn der Schlusskurs das Hoch der letzten 50, 150 bzw. 200 Tage um das Band (0 %/1 %) übersteigt; 10 Tage halten | Brock et al. (1992) | D |
| K4 | RSI(14) 30/70 | Kauf, wenn der RSI unter 30 fällt und wieder über 30 steigt; Verkauf, wenn er über 70 steigt und wieder unter 70 fällt; höchstens 10 Tage halten (wie in der Quelle, nach Brock et al.). Long/flat-Anpassung der Kauf-minus-Verkauf-Messung (erklärt) | Chong, Ng & Liew (2014): Kauf-minus-Verkauf-Differenz im DAX −0,914 %, in mehreren der 5 Märkte negativ | D |
| K5 | Bollinger-Bänder | Kauf bei Schlusskurs unter dem unteren Band (20; 2), Verkauf bei Schlusskurs über dem Mittelband | Lento et al. (2007): nach Kosten durchgehend schlechter als Buy-and-hold; Parameter der Studie UNVERIFIZIERT, Regel hier ENTSCHEIDUNG | D |
| K6 | Kerzenmuster | Muster und Trenddefinition (10-Tage-EMA) nach Marshall, Young & Rose (2006); Einstieg zur nächsten Eröffnung, 10 Tage halten; Anzahl und Definition der Muster vor Implementierung aus dem Anhang übernehmen | "Kein Wert" für Anleger | D |
| K7 | Kurzfristige Umkehr (Kostenbeispiel) | Wöchentlich: unterstes Dezil der Vorwochenrendite im Universum PE2 (USA) kaufen, eine Woche halten; Variante mit Haltepuffer (halten bis Austritt aus der unteren Hälfte, nach de Groot et al.) | Novy-Marx & Velikov (2016): netto −1,28 % pro Monat; de Groot et al. (2012): positiv nur mit institutionellen Kosten | D |
| K8 | Post-Earnings-Drift (Zerfallsbeispiel) | SUE = (EPS_q − EPS_{q−4}) / Standardabweichung dieser Differenz über die 8 Vorquartale; EPS verwässert aus EDGAR; **Ereigniszeit = Annahmezeitpunkt der 10-Q- bzw. 10-K-Meldung** (die Zahlen aus der früheren 8-K-Pressemitteilung sind nicht maschinenlesbar in EDGAR); **nur Q1–Q3** (Q4-EPS ist aus Jahres- minus 9-Monats-Wert nicht sauber ableitbar); Kauf, wenn SUE über dem 90. Perzentil der SUE-Verteilung **des Vorquartals** liegt; 60 Handelstage halten | Bernard & Thomas (1989); Martineau (2022): bei großen Aktien seit 2006 verschwunden; Novy-Marx & Velikov: netto 0,26 % (t = 1,60). Die späte Ereigniszeit schwächt die Regel gegenüber der Quelle zusätzlich (erklärt) | D |
| K9 | Opening Range Breakout | Nach Zarattini & Aziz (2023) auf QQQ (Quelleninstrument): Richtung der ersten 5-Minuten-Bar ab 09:30 ET, Einstieg zur Eröffnung der zweiten Bar, keine Position bei Doji, Stop am Extrem der ersten Bar, Ziel 10R, sonst Ausstieg zum Schluss; 1 % Risiko je Trade; **ohne Hebel** (Quelle bis 4-fach) | Nicht begutachtet; Autoren mit kommerziellem Interesse; Basisversion über alle Aktien Sharpe 0,48 (Zarattini, Barbon & Aziz, 2024) | D |
| K10 | "Noise Area" | Nach Zarattini, Aziz & Barbon (2024) auf SPY: σ je Uhrzeit = Mittel der letzten 14 Tage von \|Kurs(Uhrzeit) / Eröffnung − 1\|; oberes Band = max(Eröffnung, Vortagesschluss) × (1 + σ), unteres Band = min(Eröffnung, Vortagesschluss) × (1 − σ); Entscheidungen nur zur vollen und halben Stunde; long über dem oberen, short über dem unteren Band (in der App long/flat); Stop = max(oberes Band, VWAP); Schluss um 16:00; **Basisgröße 100 % des Kapitals ohne dynamischen Hebel** | Nicht begutachtet; Autoren mit kommerziellem Interesse | D |
| K11 | Fibonacci und Elliott-Wellen | Nicht als eindeutige Regel definierbar; **nicht getestet**, nur im Lernmodul erklärt | Keine begutachtete Evidenz für Profitabilität gefunden | D |

**Bewusst nicht aufgenommen:** Kopf-Schulter- und andere Chartformationen. Die Erkennung braucht aufwendige Glättungsverfahren (Lo, Mamaysky & Wang, 2000, testen zudem keine Profitabilität); bei Aktien fand sich kein eigenständiger Gewinn (Savin, Weller & Zvingelis, 2007).

---

## 9. Reproduktionsziele und Look-ahead-Fallen je Strategie

Exakte Reproduktion ist mit kostenlosen Daten nicht möglich (andere Instrumente, Zeiträume, Währungen). Ziel ist, **Richtung und Größenordnung** der Quelle im überlappenden Zeitraum zu treffen. Weicht das Ergebnis stark ab, wird zuerst die Engine geprüft.

| ID | Reproduktionsziel (qualitativ) | Look-ahead-Fallen |
|---|---|---|
| L1 | Keine (Benchmark); Rebalancing-Umschlag und Kosten plausibel | Rebalancing mit Kursen des Bewertungstags, Ausführung erst am Folgetag |
| L2 | Deutlich geringere Volatilität und maximaler Drawdown als Buy-and-hold derselben Klassen bei ähnlicher oder etwas geringerer Rendite | Monatsschlusskurse müssen feststehen; Total-Return-Anpassung nur mit bis dahin bekannten Ausschüttungen (K4) |
| L3 | Positiver, aber gegenüber der Quelle deutlich kleinerer Vorteil; Ergebnis abhängig vom Anteil der Aktienklassen | Klassen ohne 13 Monate Historie dürfen nicht über rückwirkend verlängerte Proxies in die Rangfolge kommen, wenn der Proxy zum Zeitpunkt nicht bekannt war |
| L4 | Geringerer Drawdown als der ungesteuerte Markt; Sharpe-Vorteil kleiner als in der Quelle (Echtzeit-c) | c_t nur bis Monatsende t; Varianz des Monats t bestimmt das Gewicht ab Eröffnung t+1 |
| S1 | Positive, aber kleine aktive Rendite gegenüber "immer long"; Hauptnutzen in Bärenmärkten (2008, 2022) | σ̂ nur aus Tagesdaten bis t; Zinssatz mit Veröffentlichungsverzug (G5) |
| S2 | Top-Dezil schlägt gleichgewichtetes Universum brutto; nach Kosten fraglich; Einbrüche in Momentum-Crashs (2009) | Universum und Marktkapitalisierung point-in-time (PE2); delistete Aktien mit Delisting-Rendite |
| S3 | Kleiner positiver Effekt, Januar schwach | Höchstkurs einschließlich des Bewertungstags ist zulässig (Schlusskurs steht fest); Split-Bereinigung nur mit bekannten Splits |
| I1 | Trefferquote knapp über 50 %, aktive Rendite nach Kosten nahe null | Einstieg frühestens eine Minute nach dem Signal; Schlusskurs-Order vor Annahmeschluss |
| K1–K10 | Keine signifikante aktive Rendite nach Kosten im Zeitraum nach 1987 bzw. nach der Quellenstichprobe | K8: Ereigniszeit = 10-Q/10-K-Annahme, Perzentilgrenzen aus dem Vorquartal |

---

## 10. Reihenfolge der Umsetzung

| Phase | Strategien |
|---|---|
| 2 (Engine-Validierung) | L1, L2 als erste Tests; K1, K2 als Negativkontrolle |
| 3 (Langfrist) | L1–L4 |
| 3b (Simulator) | L1 und L2 als Signalvorschläge im Übungsdepot |
| 5 (Swing) | S1, dann S2, S3; K3–K8 |
| 5b (Intraday) | I1, K9, K10, mit eigener Aufzeichnung ab Phase 1 |
| 7 (Optionen) | O1–O4 |

---

## 11. Offene Punkte

| Punkt | Wann klären |
|---|---|
| Konkrete UCITS-Produkte je Anlageklasse (Kosten, Replikation, Handelsplatz) und Datenproxies | Phase 1 |
| Quellensteuersatz irischer UCITS-Fonds auf US-Dividenden (G4) | Phase 1 |
| Verfügbarkeit des Frankfurter Tagesgeldsatzes vor 1999 als kostenlose Zeitreihe (G5) | Phase 1 |
| Liquidität eines S&P-500-UCITS-ETF im Abendhandel (I1, Test-Markt 2) | Vor Phase 5b |
| Kerzenmuster-Definitionen (K6) | Vor Phase 5 |
| Risikosteuerung für Long-only-Momentum (S2) | Offene Research-Frage |
| Formalisierung O1–O4 | Vor Phase 7 |

---

## Änderungsprotokoll

**v1.1 (20260925)** nach unabhängiger Prüfung (4 kritische, 9 schwere, viele leichte Befunde), alle eingearbeitet:
- Kritisch: Cash-gedeckter Index-Put (O1) verletzte die 2 %-Verlustgrenze → ersetzt durch Put-Credit-Spread; im Simulator wird die volle Verpflichtung als Kapital gebunden
- Kritisch: Post-Earnings-Drift (K8) hatte doppelten Look-ahead → Ereigniszeit der 10-Q/10-K-Meldung, Perzentilgrenzen aus dem Vorquartal, nur Q1–Q3
- Kritisch: Das PBO-Gate hätte die Kernstrategien systematisch blockiert → PBO nur noch, wenn die App eine Variante auswählt
- Kritisch: Das Drawdown-Gate hätte bloßes Weniger-Risiko als Strategie durchgelassen → Vergleich mit statischer Mischung gleicher Investitionsquote über die Calmar-Ratio
- Schwer: Gates auf aktiver Rendite statt absolutem Sharpe; Prüfung nur nach der Quellenstichprobe; Abschlag 60 % auf die aktive Rendite; ein gemeinsames N über alle signalfähigen Familien und t ≥ 3; L3 als eigene, abgewandelte Strategie erklärt (Grad C); S1 ohne unerreichbares Volatilitätsziel; S2 auf Grad C, ohne eigene Risikosteuerung, zunächst nur USA; I1 mit 1-Minuten-Daten, Schlusskurs-Order und ehrlicher Zeitschätzung; Proxy-Regeln für Währung, Quellensteuer und Kalender; K9/K10 auf den Quelleninstrumenten mit vollständigen Regeln
- Leicht: Zitat Rosa (2022) korrigiert und internationale Befunde der richtigen Quelle zugeordnet; Chong et al. richtig beschrieben; Varianten ohne Quellenbasis entfernt (G1); YAML vereinheitlicht; Startzustände, Aufwärmphasen, Bindungsregeln und Zinsreihen vor 2019 festgelegt; Reproduktionsziele und Look-ahead-Fallen für alle Strategien ergänzt

---

## Quellen

- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). Value and momentum everywhere. *Journal of Finance, 68*(3), 929–985.
- Bajgrowicz, P., & Scaillet, O. (2012). Technical trading revisited: False discoveries, persistence tests, and transaction costs. *Journal of Financial Economics, 106*(3), 473–491.
- Baltussen, G., Da, Z., Lammers, S., & Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics, 142*(1), 377–403.
- Barber, B. M., Lee, Y.-T., Liu, Y.-J., & Odean, T. (2009). Just how much do individual investors lose by trading? *Review of Financial Studies, 22*(2), 609–632.
- Barber, B. M., Lee, Y.-T., Liu, Y.-J., & Odean, T. (2014). The cross-section of speculator skill: Evidence from day trading. *Journal of Financial Markets, 18*, 1–24.
- Barber, B. M., & Odean, T. (2000). Trading is hazardous to your wealth. *Journal of Finance, 55*(2), 773–806.
- Barroso, P., & Detzel, A. (2021). Do limits to arbitrage explain the benefits of volatility-managed portfolios? *Journal of Financial Economics, 140*(3), 744–767.
- Barroso, P., & Santa-Clara, P. (2015). Momentum has its moments. *Journal of Financial Economics, 116*(1), 111–120.
- Bernard, V. L., & Thomas, J. K. (1989). Post-earnings-announcement drift: Delayed price response or risk premium? *Journal of Accounting Research, 27*(Suppl.), 1–36. (Nicht eingesehen.)
- Brock, W., Lakonishok, J., & LeBaron, B. (1992). Simple technical trading rules and the stochastic properties of stock returns. *Journal of Finance, 47*(5), 1731–1764.
- Cederburg, S., O'Doherty, M. S., Wang, F., & Yan, X. (2020). On the performance of volatility-managed portfolios. *Journal of Financial Economics, 138*(1), 95–117.
- Chague, F., De-Losso, R., & Giovannetti, B. (2020). *Day trading for a living?* [Working paper]. SSRN 3423101.
- Chong, T. T.-L., Ng, W.-K., & Liew, V. K.-S. (2014). Revisiting the performance of MACD and RSI oscillators. *Journal of Risk and Financial Management, 7*(1), 1–12.
- Clare, A., Seaton, J., Smith, P. N., & Thomas, S. (2016). The trend is our friend: Risk parity, momentum and trend following in global asset allocation. *Journal of Behavioral and Experimental Finance, 9*, 63–80.
- Daniel, K., & Moskowitz, T. J. (2016). Momentum crashes. *Journal of Financial Economics, 122*(2), 221–247.
- de Groot, W., Huij, J., & Zhou, W. (2012). Another look at trading costs and short-term reversal profits. *Journal of Banking & Finance, 36*(2), 371–382.
- Erb, C. B., & Harvey, C. R. (2013). The golden dilemma. *Financial Analysts Journal, 69*(4), 10–42.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79. (Gelesen: Update 2013.)
- Gao, L., Han, Y., Li, S. Z., & Zhou, G. (2018). Market intraday momentum. *Journal of Financial Economics, 129*(2), 394–414.
- George, T. J., & Hwang, C.-Y. (2004). The 52-week high and momentum investing. *Journal of Finance, 59*(5), 2145–2176.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). … and the cross-section of expected returns. *Review of Financial Studies, 29*(1), 5–68. (Nicht eingesehen.)
- Huang, D., Li, J., Wang, L., & Zhou, G. (2020). Time series momentum: Is it there? *Journal of Financial Economics, 135*(3), 774–794.
- Huang, J.-Z., & Huang, Z. (2020). Testing moving average trading strategies on ETFs. *Journal of Empirical Finance, 57*, 16–32.
- Hurst, B., Ooi, Y. H., & Pedersen, L. H. (2017). A century of evidence on trend-following investing. *Journal of Portfolio Management, 44*(1), 15–29.
- Israelov, R. (2019). Pathetic protection: The elusive benefits of protective puts. *Journal of Alternative Investments, 21*(3), 6–. (Endseite nicht geprüft.)
- Israelov, R., & Nielsen, L. N. (2015). Covered calls uncovered. *Financial Analysts Journal, 71*(6), 44–57.
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers: Implications for stock market efficiency. *Journal of Finance, 48*(1), 65–91.
- Jegadeesh, N., & Titman, S. (2001). Profitability of momentum strategies: An evaluation of alternative explanations. *Journal of Finance, 56*(2), 699–720.
- Kim, A. Y., Tse, Y., & Wald, J. K. (2016). Time series momentum and volatility scaling. *Journal of Financial Markets, 30*, 103–124.
- Koijen, R. S. J., Moskowitz, T. J., Pedersen, L. H., & Vrugt, E. B. (2018). Carry. *Journal of Financial Economics, 127*(2), 197–225.
- Lento, C., Gradojevic, N., & Wright, C. S. (2007). Investment information content in Bollinger Bands? *Applied Financial Economics Letters, 3*(4), 263–267.
- Limkriangkrai, M., Chai, D., & Zheng, G. (2023). *Pacific-Basin Finance Journal, 80*, 102086. (Titel nicht geprüft.)
- Liu, M., Liu, Q., & Ma, T. (2011). The 52-week high momentum strategy in international stock markets. *Journal of International Money and Finance, 30*(1), 180–204.
- Lo, A. W., Mamaysky, H., & Wang, J. (2000). Foundations of technical analysis. *Journal of Finance, 55*(4), 1705–1765.
- Lou, D., Polk, C., & Skouras, S. (2019). A tug of war: Overnight versus intraday expected returns. *Journal of Financial Economics, 134*(1), 192–213.
- Marshall, B. R., Young, M. R., & Rose, L. C. (2006). Candlestick technical trading strategies: Can they create value for investors? *Journal of Banking & Finance, 30*(8), 2303–2323.
- Martineau, C. (2022). Rest in peace post-earnings announcement drift. *Critical Finance Review, 11*(3–4), 613–646.
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Moreira, A., & Muir, T. (2017). Volatility-managed portfolios. *Journal of Finance, 72*(4), 1611–1644.
- Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics, 104*(2), 228–250.
- Novy-Marx, R., & Velikov, M. (2016). A taxonomy of anomalies and their trading costs. *Review of Financial Studies, 29*(1), 104–147.
- Rosa, C. (2022). Understanding intraday momentum strategies. *Journal of Futures Markets, 42*(12), 2218–2234.
- Savin, G., Weller, P., & Zvingelis, J. (2007). The predictive power of "head-and-shoulders" price patterns in the U.S. stock market. *Journal of Financial Econometrics, 5*(2), 243–265.
- Sullivan, R., Timmermann, A., & White, H. (1999). Data-snooping, technical trading rule performance, and the bootstrap. *Journal of Finance, 54*(5), 1647–1691.
- Zakamulin, V. (2014). The real-life performance of market timing with moving average and time-series momentum rules. *Journal of Asset Management, 15*(4), 261–278.
- Zarattini, C., & Aziz, A. (2023). *Can day trading really be profitable?* [Working paper]. SSRN 4416622.
- Zarattini, C., Aziz, A., & Barbon, A. (2024). *Beat the market: An effective intraday momentum strategy for S&P500 ETF (SPY)* [Working paper]. SSRN 4824172.
- Zarattini, C., Barbon, A., & Aziz, A. (2024). *A profitable day trading strategy for the U.S. equity market* [Working paper]. SSRN 4729284.
- Nicht erneut geprüft, nur für O1 genannt: Bakshi, G., & Kapadia, N. (2003). *Review of Financial Studies, 16*(2); Carr, P., & Wu, L. (2009). *Review of Financial Studies, 22*(3).
