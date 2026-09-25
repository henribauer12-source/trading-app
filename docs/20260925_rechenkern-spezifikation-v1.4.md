---
title: Trading-Analyse-App – Rechenkern-Spezifikation
date: 20260925
status: v1.4 (Phase 0b); alle Abschnitte unabhängig geprüft; E12b (Schlusskurs-Order) aus der Katalog-Prüfung ergänzt
owner: Henri
basis: 20260925_trading-app-plan-v6.md, 20260924_trading-app-qualitaetsstandards.md
---

# Rechenkern-Spezifikation v1

## 0. Zweck und Lesart

Diese Spezifikation legt jede Berechnung der App fest, **bevor** Code entsteht: Formel, Konvention, Randfälle, Quelle und Testwert. Code, der von ihr abweicht, ist ein Fehler, auch wenn er "plausibel" rechnet. Änderungen an der Spezifikation werden versioniert und begründet.

**Status jedes Eintrags:**

| Status | Bedeutung |
|---|---|
| VERIFIZIERT | Formel und Testwert in der Primärquelle gelesen und unabhängig zweimal nachgerechnet |
| REPRODUZIERT | Testwert aus verlässlicher Sekundärquelle (z. B. QuantLib-Testsuite, die das Original zitiert), zweimal exakt nachgerechnet |
| ENTSCHEIDUNG | Keine Literaturvorgabe; bewusste Festlegung für diese App, begründet |
| UNVERIFIZIERT | Primärquelle nicht eingesehen; vor Implementierung prüfen |

**Nachrechnung:** Alle numerischen Testwerte in Abschnitt 10 wurden am 20260925 dreimal unabhängig berechnet: durch die Recherche-Agenten (scipy), durch ein separat geschriebenes Skript nur aus den Formeln dieser Spezifikation und durch einen Prüf-Agenten, der die Spezifikation nicht geschrieben hat. Alle stimmen auf die angegebenen Stellen überein. Die Befunde der Prüfung (0 kritisch, 9 schwer, 17 leicht) sind in v1.1 eingearbeitet; siehe Änderungsprotokoll am Ende.

**Toleranzen (gelten für alle Tests):**

| Testart | Toleranz |
|---|---|
| Gegen publizierten Wert mit d Nachkommastellen | \|x − Wert\| ≤ 0,5 · 10⁻ᵈ |
| Regressionswert, hier mit 6 Nachkommastellen angegeben | absolut ≤ 5 · 10⁻⁷; die Testdatei speichert die volle Präzision (≥ 12 signifikante Stellen) aus der Nachrechnung und prüft dann relativ ≤ 10⁻⁹ |
| Zwei Implementierungen derselben Formel (geschlossene Form) | relativ ≤ 10⁻⁹ |
| Numerische Verfahren gegeneinander (Baum vs. Näherung) | methodenspezifisch, beim Test angegeben |
| Invarianten (Parität, Symmetrie) | absolut ≤ 10⁻¹⁰ · Preisniveau |

---

## 1. Konventionen

| Nr. | Festlegung | Status |
|---|---|---|
| K1 | **Zeit:** intern UTC mit Zeitzonen-Info; Anzeige in Europe/Berlin. Handelstage und -zeiten aus Börsenkalendern je Handelsplatz (Xetra, NYSE, CME, Eurex usw.) | ENTSCHEIDUNG |
| K2 | **Point-in-time:** Jede Berechnung zum Zeitpunkt t nutzt ausschließlich Daten mit `available_at ≤ t`. Rollierende Fenster enden bei der letzten abgeschlossenen Bar. Eine Bar ist erst ab ihrem Endzeitpunkt verfügbar | ENTSCHEIDUNG (Qualitätsstandards Abschnitt 3) |
| K3 | **Renditen:** gespeichert als einfache Renditen R_t = P_t / P_{t−1} − 1 auf Total-Return-Basis (Dividenden reinvestiert). Log-Renditen r_t = ln(1 + R_t) nur dort, wo ein Modell sie verlangt (Volatilitätsschätzung, HAR, GARCH). Portfolio-Aggregation immer mit einfachen Renditen | ENTSCHEIDUNG |
| K4 | **Kurse:** Rohpreise plus separate Corporate-Actions-Tabelle (Splits, Dividenden, Bezugsrechte) mit Ankündigungs- und Ex-Datum. Adjustierte Reihen werden zum Zeitpunkt t nur mit bis t bekannten Ereignissen gebildet | ENTSCHEIDUNG |
| K5 | **Annualisierung:** 252 Handelstage für Tagesdaten, 12 für Monatsdaten, 52 für Wochendaten. Ausnahme: Die papiergetreue **Replikation** von TSMOM nutzt 261 (siehe I7); im Produktivbetrieb gilt auch dort 252 | ENTSCHEIDUNG |
| K6 | **Risikofreier Zins:** €STR für EUR-Positionen, SOFR für USD. Beide sind ACT/360-Geldmarktsätze. Umrechnung in stetigen Zins über die Laufzeit: R_c = ln(1 + R · D/360) / τ, mit D = Kalendertage und τ = Laufzeit in Jahren nach ACT/365 | VERIFIZIERT (Hull, Kap. 4) |
| K7 | **Überschussrendite pro Periode:** R_t − r_f,t, mit r_f,t = periodengerechter Anteil des risikofreien Zinses | ENTSCHEIDUNG |
| K8 | **Währung:** Basiswährung EUR. Umrechnung jeder Position mit dem Wechselkurs, der zum Bewertungszeitpunkt verfügbar war (kein Tagesschlusskurs für Intraday-Bewertungen) | ENTSCHEIDUNG |
| K9 | **Laufzeit von Optionen:** Kalenderzeit ACT/365 bis zum exakten Verfalls-/Settlement-Zeitpunkt in Sekunden: τ = Sekunden bis Settlement / (365 · 86.400). AM- und PM-Settlement werden unterschieden | ENTSCHEIDUNG (Hull diskutiert Handelstage; wir wählen Kalenderzeit für Konsistenz mit Marktkonvention bei IV) |
| K10 | **Volatilitätsvergleich:** Implizite und prognostizierte Volatilität werden nie als annualisierte Zahlen direkt verglichen, sondern als **Gesamtvarianz über die Restlaufzeit**: w = σ² · τ (implizit, Kalenderzeit) gegen Σ prognostizierte Tagesvarianzen über die verbleibenden Handelstage. So kann die Konventionswahl in K5/K9 keinen Scheinvorteil erzeugen | ENTSCHEIDUNG |
| K11 | **Numerik:** float64. Normalverteilung über erfc-basierte Implementierung (scipy). Bivariate Normalverteilung mit Genauigkeit ≤ 10⁻⁸ (Genz). Geldbeträge werden erst bei der Anzeige gerundet | ENTSCHEIDUNG |
| K12 | **Fehlerverhalten:** Iterative Verfahren prüfen Konvergenz; bei Nichtkonvergenz, Werten außerhalb der Arbitragegrenzen oder fehlenden Daten wird ein expliziter Fehlerzustand zurückgegeben (kein stiller Ersatzwert, kein Vorwärtsfüllen über mehr als eine Bar ohne Kennzeichnung) | ENTSCHEIDUNG |

---

## 2. Rendite- und Performancekennzahlen

**P1 Kumulierte Rendite:** W_t = Π(1 + R_s) − 1. Status: Standarddefinition.

**P2 CAGR:** (W_T + 1)^(1/Jahre) − 1, Jahre = Kalendertage / 365,25. ENTSCHEIDUNG.

**P3 Volatilität:** Stichproben-Standardabweichung (ddof = 1) der Periodenrenditen · √(Perioden pro Jahr). ENTSCHEIDUNG.

**P4 Sharpe Ratio:** SR = Mittelwert(R − r_f) / Stichproben-Std(R − r_f). Berechnet **pro Periode**; annualisiert nur für die Anzeige mit √(Perioden pro Jahr). PSR, DSR und MinTRL (S2–S4) erhalten immer die nicht annualisierte SR. Status: VERIFIZIERT (Konvention nach Bailey & López de Prado, 2012, Fn. 5).

**P5 Sortino Ratio:** S = (R̄ − T) / TDD mit TDD = √[(1/N) · Σ min(R_i − T, 0)²]. Division durch **alle** N Beobachtungen, nicht nur die negativen. Zielrendite T = risikofreier Zins pro Periode. Status: VERIFIZIERT (Rollinger & Hoffman; Sortino & van der Meer 1991 nicht eingesehen). Testwert T5.

**P6 Maximaler Drawdown:** MDD = max_t (1 − V_t / max_{s≤t} V_s) auf dem Vermögensverlauf V. Immer auf Tagesdaten berechnet; bei Vergleich mit Monatsstudien zusätzlich auf Monatsdaten ausgewiesen, weil die Werte sich unterscheiden. Status: Standarddefinition (UNVERIFIZIERT gegen Primärquelle, unkritisch).

**P7 Calmar Ratio:** CAGR / MDD. ENTSCHEIDUNG.

**P8 Trefferquote und Erwartungswert je Trade:**
- Trefferquote h = Anzahl Trades mit Netto-P&L > 0 / Anzahl Trades
- Erwartungswert E = h · Ø-Gewinn − (1 − h) · Ø-Verlust, **nach Kosten**
- Profit-Faktor = Σ Gewinne / |Σ Verluste|
- Status: ENTSCHEIDUNG

**P9 Umschlag (Turnover):** Σ |Δ Gewicht| / 2 pro Periode, annualisiert. ENTSCHEIDUNG.

**P10 Benchmark:** Jede Kennzahl wird neben der eines günstigen, breit gestreuten UCITS-Welt-ETF ausgewiesen, gleiche Periode, gleiche Kostenannahmen. ENTSCHEIDUNG.

---

## 3. Statistik und Validierung

**S1 Wilson-Konfidenzintervall** für Trefferquoten (x Treffer in n Versuchen, p = x/n, q = 1 − p, z = 1,959964 für 95 %):

  Grenzen = [2np + z² ∓ z · √(z² + 4npq)] / [2(n + z²)]

Status: VERIFIZIERT (Wilson, 1927, über Newcombe, 1998, Methode 3). Testwerte T6.

**Anzeige-Regel (ENTSCHEIDUNG):** Eine Trefferquote wird nur angezeigt, wenn n ≥ 30 und die Breite des 95 %-Intervalls ≤ 20 Prozentpunkte. Sonst zeigt die App "zu wenig Beobachtungen" mit n.

**S2 Probabilistic Sharpe Ratio:**

  PSR(SR*) = Φ[ (SR̂ − SR*) · √(n − 1) / √(1 − γ̂₃ · SR̂ + ((γ̂₄ − 1)/4) · SR̂²) ]

- SR̂, SR* pro Periode (nicht annualisiert), n = Anzahl Beobachtungen
- γ̂₃ = Schiefe, γ̂₄ = **rohe** Kurtosis (Normalverteilung = 3). Wird Überschuss-Kurtosis κ gespeichert, lautet der Term (κ + 2)/4
- Status: VERIFIZIERT (Bailey & López de Prado, 2012, Gl. 11). Testwerte T7

**S3 Deflated Sharpe Ratio:**

  SR̂₀ = √V[SR_n] · ( (1 − γ) · Φ⁻¹[1 − 1/N] + γ · Φ⁻¹[1 − 1/(N·e)] )
  DSR = PSR(SR̂₀)

- γ = 0,5772156649 (Euler-Mascheroni), e = Eulersche Zahl
- N = Anzahl **unabhängiger** Versuche; V[SR_n] = Varianz der Sharpe Ratios aller Versuche, **pro Periode** (annualisierte Varianz durch Perioden pro Jahr teilen)
- N wird aus dem Backtest-Tagebuch gezählt (jeder Lauf zählt). Bei korrelierten Varianten: N̂ = ρ̂ + (1 − ρ̂) · M, mit M = Anzahl Versuche und ρ̂ = mittlere Korrelation ihrer Renditen (Bailey & López de Prado, 2014, Anhang 3; VERIFIZIERT in der zweiten Recherche). Die Autoren warnen, dass auch ρ̂ überangepasst sein kann; im Zweifel gilt N = M
- **Gate (ENTSCHEIDUNG):** DSR ≥ 0,95
- Status: VERIFIZIERT (Bailey & López de Prado, 2014, Gl. 1–2 und Zahlenbeispiel). Testwerte T8

**S4 Minimum Track Record Length:**

  MinTRL = 1 + [1 − γ̂₃ · SR̂ + ((γ̂₄ − 1)/4) · SR̂²] · (z_α / (SR̂ − SR*))²

Ergebnis in Beobachtungen (nicht Jahren). Status: VERIFIZIERT (Bailey & López de Prado, 2012, Gl. 13). Testwert T9. Die App zeigt MinTRL für jede Strategie; liegt die verfügbare Historie darunter, gilt die Strategie als nicht ausreichend belegt.

**S5 Probability of Backtest Overfitting (CSCV):**
1. Matrix M (T × N): Spalten = N Strategievarianten, Zeilen = synchrone Periodenrenditen
2. Zeilen in eine gerade Zahl S zusammenhängender, gleich großer Blöcke teilen; **S = 16**
3. Alle C(S, S/2) Kombinationen bilden (S = 16: 12.870)
4. Je Kombination c: Training J = gewählte Blöcke (Reihenfolge erhalten), Test J̄ = Rest. Kennzahl (Sharpe) je Spalte auf J und J̄. n* = argmax in J. Rang von n* in J̄ unter N Varianten (Rang N = bester). ω̄_c = Rang / (N + 1), λ_c = ln(ω̄_c / (1 − ω̄_c))
5. PBO = Anteil der Kombinationen mit λ_c ≤ 0
- **Rangbindungen (ENTSCHEIDUNG):** Durchschnittsrang
- **Gate (ENTSCHEIDUNG):** PBO ≤ 0,05. Ob die Autoren diese Schwelle ausdrücklich empfehlen, ist widersprüchlich belegt (Recherche: ja; Prüfung: nicht bestätigt) und daher als eigene Festlegung geführt
- Status: VERIFIZIERT (Bailey et al., überarbeitetes Working Paper 2015, Algorithmus 2.3). Hinweis: Das Paper nennt für S = 16 fälschlich 12.780 Kombinationen; korrekt ist 12.870. Testwert T10

**S6 Stationärer Bootstrap** für Konfidenzintervalle von Sharpe, CAGR und MDD:
1. Daten zirkulär fortsetzen: Y_t = X_{t mod N}
2. Blockstarts gleichverteilt, Blocklängen geometrisch mit Mittelwert b
3. Blöcke aneinanderhängen, erste N Werte behalten
- Blocklänge b nach Politis & White (2004) **mit Korrektur von Patton, Politis & White (2009)**: b̂ = (2Ĝ² / D̂)^(1/3) · N^(1/3), D̂ = 2ĝ(0)². Deckelung b ≤ min(3√N, N/3)
- Anzahl Wiederholungen B = 10.000, Perzentil-Intervall, fester Zufallsseed (gespeichert)
- Status: VERIFIZIERT (über Politis & White, 2004, und Patton et al., 2009; Politis & Romano, 1994, selbst nicht eingesehen). Testwerte T11

**S7 Walk-forward:** Rollierende Fenster mit Trainingslänge L_train und Testlänge L_test (je Strategie festgelegt, mindestens 5 Testfenster). Parameter werden nur im Trainingsfenster gewählt. Performance wird ausschließlich aus aneinandergehängten Testfenstern berichtet. ENTSCHEIDUNG.

**S8 Purged k-fold mit Embargo:** Für Modelle mit überlappenden Labels (z. B. Label = Rendite der nächsten 10 Tage):
- Purging: Trainingsbeobachtung i wird entfernt, wenn ihr Label-Intervall [t_i,0, t_i,1] ein Test-Label-Intervall überlappt (Start im Test, Ende im Test, oder umschließt den Test)
- Embargo: nach jedem Testblock werden zusätzlich h = 0,01 · T Beobachtungen aus dem Training entfernt (h UNVERIFIZIERT als Buchempfehlung, als ENTSCHEIDUNG übernommen)
- Keine Durchmischung, zusammenhängende Test-Folds
- Status: VERIFIZIERT über Transkription von López de Prado (2018), Snippets 7.1–7.3; Buch selbst nicht eingesehen

**S9 Brier Score und Kalibrierung** (nur wenn ein Modell Wahrscheinlichkeiten ausgibt):
- BS = (1/N) · Σ (f_t − o_t)², f = Prognosewahrscheinlichkeit, o ∈ {0, 1}. **Binäre Form**, Wertebereich [0, 1] (Briers Originalform ist doppelt so groß)
- Murphy-Zerlegung: BS = REL − RES + UNC mit REL = (1/N) Σ_k n_k (f̄_k − ō_k)², RES = (1/N) Σ_k n_k (ō_k − ō)², UNC = ō(1 − ō). Exakt nur bei gleichen Prognosen je Klasse; bei 10 Klassen gleicher Breite als Näherung ausgewiesen
- Reliability-Diagramm: ō_k gegen f̄_k je Klasse, mit Wilson-Intervall pro Punkt
- **Anzeige-Regel (ENTSCHEIDUNG):** Eine Wahrscheinlichkeit wird nur angezeigt, wenn das Modell out-of-sample besser ist als die Basisrate (BS < ō(1 − ō)) und kein Klassenpunkt mit n ≥ 30 außerhalb seines 95 %-Intervalls um die Diagonale liegt
- Status: UNVERIFIZIERT gegen Primärquellen (Brier, 1950; Murphy, 1973); Formeln aus mehreren übereinstimmenden Sekundärquellen. Testwerte T12 (trivial)

**S10 "Zu gut"-Alarm (ENTSCHEIDUNG, aus den Qualitätsstandards):** Sperre bis zur manuellen Prüfung, wenn eine der Bedingungen gilt: annualisierte SR > 3 (Tagesdaten) bzw. > 2 (Intraday nach Kosten), Trefferquote > 70 % bei ≥ 100 Trades, MDD < 5 % über ≥ 5 Jahre.

---

## 4. Kostenmodell

Jede Ausführung im Backtest und im Paper Trading trägt Kosten. Parameter werden je Instrument konfiguriert und später mit Paper-Trading-Ausführungen kalibriert.

| Nr. | Kostenart | Formel | Status |
|---|---|---|---|
| C1 | Kommission | Nach Gebührentabelle des Brokers je Produktklasse (fix, prozentual oder je Kontrakt, mit Minimum/Maximum); ohne Broker: konservative Standardtabelle | ENTSCHEIDUNG |
| C2 | Halber Spread | Ausführung zu Mid ± ½ Spread. Spread aus Bid/Ask, wenn verfügbar; sonst Schätzung nach Corwin & Schultz (2012) aus Hoch/Tief des **Tagespaars (t−1, t)**, damit bei Ausführung zum Open von t+1 nur Vergangenheit genutzt wird; mindestens Instrument-Minimum | ENTSCHEIDUNG (Corwin & Schultz UNVERIFIZIERT) |
| C3 | Slippage | **Zusätzlich** zum halben Spread: k · σ_bar · Preis, σ_bar = Volatilität einer Bar aus den vorangegangenen 20 abgeschlossenen Bars, k = 0,1 als Startwert | ENTSCHEIDUNG, wird kalibriert |
| C4 | Ausführungszeitpunkt | Signal auf Bar t → Ausführung zum Eröffnungskurs von Bar t+1 plus C1–C3. Nie zum Signalkurs | ENTSCHEIDUNG (Look-ahead-Schutz) |
| C5 | CFD-Finanzierung | Positionswert · (Referenzzins ± Aufschlag) / 365 je Nacht, Wochenenden mitgezählt | ENTSCHEIDUNG |
| C6 | Futures-Rollen | Rollen an einem festen Tag vor Verfall (je Kontrakt konfiguriert); Kosten = C1–C3 auf beide Legs | ENTSCHEIDUNG |
| C7 | Optionen | Ausführung zu Bid (Verkauf) bzw. Ask (Kauf), niemals Mid; Kommission je Kontrakt | ENTSCHEIDUNG |
| C8 | Steuern | Nicht im Backtest. Separate Anzeige einer groben Nach-Steuer-Schätzung (Abgeltungsteuer + Soli, Sparerpauschbetrag), klar als Schätzung gekennzeichnet | ENTSCHEIDUNG |

**Kostenstress (ENTSCHEIDUNG):** Jede Strategie wird zusätzlich mit doppelten Kosten getestet. Wird sie dadurch unprofitabel, erhält sie den Hinweis "kostensensitiv".

---

## 5. Positionsgröße und Risiko

**R1 Risikobudget je Trade:** B = Kapital · 1 % (einstellbar, maximal 2 %). Ohne Kapitaleingabe wird das Risiko in Prozent angezeigt. ENTSCHEIDUNG.

**R2 Stückzahl bei Stop-basiertem Sizing:** Stückzahl = abrunden( B / (|Einstieg − Stop| · Multiplikator · FX) ). Stop-Abstand typischerweise k · ATR(14) mit k je Strategie. Liegt das Ergebnis unter 1 Stück oder Kontrakt, wird kein Signal zur Umsetzung angezeigt ("Kapital zu klein"). ENTSCHEIDUNG.

**R3 Volatilitäts-Targeting:** Gewicht w = σ_Ziel / σ̂_t, gedeckelt durch das Hebel-Limit je Produktklasse. σ̂_t ist die zum Zeitpunkt t verfügbare Schätzung (Gewichtung wie I7, annualisiert mit 252 nach K5). ENTSCHEIDUNG, angelehnt an Moskowitz et al. (2012).

**R4 Hebel-Limits (ENTSCHEIDUNG):** Aktien/ETFs/ETCs 1,0 (kein Kredit); Futures und CFDs Nettoexposure ≤ 1,5 × Kapital **und** Bruttoexposure ≤ 2,0 × Kapital, strenger als ESMA; Optionen nur Starter-Set mit definiertem Risiko, Maximalverlust ≤ 2 % je Position.

**R5 Kovarianz:** EWMA mit λ = 0,94 auf täglichen Log-Renditen. Σ_t = λ Σ_{t−1} + (1 − λ) r_{t−1} r_{t−1}ᵀ. Status: UNVERIFIZIERT gegen Primärquelle (RiskMetrics Technical Document, 1996), Standardwert.

**R6 Klumpenrisiko:** Positionen werden über ihre Deltas auf Basiswerte gemappt (Optionen mit Delta, Minenaktien zusätzlich über ihre geschätzte Beta zum Gold). Ausgewiesen: Exposure je Basiswert und je Risikofaktor. Warnung, wenn ein Basiswert > 25 % des Kapitals ausmacht. ENTSCHEIDUNG.

**R7 VaR und CVaR:** Historische Simulation über die letzten 500 Handelstage mit den **aktuellen** Positionen: VaR₉₅ = 5 %-Quantil der simulierten Tages-P&L (Verlust positiv; lineare Interpolation, Hyndman-Fan Typ 7), CVaR₉₅ = Mittelwert der Verluste ≥ VaR₉₅. Optionen werden in jedem Szenario vollständig neu bewertet (nicht per Delta), mit unveränderter impliziter Volatilität je Strike (sticky strike); Volatilitätsschocks deckt R8 ab. ENTSCHEIDUNG.

**R8 Stresstests:** Feste Szenarien (Basiswert ±5/10/20/30 %, IV +10/+20 Punkte, IV −50 %) und historische Replays (19871019, Herbst 2008, März 2020, 20240805, April 2025). ENTSCHEIDUNG.

**R9 Tagesverlustlimit:** Überschreitet der Tagesverlust 3 % des Kapitals (einstellbar), zeigt die App bis zum nächsten Handelstag keine neuen Signale. ENTSCHEIDUNG.

---

## 6. Indikatoren und Strategiebausteine

Alle Indikatoren arbeiten auf abgeschlossenen Bars. **Rekursive** Glättungen (EMA, Wilder) werden erst nach einer Aufwärmphase von 10 × Periodenlänge für Signale verwendet, weil sie sonst vom Startwert abhängen; nicht rekursive Größen (SMA, Bollinger) brauchen nur ihre Fensterlänge (ENTSCHEIDUNG).

**I1 SMA:** arithmetisches Mittel der letzten n Schlusskurse einschließlich der aktuellen abgeschlossenen Bar.

**I2 EMA:** EMA_t = α · P_t + (1 − α) · EMA_{t−1}, α = 2/(n + 1), Start mit SMA der ersten n Werte. Status: Standardkonvention (UNVERIFIZIERT gegen Primärquelle).

**I3 Wilder-Glättung:** wie EMA mit α = 1/n, Start mit einfachem Mittel der ersten n Werte. Status: VERIFIZIERT über StockCharts-Reproduktion (Wilder, 1978, nicht eingesehen).

**I4 RSI(14):** Veränderungen Δ_t; Gewinne G = max(Δ, 0), Verluste L = max(−Δ, 0); Durchschnitte per Wilder-Glättung (I3); RS = Ø-Gewinn / Ø-Verlust; RSI = 100 − 100 / (1 + RS); RSI = 100, wenn Ø-Verlust = 0. Status: VERIFIZIERT (Reproduktion). Testwert T13.

**I5 ATR(14):** TR_t = max(H − L, |H − C_{t−1}|, |L − C_{t−1}|), erster Tag TR = H − L; ATR per Wilder-Glättung. Status: VERIFIZIERT (Reproduktion). Testwert T14.

**I6 Bollinger-Bänder(20, 2):** SMA(20) ± 2 · σ, σ als **Populations**-Standardabweichung (Division durch n, in pandas `ddof=0`). Status: VERIFIZIERT (bollingerbands.com).

**I7 Time-Series-Momentum (Moskowitz et al., 2012):**
- Varianz: σ²_t = 261 · Σ_{i≥0} (1 − δ) δⁱ (r_{t−1−i} − r̄_t)², r̄_t exponentiell gewichteter Mittelwert, **Schwerpunkt 60 Tage → δ = 60/61**. In pandas: `ewm(com=60, adjust=False)`, Varianz mit `bias=True` (nicht `span=60`, nicht die Standardeinstellungen)
- Signal: Vorzeichen der kumulierten Überschussrendite der letzten 12 Monate
- Position: Vorzeichen · (40 % / σ_t), mit σ_t aus Daten bis Monatsende t
- Replikation: 261 wie im Paper; im Produktivbetrieb Parameter nur über Walk-forward bestätigt
- Status: VERIFIZIERT (Gl. 1 und 5). Kein publizierter Einzelzahl-Testwert; Test über synthetische Reihe (T19)

**I8 Faber-Trendfilter:**
- Monatsende-Schlusskurs der Total-Return-Reihe gegen SMA der letzten 10 Monatsschlusskurse **einschließlich des aktuellen Monats**
- Kurs > SMA: investiert; Kurs < SMA: Geldmarkt (€STR-Proxy); Kurs = SMA: vorherigen Zustand halten
- Ausführung zum Eröffnungskurs des ersten Handelstags des Folgemonats (C4), Faber rechnet dagegen ohne Verzögerung und ohne Kosten
- Status: VERIFIZIERT (Faber, 2006/2013). Die drei Mehrdeutigkeiten des Papers sind hier festgelegt (ENTSCHEIDUNG)

**I9 Volatilitätsschätzer aus Tagesdaten (Range-basiert)** für Zeiträume ohne Intraday-Daten:
- Parkinson (1980): σ² = (1 / (4 ln 2)) · Ø[(ln H/L)²]
- Garman-Klass (1980): σ² = Ø[0,5 (ln H/L)² − (2 ln 2 − 1)(ln C/O)²]
- Yang-Zhang (2000): σ² = σ²_O + k σ²_C + (1 − k) σ²_RS, k = 0,34 / (1,34 + (n + 1)/(n − 1)), mit Overnight-Varianz σ²_O, Open-Close-Varianz σ²_C und Rogers-Satchell-Term σ²_RS = Ø[ln(H/C) ln(H/O) + ln(L/C) ln(L/O)]
- **Standard der App für Mehrtagesfenster: Yang-Zhang** (berücksichtigt Overnight-Sprünge und Drift). Yang-Zhang ist nur über ein Fenster von n ≥ 2 Tagen definiert
- **Tagesproxy für einzelne Tage** (Eingang für HAR, V2): Rogers-Satchell-Term des Tages plus quadrierte Overnight-Log-Rendite, v_t = ln(H/C) ln(H/O) + ln(L/C) ln(L/O) + (ln O_t / C_{t−1})²
- Status: UNVERIFIZIERT (aus Sekundärwissen; vor Implementierung gegen Primärquellen prüfen)

---

## 7. Volatilitätsprognose

**Wichtige Einschränkung:** HAR-RV braucht realisierte Varianz aus Intraday-Renditen. Kostenlos gibt es 5-Minuten-Daten nur für 60 Tage. Deshalb gibt es **zwei getrennte HAR-Modelle**, die nie gemischt geschätzt werden:
- **HAR-Proxy** auf dem Tagesproxy v_t aus I9 (lange Historie verfügbar), in der Anzeige als "Proxy" gekennzeichnet
- **HAR-RV** auf echter realisierter Varianz aus eigenen 5-Minuten-Aufzeichnungen; wird erst aktiv, wenn ≥ 500 Handelstage aufgezeichnet sind (Schätzfenster dann 500 Tage, ab 1.000 Tagen 1.000 Tage). Bis dahin läuft es nur im Schattenbetrieb zum Vergleich

**Zeitbezug aller Modelle (Look-ahead-Schutz):** Regressionspaare (x_{t−1}, y_t) nur mit y_t, dessen `available_at` vor dem Schätzzeitpunkt liegt. Neuschätzung wöchentlich am Wochenende; zwischen zwei Schätzungen werden die zuletzt geschätzten Parameter verwendet. ENTSCHEIDUNG.

**V1 Realisierte Varianz:** RV_t = Σ_j r²_{t,j} über 5-Minuten-Log-Renditen der regulären Handelszeit, plus quadrierte Overnight-Rendite. ENTSCHEIDUNG (5 Minuten als Kompromiss zwischen Rauschen und Mikrostruktur).

**V2 HAR-RV (Corsi, 2009):**
- Corsi definiert RV als **Volatilität** (Wurzel der Summe). Die App modelliert **log-Varianz**: ln RV²_{t+1} = c + β_d ln RV²_t + β_w ln RV²_{w,t} + β_m ln RV²_{m,t} + ε (Tages-, 5-Tages-, 22-Tages-Mittel)
- Schätzung per OLS auf rollierendem Fenster (HAR-Proxy: 1.000 Tage; HAR-RV siehe oben); Standardfehler Newey-West mit 5 Lags
- **Mehrtagesprognose mit korrekter Bias-Korrektur:** Die Fehlervarianz wächst mit dem Horizont, eine konstante Korrektur exp(μ + ½σ̂²_ε) je Schritt würde die Varianz über lange Laufzeiten **unterschätzen** und Optionen systematisch als teuer erscheinen lassen. Deshalb Simulation: 10.000 Pfade des iterierten log-HAR mit gebootstrappten Residuen (fester Seed), je Pfad exp der log-Varianzen über die Restlaufzeit summieren, Mittelwert über Pfade = Prognose der Gesamtvarianz (K10)
- Status: Modellform VERIFIZIERT (Gl. 8); log-Varianz-Variante und Simulationsverfahren sind ENTSCHEIDUNG

**V3 GARCH(1,1) (Gegencheck):**
- h_t = ω + α ε²_{t−1} + β h_{t−1}, ω > 0, α ≥ 0, β ≥ 0, α + β < 1
- Langfristige Varianz σ̄² = ω / (1 − α − β)
- Prognose: E_t[h_{t+k}] = σ̄² + (α + β)^{k−1} (h_{t+1} − σ̄²)
- Schätzung per Maximum Likelihood auf Tages-Log-Renditen mit konstantem Mittelwert und Student-t-Innovationen, **standardisiert auf Varianz 1** (Freiheitsgrade mitgeschätzt, ν > 2)
- Status: VERIFIZIERT (Bollerslev, 1986). Testwert T15

**V4 GJR-GARCH (optional):** h_t = ω + α ε²_{t−1} + γ I[ε_{t−1} < 0] ε²_{t−1} + β h_{t−1}, Stationarität α + γ/2 + β < 1. Status: UNVERIFIZIERT gegen Primärquelle (nur über Implementierung der `arch`-Bibliothek bestätigt).

**V5 Prognosegüte:** Beide Modelle werden laufend mit der QLIKE-Verlustfunktion verglichen: L = RV/ĥ − ln(RV/ĥ) − 1. Das bessere Modell der letzten 250 Tage ist führend, das andere wird als Gegencheck angezeigt. Status: QLIKE nach Patton (2011) UNVERIFIZIERT; Auswahlregel ENTSCHEIDUNG.

---

## 8. Optionen

### O1 Generalisiertes Black-Scholes-Merton (europäisch)

  d₁ = [ln(S/X) + (b + σ²/2) τ] / (σ √τ), d₂ = d₁ − σ √τ
  Call = S e^{(b−r)τ} N(d₁) − X e^{−rτ} N(d₂)
  Put = X e^{−rτ} N(−d₂) − S e^{(b−r)τ} N(−d₁)

Cost of Carry b: b = r (ohne Dividende), b = r − q (stetige Dividendenrendite q, Aktienindizes), b = 0 (Black-76, Optionen auf Futures mit S = F), b = r − r_f (Devisen). Status: VERIFIZIERT (Hull, Gl. 17.4/17.5 und 18.7/18.8; Haug über QuantLib). Testwerte T1–T3.

**Randfälle:** τ → 0 oder σ → 0: Preis = max(S e^{(b−r)τ} − X e^{−rτ}, 0) für Calls, analog Puts; direkt berechnet, nicht über d₁ (Division durch null).

### O2 Greeks (für b allgemein, e_b = e^{(b−r)τ})

| Greek | Call | Put |
|---|---|---|
| Delta | e_b N(d₁) | −e_b N(−d₁) |
| Gamma | e_b n(d₁) / (S σ √τ) | gleich |
| Vega | S e_b n(d₁) √τ | gleich |
| Theta | −S e_b n(d₁) σ / (2√τ) − (b − r) S e_b N(d₁) − r X e^{−rτ} N(d₂) | −S e_b n(d₁) σ / (2√τ) + (b − r) S e_b N(−d₁) + r X e^{−rτ} N(−d₂) |
| Rho (b = r) | τ X e^{−rτ} N(d₂) | −τ X e^{−rτ} N(−d₂) |
| Rho (b = 0, Black-76) | −τ · Call | −τ · Put |
| Dividenden-Rho ∂/∂q (b = r − q) | −τ S e_b N(d₁) | +τ S e_b N(−d₁) |

**Einheiten (ENTSCHEIDUNG, angezeigt):** Vega je 1 Volatilitätspunkt (= Formelwert / 100), Rho je 1 Prozentpunkt Zins (/100), Theta je Kalendertag (/365). Intern Formelwerte. Status: VERIFIZIERT (Hull, Kap. 19; Haug über QuantLib). Testwerte T4.

### O3 Arbitragegrenzen und Parität
- **Nur für europäische Optionen** (Indexoptionen wie SPX, ODAX, OESX; Optionen auf Futures mit europäischer Ausübung):
  - Parität mit stetiger Dividende: c + X e^{−rτ} = p + S e^{−qτ}
  - c ≥ max(S e^{−qτ} − X e^{−rτ}, 0), p ≥ max(X e^{−rτ} − S e^{−qτ}, 0), c ≤ S e^{−qτ}, p ≤ X e^{−rτ}
- **Amerikanische Optionen** (US-Einzelaktien, Eurex-Aktienoptionen): nur C ≥ max(S − X, 0), P ≥ max(X − S, 0), C ≤ S, P ≤ X; keine europäische Parität
- **Prüfung von Marktquoten auf Bid/Ask, nicht auf Mid:** Eine Quote verletzt eine Grenze nur, wenn auch das günstigste Ende (Ask bei Untergrenze, Bid bei Obergrenze) sie um mehr als eine Tick-Größe verletzt. Solche Quoten werden verworfen und protokolliert
- Modellpreise der App müssen die Grenzen immer exakt erfüllen (Invariante)
- Status: VERIFIZIERT (Hull, Gl. 17.1–17.3, 11.1–11.11)

### O4 Amerikanische Optionen

**Primärverfahren: Leisen-Reimer-Binomialbaum**, ungerade Schrittzahl N ≥ 201. Konvergiert glatt, ohne das Gerade/Ungerade-Pendeln des CRR-Baums. Status: Verfahren REPRODUZIERT (Konvergenzverhalten nachgerechnet); Formel für die Peizer-Pratt-Inversion UNVERIFIZIERT gegen Leisen & Reimer (1996), vor Implementierung prüfen.

**Zweitverfahren (Gegencheck): CRR-Baum** mit u = e^{σ√Δt}, d = 1/u, a = e^{bΔt}, p = (a − d)/(u − d), Rückwärtsinduktion mit Ausübungsprüfung an jedem Knoten; Mittelwert aus N und N+1 Schritten. Status: VERIFIZIERT (Hull, Kap. 21). Testwerte T16.

**Schnellnäherung: Bjerksund-Stensland 2002**, **papierwörtliche Variante** (erste Grenze aus h(T − t)), weil nur sie die Tabellen des Papers exakt reproduziert; Put über P(S, X, τ, r, b, σ) = C(X, S, τ, r − b, −b, σ); bei b ≥ r gilt amerikanischer Call = europäischer Call. Bivariate Normalverteilung nach K11. Status: VERIFIZIERT (Bjerksund & Stensland, 2002, Tabellen 1–4). Testwerte T17.

**Konsistenzregeln:** Leisen-Reimer und CRR (N, N+1 gemittelt, N = 1.000) dürfen relativ um höchstens 0,2 % abweichen; Bjerksund-Stensland muss ≤ Baumwert · (1 + 10⁻⁴) sein (Näherung ist eine Untergrenze) und darf höchstens 1 % darunter liegen, sonst Warnung.

### O5 Diskrete Dividenden
- Escrowed-Dividend-Modell: S* = S − Σ D_i e^{−r t_i}, Bewertung mit S* und unverändertem σ
- Bekannter Fehler: Unterbewertung bei langen Laufzeiten und hohen Dividenden (Haug, Haug & Lewis, 2003). **Regel (ENTSCHEIDUNG):** Liegen Dividenden vor Verfall mit Σ D / S > 1 % oder τ > 1 Jahr, wird zusätzlich ein nicht rekombinierender Baum mit Dividendenabschlag gerechnet und die Differenz angezeigt
- Status: VERIFIZIERT (Hull, Bsp. 15.9). Testwert T18. Die Werte von Haug, Haug & Lewis sind nur PLAUSIBEL (Eingaben erschlossen) und werden erst nach Prüfung des Artikels als Test genutzt

### O6 Implizite Volatilität
- **Europäische Optionen, primär:** Jäckel "Let's Be Rational" über `py_vollib` (maschinengenau in zwei Iterationen für alle zulässigen Eingaben). Eingabe undiskontiert: Preis · e^{rτ}, F = S e^{bτ}
- **Europäische Optionen, Zweitimplementierung:** eigenes abgesichertes Newton-Verfahren mit Vega, eingeschlossen in ein Bisektionsintervall [10⁻⁴, 5]; Newton-Schritt nur, wenn er im Intervall bleibt und Vega > 10⁻⁸, sonst Bisektion
- **Amerikanische Optionen:** Inversion des Leisen-Reimer-Baums (O4) per Brent-Verfahren auf σ; die europäische Formel wird für amerikanische Quoten nicht verwendet, weil sie die IV verzerrt
- **Abbruchkriterium:** Änderung von σ < 10⁻¹⁰ (nicht Preisfehler, weil ein kleiner Preisfehler bei geringem Vega einen großen IV-Fehler bedeuten kann)
- **Übereinstimmung beider Implementierungen:** ≤ 10⁻⁸ in σ, sofern Vega/S > 10⁻⁶; darunter gilt die Option als "IV nicht belastbar" und wird nicht für den SVI-Fit verwendet
- **Preis unter innerem Wert oder über Obergrenze:** Fehlerzustand "außerhalb Arbitragegrenzen", keine IV
- Status: Verfahren VERIFIZIERT (Jäckel, 2015, Preprint); Testwert T20

### O7 Volatility Smile: SVI
- **Forward F je Verfall:** bei europäischen Optionen aus der Put-Call-Parität der liquidesten Strike-Paare nahe am Geld (Median über ≥ 3 Paare); bei amerikanischen Optionen F = S e^{bτ} mit erwarteten Dividenden (O5)
- Raw-SVI: w(k) = a + b [ρ(k − m) + √((k − m)² + σ²)], k = ln(X/F), w = σ²_BS · τ
- Nebenbedingungen: b ≥ 0, |ρ| < 1, σ > 0, a + b σ √(1 − ρ²) ≥ 0, **Flügelbedingung b(1 + |ρ|) ≤ 2** (Lee, 2004; UNVERIFIZIERT gegen Primärquelle)
- Butterfly-Arbitragefreiheit (Pflichtprüfung nach jedem Fit): g(k) = (1 − k w'/(2w))² − (w'²/4)(1/w + 1/4) + w''/2 ≥ 0 auf einem Gitter k ∈ [−1,5; 1,5] in Schritten von 0,001
- Kalenderfreiheit: Gesamtvarianz-Kurven verschiedener Verfälle dürfen sich nicht kreuzen (∂w/∂τ ≥ 0)
- Fit: gewichtete kleinste Quadrate auf Mid-IVs, Gewicht = 1/(Spread in IV-Punkten)², nur Quoten, die O3, O6 und den Liquiditätsfilter bestehen
- Verletzt der Raw-SVI-Fit eine Bedingung: Ersatz durch SSVI, w(k, θ) = (θ/2){1 + ρφk + √((φk + ρ)² + 1 − ρ²)}, mit φ(θ) = η / (θ^γ (1 + θ)^{1−γ}), 0 < γ < 1, **η(1 + |ρ|) ≤ 2** (Butterfly-frei). Kalenderfreiheit zusätzlich: θ steigend in τ und 0 ≤ ∂(θφ)/∂θ ≤ (1/ρ²)(1 + √(1 − ρ²)) φ
- Status: VERIFIZIERT (Gatheral & Jacquier, 2014, Gl. 3.1, Lemma 2.2, Theoreme 4.1–4.2). Negativtest T21

### O8 Wahrscheinlichkeiten
- Risikoneutral: Q(S_T > X) = N(d₂). **Mit Smile** ist die korrekte digitale Wahrscheinlichkeit N(d₂) − Vega · (∂σ/∂X) · e^{rτ}, mit Vega in Formeleinheiten (je 1,00, nicht der angezeigte Wert je Punkt) und ∂σ/∂X = w'(k) / (2 σ τ X) aus dem SVI-Fit
- Real-World: P(S_T > X) = N(d₂ᴾ), d₂ᴾ = [ln(S/X) + (μ − q) τ − W/2] / √W, mit W = prognostizierte Gesamtvarianz über die Restlaufzeit (K10, V2/V3) und μ = konservative Drift-Annahme (ENTSCHEIDUNG: μ = r, d. h. keine Risikoprämie unterstellt; alternativ einstellbar)
- Risikoneutrale Dichte (Breeden-Litzenberger): g(X) = e^{rτ} ∂²c/∂X², numerisch aus dem SVI-Fit, nicht aus Rohquoten
- Die App zeigt immer beide Wahrscheinlichkeiten nebeneinander mit Beschriftung
- Status: VERIFIZIERT (Hull, Abschnitt 15.8, Gl. 20A.1)

### O9 Monte-Carlo-Verteilung einer Optionsposition
- Pfade des Basiswerts per gefiltertem historischem Bootstrap: standardisierte Residuen aus V3 werden mit der aktuellen Varianzprognose skaliert (ENTSCHEIDUNG)
- 100.000 Pfade, fester Seed, **keine antithetischen Pfade** (sie würden die empirische Schiefe der Residuen spiegeln und das Crash-Risiko von Short-Puts unterschätzen)
- Ausgaben: erwarteter P&L nach Bid/Ask und Kommission, Gewinnwahrscheinlichkeit, CVaR₉₅, Maximalverlust (analytisch aus dem Payoff, nicht simuliert)
- Standardfehler des Erwartungswerts wird angezeigt; ist er größer als |Erwartungswert| / 2, gilt das Ergebnis als "nicht unterscheidbar von null". Der Standardfehler deckt nur Simulationsrauschen ab, nicht Modellfehler; das übernimmt der Puffer in O10

### O10 Handelbarer Edge (Entscheidungsregel)
- **Zulässig sind nur Strukturen mit endlichem, analytisch bestimmtem Maximalverlust** (Starter-Set: Covered Call, cash-gedeckter Put, vertikale Spreads, gekaufte Optionen). Positionen mit unbegrenztem Verlust werden vor jeder Bewertung blockiert
- Fairer Wert V mit σ aus der eigenen Prognose (Gesamtvarianz nach K10)
- Edge_Kauf = V − Ask, Edge_Verkauf = Bid − V
- **Puffer = Kommission + Vega (je Punkt) · q₈₀**, mit q₈₀ = 80 %-Quantil des absoluten Prognosefehlers |σ̂ − σ_realisiert| in Volatilitätspunkten, gemessen out-of-sample über die letzten 250 Prognosen desselben Basiswerts und Horizonts. Solange weniger als 250 Prognosen vorliegen: q₈₀ = 5 Punkte
- Signal nur, wenn Edge > Puffer, der Monte-Carlo-Erwartungswert > 0 ist und alle Risikoregeln (R4, R8) erfüllt sind
- ENTSCHEIDUNG (Research-Report Abschnitt 4.4, nach Prüfung verschärft)

---

## 9. Markt-Intelligenz

Alle Größen in diesem Abschnitt sind **Kandidaten** und werden erst nach Walk-forward-Bestätigung (Plan Phase 8) mit Gewicht versehen.

**M1 Artikel-Stimmung:** s = P(positiv) − P(negativ) aus FinBERT, Wertebereich [−1, 1]. Firmennamen vor der Bewertung durch Platzhalter ersetzt. Zeitstempel = erster Abruf durch die App (`available_at`). ENTSCHEIDUNG.

**M2 Wöchentlicher Ton je Titel:** Mittelwert von s über alle Artikel mit available_at in der Woche bis Freitag 22:00 UTC; nur wenn ≥ 3 Artikel, sonst "keine Aussage". Standardisiert mit expandierendem Mittelwert und Standardabweichung des Titels (nur Vergangenheit, K2). ENTSCHEIDUNG, angelehnt an Heston & Sinha (2017).

**M3 Insider-Klassifikation (Cohen et al., 2012):**
- Nur offene Markttransaktionen (Form 4, Käufe und Verkäufe), keine Optionsausübungen oder Privatgeschäfte
- Zu Beginn jedes Kalenderjahres: Insider mit mindestens einem Trade in jedem der drei Vorjahre sind klassifizierbar
- **Routiniert:** hat in mindestens drei aufeinanderfolgenden Jahren im selben Kalendermonat gehandelt; **opportunistisch:** alle anderen klassifizierbaren Insider
- Käufe und Verkäufe werden für den Monatsabgleich zusammengefasst (Wortlaut "a trade"); die Klassifikation nutzt das **Handelsdatum**, aber **nur Meldungen, die zum Klassifikationszeitpunkt bereits veröffentlicht waren** (available_at ≤ Klassifikationsdatum), damit verspätete Meldungen nicht rückwirkend einfließen
- `available_at` einer Meldung = **EDGAR-Annahmezeitpunkt (acceptance datetime)**, nicht nur das Datum; ein Signal wirkt frühestens ab der nächsten Bar nach diesem Zeitpunkt
- Status: VERIFIZIERT (NBER-Working-Paper-Fassung); die Mehrdeutigkeiten sind hier festgelegt (ENTSCHEIDUNG)

**M4 Insider-Cluster (ENTSCHEIDUNG):** Mindestens zwei verschiedene opportunistische Insider mit offenen Marktkäufen innerhalb von 30 Kalendertagen, Gesamtvolumen ≥ 100.000 USD.

**M5 Tilt:** Positionsgröße eines bestehenden Signals × (1 + u), Tilt-Faktor u ∈ [−0,2; +0,2]. u = 0,1 bei Insider-Cluster, −0,1 bei standardisiertem Wochenton < −1,5, sonst 0. Vor Nutzung wird u im Walk-forward bestätigt und mit ≥ 50 % Publikationsabschlag (McLean & Pontiff, 2016) versehen. ENTSCHEIDUNG.

**M6 Experten-Scorecard:** Jede Aussage mit Richtung d ∈ {+1, −1}, Asset, Horizont H und Zeitstempel. Treffer, wenn d · (Rendite über H − Benchmarkrendite über H) > 0. Trefferquote mit Wilson-Intervall und **derselben Anzeige-Regel wie S1** (n ≥ 30, Intervallbreite ≤ 20 Prozentpunkte; bei Trefferquoten um 50 % heißt das in der Praxis rund 90 Aussagen). Vorher zeigt die Scorecard nur n und "zu wenig Aussagen". ENTSCHEIDUNG.

---

## 10. Testkatalog

Alle Werte am 20260925 zweimal unabhängig nachgerechnet. "Publiziert" ist maßgeblich im Rahmen der Toleranz aus Abschnitt 0; "Regression" sichert die Implementierung auf 6 Stellen.

### Optionen

| Nr. | Test | Eingaben | Publiziert | Regression | Quelle | Status |
|---|---|---|---|---|---|---|
| T1a | BSM Call | S=42, X=40, τ=0,5, r=0,10, b=r, σ=0,20 | 4,76 | 4,759422 | Hull Bsp. 15.6 | VERIFIZIERT |
| T1b | BSM Put | wie T1a | 0,81 | 0,808599 | Hull Bsp. 15.6 | VERIFIZIERT |
| T1c | BSM Index-Call | S=930, X=900, τ=2/12, r=0,08, q=0,03, σ=0,20 | 51,83 | 51,832957 | Hull Kap. 17 | VERIFIZIERT |
| T1d | GBSM Put | S=75, X=70, τ=0,5, r=0,10, b=0,05, σ=0,35 | 4,0870 | 4,086954 | Haug (1. Aufl.) | REPRODUZIERT |
| T1e | Merton Put | S=100, X=95, τ=0,5, r=0,10, q=0,05, σ=0,20 | 2,4648 | 2,464788 | Haug (1. Aufl.) | REPRODUZIERT |
| T2a | Black-76 Call = Put | F=19, X=19, τ=0,75, r=0,10, σ=0,28 | 1,7011 | 1,701051 | Haug (1. Aufl.) | REPRODUZIERT |
| T2b | Black-76 Call | F=1.240, X=1.200, τ=0,5, r=0,05, σ=0,20 | 88,37 | 88,373707 | Hull Bsp. 18.7 | VERIFIZIERT |
| T3 | Put-Call-Parität | S=100, X=95, τ=0,5, r=0,10, q=0,05, σ=0,20 | Residuum 0 | ≤ 10⁻¹⁰ | Hull Gl. 17.3 | VERIFIZIERT |
| T4a | Delta Call | S=49, X=50, r=0,05, σ=0,20, τ=0,3846 | 0,522 | 0,521602 | Hull Kap. 19 | VERIFIZIERT |
| T4b | Gamma | wie T4a | 0,066 | 0,065545 | Hull Kap. 19 | VERIFIZIERT |
| T4c | Vega (je 1,00) | wie T4a | 12,1 | 12,105243 | Hull Kap. 19 | VERIFIZIERT |
| T4d | Theta Call (je Jahr) | wie T4a | −4,31 | −4,305390 | Hull Kap. 19 | VERIFIZIERT |
| T4e | Rho Call (je 1,00) | wie T4a | 8,91 | 8,906574 | Hull Kap. 19 | VERIFIZIERT |
| T4f | Greeks vs. numerische Ableitung | wie T4a, zentrale Differenz: h = 10⁻⁴ für Delta, Vega, Theta; h = 10⁻³ · S für Gamma | – | relative Abweichung ≤ 10⁻⁵ | Invariante | ENTSCHEIDUNG |
| T16a | CRR amerik. Put, 5 Schritte | S=50, X=50, r=0,10, σ=0,40, τ=5/12 | 4,49 | 4,488459 | Hull Kap. 21 | VERIFIZIERT |
| T16b | dito, 30 / 50 / 100 / 500 Schritte | wie T16a | 4,263 / 4,272 / 4,278 / 4,283 | 4,263427 / 4,272021 / 4,278059 / 4,283021 | Hull Kap. 21 | VERIFIZIERT |
| T16c | Leisen-Reimer Konvergenz | wie T16a, N=1001 | – | 4,284172 (CRR-Mittel 1000/1001: 4,284496) | eigene Rechnung, zweifach | REPRODUZIERT |
| T17a | BS-2002 Call (zweistufig, papierwörtlich) | S=100, X=100, τ=0,25, r=0,08, b=−0,04, σ=0,20 | 3,51 | 3,511402 | Bjerksund & Stensland Tab. 1 | VERIFIZIERT |
| T17b | BS-2002 Calls, τ=3 | X=100, r=0,08, b=0, σ=0,20, S=80/90/100/110/120 | 3,97 / 7,23 / 11,68 / 17,28 / 23,95 | 3,970256 / 7,231368 / 11,676830 / 17,276355 / 23,954938 | Tab. 4 | VERIFIZIERT |
| T17c | BS-1993 Call (flache Grenze) | S=42, X=40, τ=0,75, r=0,04, b=−0,04, σ=0,35 | 5,2704 | 5,270404 | Haug (1. Aufl.) | REPRODUZIERT |
| T18 | Escrowed Dividend Call | S=40, X=40, σ=0,30, r=0,09, τ=0,5, je 0,50 nach 2 und 5 Monaten | 3,67 | 3,671233 | Hull Bsp. 15.9 | VERIFIZIERT |
| T20 | Implizite Volatilität | c=1,875, S=21, X=20, r=0,10, τ=0,25 | 0,235 | 0,234513 | Hull Abschnitt 15.11 | VERIFIZIERT |
| T21 | SVI Negativtest | a=−0,0410, b=0,1331, m=0,3586, ρ=0,3060, σ=0,4153, τ=1 | Butterfly verletzt | min g ≈ −0,0329 bei k ≈ 0,88 | Gatheral & Jacquier Bsp. 3.1 | VERIFIZIERT |

**Invarianten (Property-based, je 10.000 Zufallseingaben):** Parität (T3, nur europäisch); Arbitragegrenzen (O3); Call steigend in S und σ; Call steigend in τ **nur für b ≥ r** (bei b < r, z. B. Black-76 oder Dividenden, kann ein Call mit der Laufzeit an Wert verlieren); Put fallend in S; amerikanisch ≥ europäisch; amerikanischer Call = europäischer bei b ≥ r; Gamma, Vega ≥ 0; IV(Preis(σ)) = σ auf 10⁻⁸ **auf dem Bereich Vega/S > 10⁻⁶** (weit aus dem Geld unterlaufen die Preise die Rechengenauigkeit).

### Statistik und Kennzahlen

| Nr. | Test | Eingaben | Publiziert | Regression | Quelle | Status |
|---|---|---|---|---|---|---|
| T5 | Sortino | Renditen 17, 15, 23, −5, 12, 9, 13, −4 %, T=0 | 4,417 | 4,417261 | Rollinger & Hoffman | VERIFIZIERT |
| T6a | Wilson 95 % | 81 / 263 | 0,2553–0,3662 | 0,255289–0,366210 | Newcombe Tab. I | VERIFIZIERT |
| T6b | Wilson 95 % | 0 / 20 | 0,0000–0,1611 | 0–0,161125 | Newcombe Tab. I | VERIFIZIERT |
| T7a | PSR(0), normal | SR=0,458, n=24, γ₃=0, γ₄=3 | 0,982 | 0,981675 | Bailey & LdP 2012 | VERIFIZIERT |
| T7b | PSR(0), nicht normal | SR=0,458, n=24, γ₃=−2,448, γ₄=10,164 | 0,913 | 0,913361 | dito | VERIFIZIERT |
| T7c | dito mit n=36 | | 0,953 | 0,953505 | dito | VERIFIZIERT |
| T8a | DSR | N=100, V=0,5 (ann.), T=1.250, γ₃=−3, γ₄=10, SR=2,5 (ann.), 250/Jahr | SR̂₀ ≈ 0,1132; DSR 0,9004 | 0,113172; 0,900397 | Bailey & LdP 2014 | VERIFIZIERT |
| T8b | DSR mit N=46 | sonst wie T8a | 0,9505 | 0,950502 | dito | VERIFIZIERT |
| T9 | MinTRL | SR=2/√12, SR*=1/√12, γ₃=−0,72, γ₄=5,78, 95 % | 59,895 Monate | 59,895099 | Bailey & LdP 2012 | VERIFIZIERT |
| T10 | CSCV Kombinationen | S=16 | 12.870 | 12.870 | Kombinatorik (Paper-Druckfehler 12.780) | VERIFIZIERT |
| T11 | Optimale Blocklänge SB | AR(1), φ=0,7 / 0,1 / −0,4, N=200 | 11,47 / 2,01 / 5,66 | – | Patton et al. 2009 Tab. 1 | VERIFIZIERT |
| T12 | Brier | f=0,7, o=1 bzw. o=0 | 0,09 bzw. 0,49 | – | Definition | ENTSCHEIDUNG |
| T13 | RSI(14) | StockCharts-Reihe (33 Schlusskurse, siehe Anhang) | erster 70,5328, letzter 37,7730 | 70,532789; 37,772952 | StockCharts cs-rsi | VERIFIZIERT |
| T14 | ATR(14) | StockCharts-TR-Reihe (18 Werte, siehe Anhang) | 0,555; 0,593929; 0,585791; 0,568949; 0,615452 | identisch | StockCharts cs-atr | VERIFIZIERT |
| T15 | GARCH-Prognose | ω=0,05, α=0,05, β=0,9, h_{t+1}=1,3, k=10 | – | 1,189075 | Formel V3 | ENTSCHEIDUNG |
| T19 | TSMOM synthetisch | Reihe mit bekanntem Vorzeichen und konstanter Volatilität | Position = ±40 %/σ | exakt | Formel I7 | ENTSCHEIDUNG |

### Look-ahead-Tests (aus den Qualitätsstandards, für jede Funktion in Abschnitt 2–9)
- Abschneide-Test: Wert bei t mit Daten bis t = Wert bei t mit allen Daten
- Zukunfts-Störtest: Veränderung der Daten nach t ändert keinen Wert bis t
- Beide laufen für jeden Indikator, jede Kennzahl mit rollierendem Fenster, jede Volatilitätsprognose und jede Markt-Intelligenz-Größe

---

## 11. Offene Punkte vor der Implementierung

| Punkt | Warum offen | Wann klären |
|---|---|---|
| **Reproduktionsziel Phase 2** | Fabers Ergebnisse (1901–2012) beruhen auf lizenzierten GFD-Daten; kostenlos gibt es einen S&P-500-Total-Return-Index erst ab etwa 1988. Eine exakte Reproduktion ist daher nicht möglich | Gate Phase 2 wird präzisiert: (a) exakte Tests auf synthetischen Reihen mit analytisch bekanntem Ergebnis; (b) qualitative Reproduktion Faber (Timing senkt Volatilität und Drawdown gegenüber Buy-and-Hold im verfügbaren Zeitraum) |
| Leisen-Reimer-Formel | Peizer-Pratt-Inversion nicht gegen das Paper geprüft | Vor Implementierung von O4 |
| Range-Schätzer und Tagesproxy (I9) | Primärquellen nicht eingesehen | Vor Implementierung von I9 |
| Lee-Flügelbedingung (O7) | Primärquelle nicht eingesehen | Vor Implementierung von O7 |
| GJR (V4), QLIKE (V5), EWMA-Kovarianz (R5), Corwin-Schultz (C2) | Primärquellen nicht eingesehen | Vor Implementierung des jeweiligen Moduls |
| Brier/Murphy (S9) | Primärquellen blockiert | Vor Aktivierung von Wahrscheinlichkeitsanzeigen |
| Haug 2. Auflage | Werte stammen aus der 1. Auflage (über QuantLib) | Unkritisch, Werte sind nachgerechnet |
| Haug, Haug & Lewis (2003) Testwerte | Eingaben nur erschlossen | Vor Nutzung als Test |

---

## 12. Ausführungsregeln für Orders (Backtest, Simulator, Paper Trading)

Diese Regeln gelten identisch im Backtest, im Simulator und im Paper Trading. Grundsatz: **Im Zweifel die für dich ungünstigere Annahme.** Notation: O, H, L, C = Eröffnung, Hoch, Tief, Schluss der Ausführungsbar; s = Spread; slip = Slippage nach C3; tick = kleinste Kursstufe. Kommission nach C1 fällt **je Teilausführung** an (inklusive Mindestkommission).

**E1 Zeitbezug:** Eine Order mit Aufgabezeitpunkt τ_o kann frühestens in der ersten Bar ausgeführt werden, deren Beginn **strikt nach** τ_o liegt (Zeitstempel sekundengenau, UTC). Beispiel: Order um 10:00:00 bei 15-Minuten-Bars → Ausführung frühestens in der Bar ab 10:15. Im Live-Übungsdepot mit verzögerten Daten wird die Ausführung bestimmt, sobald diese Bar sichtbar ist; maßgeblich ist der tatsächliche Aufgabezeitpunkt, nicht der angezeigte veraltete Kurs. ENTSCHEIDUNG (Look-ahead-Schutz, konsistent mit C4).

**E2 Market-Order:** Kauf zu O + ½s + slip, Verkauf zu O − ½s − slip.

**E3 Limit-Order** (Kauf mit Limit Lim; Verkauf spiegelbildlich):
- **Ausführung zur Eröffnung**, wenn O + ½s + slip ≤ Lim: Kurs = O + ½s + slip (gleiche Kosten wie eine Market-Order; ein weit über dem Markt liegendes Limit ist also nie günstiger als E2)
- **Ausführung im Verlauf der Bar**, sonst, wenn L ≤ Lim − tick (der Kurs muss das Limit um mindestens eine Kursstufe durchbrechen; bloßes Berühren genügt nicht, weil Orders am Limit in der Warteschlange stehen): Kurs = Lim
- Der Ausführungskurs überschreitet das Limit nie
- ENTSCHEIDUNG (konservativ)

**E4 Stop-Order** (Verkaufs-Stop mit Stop-Kurs S; Kauf spiegelbildlich): ausgelöst, wenn L ≤ S. Kurs = min(O, S) − ½s − slip. Eine Kurslücke unter den Stop wird also zum schlechteren Eröffnungskurs ausgeführt; Stops schützen nicht vor Gaps. ENTSCHEIDUNG.

**E5 Stop-Limit** (Verkauf mit Stop S und Limit Lim ≤ S):
- **Auslösung zur Eröffnung** (O ≤ S): wird zur Limit-Order; Ausführung zur Eröffnung nur, wenn O − ½s − slip ≥ Lim, sonst weiter nach E3 in den Folgebars
- **Auslösung im Verlauf der Bar** (O > S ≥ L): Ausführung zu max(Lim, S − ½s − slip), sofern L ≤ Lim − tick bzw. der Kurs nach Auslösung das Limit erreicht; sonst bleibt die Order als Limit-Order offen. Eine Ausführung zum Eröffnungskurs ist ausgeschlossen, weil die Auslösung erst später in der Bar geschah
- Folgebars: E3
- ENTSCHEIDUNG

**E6 Reihenfolge innerhalb einer Bar:**
1. Liegt der Eröffnungskurs bereits jenseits eines Niveaus (z. B. O ≤ Stop), wird dieses Niveau zuerst ausgeführt, zum Kurs nach E4 bzw. E3
2. Werden sonst Stop-Loss und Gewinnziel derselben Position in derselben Bar berührt, gilt ohne feinere Daten **der Stop-Loss als zuerst ausgeführt**
3. Liegen feinere Bars vor, wird die Reihenfolge aus ihnen bestimmt; innerhalb der feinsten Bar gelten wieder Regel 1 und 2
4. Einstieg und Gewinnziel in derselben Bar: Das Ziel gilt in dieser Bar als **nicht** erreicht. Einstieg und Stop in derselben Bar: Der Stop gilt als ausgelöst
- ENTSCHEIDUNG (konservativ)

**E7 Volumenbegrenzung:** Je Bar werden höchstens 1 % des **Medianvolumens der vorangegangenen 20 Bars** ausgeführt (das Volumen der Ausführungsbar selbst ist bei Eröffnung noch unbekannt). Der Rest bleibt offen; Market-Orders werden in der nächsten Bar zu E2 fortgesetzt. ENTSCHEIDUNG.

**E8 Gültigkeit:** Tagesorders verfallen mit Handelsschluss, GTC-Orders nach 90 Kalendertagen. Orders außerhalb der Handelszeiten werden zur nächsten Eröffnung wirksam. ENTSCHEIDUNG.

**E9 Kapitalprüfung:** Eine Kauforder wird nur angenommen, wenn verfügbares Kapital ≥ Kaufwert + geschätzte Kosten mit 2 % Puffer auf den letzten Kurs. Reicht das Kapital bei der Ausführung (z. B. nach einer Kurslücke) nicht, wird die Stückzahl auf das Mögliche **reduziert**; ist das weniger als 1 Stück, wird die Order abgelehnt. Leerverkäufe von Aktien und ETFs sind im Simulator gesperrt (R4). ENTSCHEIDUNG.

**E10 Corporate Actions:**
- Dividenden werden am **Zahltag** gutgeschrieben (nicht am Ex-Tag; konservativ, weil das Geld erst dann verfügbar ist); der Kursabschlag am Ex-Tag wirkt sofort. Brutto, Steuerschätzung getrennt nach C8
- Splits im Verhältnis a:b passen Stückzahl (× a/b) und Einstandskurs (× b/a) an; offene Orders: Stückzahl × a/b, Limit- und Stop-Kurse × b/a, gerundet auf die Kursstufe **in die für dich ungünstigere Richtung** (Kauflimit abrunden, Verkaufslimit aufrunden); Bruchstücke werden zum Schlusskurs des Ex-Tags bar ausgeglichen
- ENTSCHEIDUNG

**E11 Optionen:** Ausführung nur zu Bid (Verkauf) bzw. Ask (Kauf) der Ausführungsbar (C7), keine Ausführung zwischen Bid und Ask. Bei Verfall automatische Ausübung, wenn im Geld um mindestens 0,01 Währungseinheiten (Konvention der OCC; UNVERIFIZIERT für Eurex, vor Freischaltung der Optionen prüfen). ENTSCHEIDUNG.

**E12 Blindmodus (nur Anzeige):** Kurse werden für die Anzeige auf 100 zum Sitzungsstart normiert, Titel und Datum verborgen. Alle Berechnungen laufen intern auf den Originalkursen, damit Kosten (Mindestkommissionen, Kursstufen) korrekt bleiben.

**E12b Schlusskurs-Order (Market-on-Close, MOC):** Wird vor dem Annahmeschluss der Schlussauktion des Handelsplatzes aufgegeben und zum offiziellen Schlusskurs P_close ausgeführt: Kauf zu P_close + slip, Verkauf zu P_close − slip (kein halber Spread, weil die Auktion einen Einheitskurs hat; slip nach C3 als Ausgleich für Auktionsungleichgewichte). Hat der Handelsplatz keine Schlussauktion, gilt der letzte gehandelte Kurs ± ½s ± slip. Annahmeschluss je Handelsplatz in der Instrumenten-Konfiguration. ENTSCHEIDUNG.

**E13 Tests** (wo nicht anders angegeben: s = 0,10; slip = 0,02; tick = 0,01; Kommission 0):

| Nr. | Test | Aufbau | Erwartet |
|---|---|---|---|
| T22 | Market-Order-Zeitpunkt | Order während Bar t | Ausführung zu O(t+1) ± ½s ± slip, nie zu C(t) |
| T23 | Limit berührt, nicht durchbrochen | Kauflimit 100, O = 101, L = 100,00 | Keine Ausführung |
| T24 | Limit mit Kurslücke | Kauflimit 100, O = 98, L = 97 | Ausführung zur Eröffnung zu 98,07 |
| T24b | Weit entferntes Limit | Kauflimit 150, O = 100 | Ausführung zu 100,07 (= Market-Order, nicht günstiger) |
| T25 | Stop mit Kurslücke | Verkaufs-Stop 95, O = 90 | Ausführung zu 89,93 |
| T25b | Stop-Limit, Auslösung im Verlauf | Stop 95, Limit 94, O = 100, H = 101, L = 90 | Ausführung zu max(94; 94,93) = 94,93, nicht zu 100 |
| T26 | Stop und Ziel in derselben Bar | Long, Stop 95, Ziel 105, O = 100, L = 94, H = 106, keine feineren Daten | Ausführung am Stop zu 94,93 |
| T26b | Eröffnung jenseits des Ziels | wie T26, aber O = 107 | Ausführung am Ziel zur Eröffnung (Verkaufslimit 105: 107 − 0,07 = 106,93) |
| T27 | Stop und Ziel mit feineren Daten | wie T26, 5-Minuten-Bars zeigen zuerst 106 | Ausführung am Ziel zu 105 |
| T28 | Volumenbegrenzung | Order 5.000 Stück, Medianvolumen der Vor-Bars 100.000 | 1.000 ausgeführt, Rest offen, Kommission je Teilausführung |
| T29 | Verzögerte Daten | Order um 10:00:00, angezeigter Kurs von 09:45, 15-Minuten-Bars | Ausführung zur Eröffnung der Bar ab 10:15, sobald sichtbar |
| T30 | Gleichheit Simulator/Backtest | Identische Orderliste in beiden Systemen | Identische Ausführungen, Kosten und Endwerte (relativ ≤ 10⁻¹²) |
| T31 | Split 2:1 | 100 Stück, Einstand 50; offenes Kauflimit 40,01 über 10 Stück | 200 Stück, Einstand 25; Limit 20,00 (abgerundet) über 20 Stück |
| T31b | Split 3:2 mit Bruchstück | 101 Stück | 151 Stück + Barausgleich für 0,5 Stück |
| T31c | Reverse Split 1:10 | 105 Stück | 10 Stück + Barausgleich für 0,5 Stück |
| T31d | MOC-Order | Kauf, Schlusskurs 100, slip 0,02 | Ausführung zu 100,02; nach Annahmeschluss aufgegeben: Ablehnung |

---

## 13. Prediction Engine (Aktien-Ranking)

### PE0 Realistische Erwartung (gilt für Anzeige und Lernmodul)

Die Engine sagt keine Kurse voraus. Sie ordnet Aktien nach der Chance, sich über 1–3 Monate besser zu entwickeln als die Mehrheit der anderen großen Aktien. Die beste publizierte Methode erreicht bei US-Einzelaktien eine monatliche Out-of-sample-Erklärungskraft von 0,40 % über alle Aktien und 0,70 % bei den 1.000 größten (Gu, Kelly & Xiu, 2020, Tab. 1, NN3). Nach Ausschluss von Kleinstwerten und nach Kosten schrumpft der Vorteil deutlich (Avramov, Cheng & Metzker, 2023; laut Recherche im Volltext: risikoadjustiertes Ergebnis ohne Kleinstwerte insignifikant, Break-even-Kosten 0,36 %; von der unabhängigen Prüfung nur anhand des Abstracts bestätigt, daher einfach geprüft).

**Folge:** Eine korrekt kalibrierte Wahrscheinlichkeit, den **Median des Universums** zu schlagen, liegt bei großen Aktien fast immer zwischen etwa 45 % und 55 %. Beispiel: Bei einem Rank-IC von 0,05 hat die Aktie am 95. Perzentil der Modellbewertung eine Wahrscheinlichkeit von 53,4 %, bei 0,08 von 55,5 % (PE8). **Zeigt die App 70–80 %, ist sie fehlkalibriert.** "So genau wie möglich" heißt hier: methodisch sauber und ehrlich kalibriert, nicht: große Zahlen.

### PE1 Ausgabe

Je Aktie und Horizont h ∈ {21, 63} Handelstage (m_h = ⌈h/21⌉ ∈ {1, 3} Monate):
- Rang und Quintil im Universum
- Kalibrierte Wahrscheinlichkeit, **den Median des Universums** über h zu schlagen, mit 95 %-Intervall
- Als Kontext daneben, klar getrennt: der historische Anteil der Universumsaktien, die den kapitalgewichteten Index über h geschlagen haben (Basisrate, langfristig expandierend geschätzt). Die Engine selbst macht **keine** Aussage über das Schlagen des Index, weil ihre Zielgröße den Index nicht enthält (PE5)
- 80 %-Prognoseintervall der Rendite relativ zum Universums-Median (PE9)
- Die drei Merkmale mit dem größten Beitrag zur Bewertung (LightGBM-eigene Beitragszerlegung, `pred_contrib`)
- Status der Engine (aktiv / Beobachtung, PE11)

### PE2 Universum und Benchmark (point-in-time)
- **USA:** zu jedem Stichtag die 500 größten Aktien nach Marktkapitalisierung mit einem Mindestumsatz von 5 Mio. USD pro Tag im 3-Monats-Median der Vergangenheit
- **Marktkapitalisierung:** Kurs × ausstehende Aktien. Aktienzahl aus EDGAR (`dei:EntityCommonStockSharesOutstanding`), maßgeblich ab dem Einreichungszeitpunkt der Meldung, **fortgeschrieben mit Splits und Kapitalmaßnahmen aus der Corporate-Actions-Tabelle (K4) mit Ex-Tag ≤ t**, summiert über alle Aktiengattungen eines Emittenten
- **Europa:** analog für die größten Werte der Heimatbörsen, aber **nur mit Kurs- und Volumenmerkmalen** (kostenlose point-in-time-Fundamentaldaten gibt es nicht)
- **Benchmark für die Gates (PE10):** kapitalgewichtete Rendite der Universumsaktien, berechnet aus denselben Kurszeitpunkten wie die Einzelaktien (keine ETF-Kurse, die an anderen Börsen zu anderen Zeiten schließen und nach Kosten und Quellensteuer notieren). Der Vergleich mit einem konkreten UCITS-ETF erfolgt nur in der Anzeige nach P10, mit dessen Kosten
- **Survivorship-Bias:**
  - Das historische Universum wird aus den EDGAR-Meldepflichtigen zum Stichtag gebildet, nicht aus heute gelisteten Aktien
  - Verschwindet eine Aktie aus den Kursdaten, obwohl sie im Universum war, wird ab ihrem letzten Kurs eine **Delisting-Rendite von −30 %** angesetzt (Richtwert für leistungsbedingte Delistings nach Shumway, 1997; UNVERIFIZIERT, vor Implementierung prüfen), außer eine Übernahme ist dokumentiert (dann letzter Kurs)
  - Fehlen für mehr als 5 % der Marktkapitalisierung des Universums an einem Stichtag Kurse, gilt der Backtest für diesen Zeitraum als **ungültig**
  - Jedes Ergebnis zeigt, wie viele Titel mit angesetzter Delisting-Rendite eingeflossen sind
- ENTSCHEIDUNG

### PE3 Fundamentaldaten aus SEC EDGAR (nur USA)
- Quelle: `companyfacts` je Unternehmen; jedes Faktum hat `start, end, val, accn, fy, fp, form, filed`
- **Zeitpunkt:** `companyfacts` liefert nur das Einreichungsdatum. Der genaue Annahmezeitpunkt wird über die Belegnummer (`accn`) aus dem Meldungsindex von EDGAR ergänzt, Zeitzone US-Eastern, gespeichert in UTC. `available_at` = Annahmezeitpunkt; Nutzung ab dem folgenden Handelstag
- **Point-in-time-Regel:** Zum Stichtag t gilt für jede Kombination (Kennzahl, start, end) der Wert aus der **zuletzt angenommenen Meldung mit available_at < t** (as-of-Verknüpfung). Korrekturen (z. B. 10-K/A) fließen so erst ab ihrer Veröffentlichung ein
- **Nicht verwenden:** die `frames`-API (liefert den zuletzt eingereichten Wert, also rückwirkend korrigierte Daten)
- Perioden über `start`/`end` und Dauer bestimmen (≈ 91 Tage Quartal, ≈ 365 Tage Jahr), **nicht** über `fy`/`fp`
- TTM-Werte = Summe der letzten vier Quartalswerte; fehlt Q4, dann Geschäftsjahr minus 9-Monats-Wert (gängige Praxis, UNVERIFIZIERT als allgemeine Regel)
- **Kennzahlen-Mapping** über Tag-Wechsel hinweg: versionierte Tabelle, in der jeder Eintrag mit dem Datum gespeichert ist, ab dem die Zuordnung erstmals bekannt war
- Abdeckung ab 2009 (XBRL-Pflicht); vorher fehlen Werte, obwohl sie öffentlich waren (konservativ, dokumentiert)
- Status: Feldstruktur und Korrektur-Fall VERIFIZIERT (Live-Abruf Apple, Testfall T33)

### PE4 Merkmale
Definitionen nach Chen & Zimmermann (2022) bzw. deren Signaldokumentation, eigene Implementierung (der dortige Code steht unter GPL-2.0 und nutzt kostenpflichtige Datenbanken; übernommen werden nur die Definitionen).

| Familie | Merkmale (Start) | Daten |
|---|---|---|
| Momentum und Umkehr | Mom12m (ohne letzten Monat), Mom6m, STreversal (1 Monat), LRreversal, High52, MaxRet, ResidualMomentum, IndMom | Kurse |
| Risiko | RealizedVol, IdioVol3F, Beta, ReturnSkew | Kurse |
| Liquidität | DolVol, Illiquidity, std_turn, zerotrade | Kurse, Volumen |
| Größe | Marktkapitalisierung (log) nach PE2 | Kurse, EDGAR |
| Bewertung und Qualität (USA) | EP, SP, BM, Asset Growth, Profitabilität (Bruttogewinn/Vermögen), Accruals | EDGAR |
| Markt-Intelligenz | Insider-Cluster (M4), wöchentlicher Nachrichtenton (M2), Analysten-Revisionen nur falls kostenlos point-in-time verfügbar | Abschnitt 9 |

**Aufbereitung:**
1. **Rangnormierung** je Stichtag über das Universum: Für n nicht fehlende Werte mit Rängen r = 1 … n (Bindungen: Durchschnittsrang) gilt x̃ = 2(r − 1)/(n − 1) − 1 ∈ [−1, 1]; bei n = 1 ist x̃ = 0; fehlende Werte = 0 (entspricht dem Median). Status: Prinzip VERIFIZIERT (Gu et al., 2020, Fn. 29); exakte Formel ENTSCHEIDUNG
2. **Veröffentlichungssperre:** Ein Merkmal darf im Backtest erst ab dem **31. Dezember des Veröffentlichungsjahres** seiner Originalstudie verwendet werden. Die Nutzung vor der Veröffentlichung überschätzt die Live-Leistung (in der Literatur um 0,52 % pro Monat; Chen, Hanauer & Kalsbach, 2025, Working Paper)
3. Keine Merkmalsauswahl nach Backtest-Ergebnis; neue Merkmale nur mit dokumentierter Literaturgrundlage, jede Aufnahme zählt als Versuch für die DSR (S3)

### PE5 Zielgröße
- y_i,t = rangnormierte Rendite der Aktie über h Handelstage ab der Ausführung am Eröffnungskurs von t+1 (C4), Rangnormierung wie PE4
- Hinweis: Die Rangnormierung einer benchmarkrelativen Rendite ist identisch mit der Rangnormierung der Rendite selbst; der Benchmark fällt heraus. Die Zielgröße misst deshalb "besser als der Median des Universums", und genau diese Aussage macht die App (PE1)
- **Regression, keine Klassifikation.** Die Wahrscheinlichkeit entsteht erst durch Kalibrierung (PE8)
- Begründung: kontinuierliche, marktrelative Ziele schneiden in der Literatur besser ab als 0/1-Ziele (Chen et al., 2025; Unterschied nicht signifikant, aber gleichgerichtet)
- ENTSCHEIDUNG auf Basis der Evidenz

### PE6 Modelle und Ensemble

| Kürzel | Modell | Rolle |
|---|---|---|
| B0 | Mom12m-Rang allein | Basislinie, muss geschlagen werden |
| B1 | Ridge-Regression auf allen Merkmalen | Lineare Basislinie und Ensemble-Mitglied |
| M1 | LightGBM-Regression, flache Bäume | Hauptmodell |
| M2 | LightGBM `lambdarank` mit Quintil-Labels | Kandidat; nur aufnehmen, wenn es M1 im Walk-forward nach PE10 schlägt (Evidenz ohne Handelskosten, daher nicht vorausgesetzt) |

- **Ensemble:** Gleichgewichteter Mittelwert der rangnormierten Bewertungen aus B1, M1 (5 Zufallsseeds) und ggf. M2, danach erneut rangnormiert. **Keine geschätzten Gewichte** (Stock & Watson, 2004; Chen et al., 2025)
- **Umrechnung in Renditeeinheiten** (für PE9 und den Clark-West-Test in PE10): ŷ_i,t = α̂ + β̂ · Bewertung_i,t, mit α̂, β̂ aus einer Regression der realisierten Median-relativen Rendite auf die Bewertung, geschätzt nur auf Trainingsdaten. Gleiches gilt für B0
- Status: ENTSCHEIDUNG auf Basis der Evidenz

### PE7 Zeitplan für Training, Tuning, Kalibrierung und Test

**Grundregel für alle Berechnungen:** Zu jedem Entscheidungszeitpunkt t werden nur Labels verwendet, deren Laufzeit **vor oder an t endet** (label_end ≤ t). Das gilt für Training, Validierung, Kalibrierung, den Rank-IC in PE8, die ACI-Überdeckung in PE9 und die Überwachung in PE11.

**Jährliche Neuschätzung zum Stichtag t0** (letzter Handelstag des Jahres), Stichtage monatlich, alle Blockgrenzen in Monaten der Stichtage:

```
Training            Validierung (36 M.)       Kalibrierung (12 M.)      Test (12 M.)
… ≤ t0−48−3m_h  | (t0−48−2m_h, t0−12−2m_h] | (t0−12−m_h, t0−m_h]    | ab t0
  Labels enden     Labels enden              Labels enden
  vor Validierung  vor Kalibrierung          ≤ t0
```

Ablauf:
1. Modelle mit jeder Gitterkonfiguration auf dem Trainingsblock schätzen, auf dem Validierungsblock bewerten, Konfiguration wählen
2. Gewählte Konfiguration auf Training + Validierung neu schätzen (alle Labels enden vor dem Kalibrierungsblock)
3. Dieses Modell bewertet den Kalibrierungsblock; darauf wird die Kalibrierung (PE8) geschätzt
4. Modell und Kalibrierung werden unverändert auf die Stichtage des Testjahres angewandt
- **Expandierendes Trainingsfenster**, Neuschätzung **einmal jährlich** (Gu et al., 2020; expandierend schlägt rollierend laut Chen et al., 2025)
- Überlappende Labels innerhalb eines Blocks (h = 63 bei monatlichen Stichtagen) sind zulässig; zwischen den Blöcken sorgen die Abstände von m_h Monaten für Purging und Embargo nach S8
- Kleines, festes Suchgitter für M1 (Blätter ∈ {8, 16, 31}, Lernrate ∈ {0,02; 0,05}, min. Beobachtungen je Blatt ∈ {200, 500}, Feature-Fraction 0,5, frühes Stoppen auf dem Validierungsblock) und Ridge-λ auf log-Gitter mit 10 Werten
- **Jede ausprobierte Konfiguration** (Gitterpunkte, Zielvarianten, Merkmalssätze, Horizonte, Haltepuffer aus PE10) wird im Backtest-Tagebuch gezählt und fließt in DSR und PBO ein
- Keine Neuschätzung als Reaktion auf eine schwache Phase
- Status: ENTSCHEIDUNG auf Basis der Evidenz

### PE8 Kalibrierung
- Abbildung: Ensemble-Bewertung → Wahrscheinlichkeit, dass die Aktie über h den Median des Universums schlägt
- **Platt-Skalierung nur mit Steigung, Achsenabschnitt fest 0:** P = 1 / (1 + exp(−a · Bewertung)). Der Achsenabschnitt ist überflüssig, weil die Basisrate bei einem Median-Ziel per Konstruktion 50 % beträgt; ein Parameter ist auf den wenigen unabhängigen Beobachtungen stabiler. Geschätzt nur auf dem Kalibrierungsblock (PE7)
- Isotonische Regression wird nicht verwendet: Aktien desselben Monats sind stark korreliert, bei h = 63 enthält ein 12-Monats-Block nur etwa 4 unabhängige Perioden; das reicht für isotonische Regression nicht (Niculescu-Mizil & Caruana, 2005: isotonisch erst ab etwa 1.000 unabhängigen Punkten überlegen)
- **Intervall der Wahrscheinlichkeit:** Block-Bootstrap über die Monate des Kalibrierungsblocks (Blocklänge m_h), 2.000 Wiederholungen, Perzentilintervall
- **Plausibilitätsgrenze (zweiseitig):**
  - ρ_U = obere Grenze des 95 %-Intervalls des mittleren monatlichen Rank-IC der letzten 36 Monate (Newey-West, Lags nach PE10), umgerechnet in eine Pearson-Korrelation: ρ = 2 · sin(π · ρ_S / 6)
  - z = Φ⁻¹(Rang / (N + 1)) für die Aktie mit Rang 1 … N; s = √(1 − ρ_U²)
  - Angezeigte Wahrscheinlichkeit wird auf [Φ(−ρ_U |z| / s); Φ(ρ_U |z| / s)] begrenzt; jede Begrenzung wird protokolliert
  - Begründung: Unter einer bivariaten Normalverteilung ist Φ(ρ z / s) die bedingte Wahrscheinlichkeit, den Median zu schlagen (Testwert T34)
- **Kalibrierungsprüfung nach S9** (Brier-Score gegen Basisrate 0,5, Reliability-Diagramm), mit Wilson-Intervallen auf Basis der **effektiven** Stichprobe (Anzahl unabhängiger Perioden × 10 Dezil-Zellen), nicht der Zahl der Aktien. Besteht die Prüfung nicht, zeigt die App nur Rang und Quintil, keine Prozentzahl
- Status: Platt-Verfahren VERIFIZIERT (Niculescu-Mizil & Caruana, 2005); Einparameter-Variante, Grenze und Stichprobenregel ENTSCHEIDUNG

### PE9 Prognoseintervalle (Adaptive Conformal Inference)
- Ziel: 80 %-Intervall für die Median-relative Rendite je Aktie über h
- Punktprognose ŷ_i,t in Renditeeinheiten nach PE6
- Abweichungsmaß: |y − ŷ| / σ̂_i, mit σ̂_i = Volatilität der Median-relativen Rendite der Aktie über h, geschätzt nur aus Vergangenheitsdaten. So werden die Intervalle für volatile Aktien breiter und für ruhige schmaler
- Start: Split-Conformal auf dem Kalibrierungsblock
- Laufende Anpassung: α_{t+1} = α_t + γ (α − err_t) mit α = 0,2; err_t = Anteil der Aktien, deren Rendite außerhalb ihres Intervalls lag (monatlich); **Aktualisierung erst, wenn die Labels nach m_h Monaten bekannt sind**
- γ = 0,1 (statt 0,005 im Paper), weil die Garantie sonst bei unserer Stichprobengröße wertlos ist
- **Was garantiert ist:** Nur die langfristige durchschnittliche Überdeckung. Ohne Verzögerung gilt |mittlere Fehlerrate − α| ≤ (max(α₁, 1 − α₁) + γ) / (γ T) (Gibbs & Candès, 2021, Prop. 4.1; VERIFIZIERT). Mit einer Verzögerung von d Monaten ergibt sich nach eigener Herleitung der Prüfung näherungsweise (max(α₁, 1 − α₁) + (d + 1) γ) / (γ T) + d / T (UNVERIFIZIERT). Für d = 3, γ = 0,1 sind das 0,125 nach T = 120 Monaten und 0,063 nach T = 240 Monaten. Die Garantie ist also schwach; maßgeblich ist die **gemessene** Überdeckung der letzten 36 Monate, die die App neben jedem Intervall zeigt
- Status: Verfahren VERIFIZIERT; Anpassungen ENTSCHEIDUNG

### PE10 Bewertung und Gates (alle müssen im Walk-forward erfüllt sein)
Newey-West-Lags für monatliche Reihen: max(m_h − 1; ⌊4 (T/100)^{2/9}⌋), T = Anzahl Monate.

1. **Rank-IC:** IC_t = Spearman(Bewertung, Rendite über h). Mittelwert > 0 mit Newey-West-t ≥ 2
2. **Besser als die Basislinie (Hauptkriterium):** Mittelwert der monatlichen Differenz IC_Ensemble − IC_B0 > 0, einseitiger Newey-West-t ≥ 1,645
3. **Besser als die Basislinie (ergänzend):** Clark-West-Test (2007) mit den Prognosen in Renditeeinheiten nach PE6 (nicht mit Rangwerten, die den Test verzerren würden): f̂ = ê₀² − [ê_E² − (ŷ₀ − ŷ_E)²], gemittelt über Aktien je Monat, einseitiger Newey-West-t ≥ 1,645
4. **Nach Kosten gegen den Benchmark:** Long-only-Portfolio des obersten Quintils, gleichgewichtet, monatliche Umschichtung mit Haltepuffer (Verkauf erst unter dem 40. Perzentil), Kosten nach Abschnitt 4, schlägt den kapitalgewichteten Universums-Benchmark (PE2) mit DSR ≥ 0,95
5. **Kontrolle gegen den Gleichgewichtungs-Effekt:** Dasselbe Portfolio muss auch das **gleichgewichtete** Universum mit identischer Umschichtung und identischen Kosten schlagen (DSR ≥ 0,95). Sonst misst Gate 4 nur den Vorteil kleinerer Aktien, nicht die Qualität der Engine
6. **Overfitting:** PBO ≤ 0,05 über alle Konfigurationen (S5)
7. **Umschlag:** jährlicher Umschlag ausgewiesen; Break-even-Kosten mindestens doppelt so hoch wie die angenommenen Kosten
- Status: Clark-West VERIFIZIERT (Clark & West, 2007); Newey-West-Faustregel UNVERIFIZIERT gegen Primärquelle (Newey & West, 1994); Gates ENTSCHEIDUNG

### PE11 Überwachung im Betrieb
- Rollierender Rank-IC über 12 und 36 Monate mit Newey-West-t; ACI-Überdeckung (nur Labels mit label_end ≤ heute)
- Fällt der 36-Monats-IC auf ≤ 0 oder die Überdeckung unter 70 %, wechselt die Engine in den Status **"Beobachtung"**: Rangliste sichtbar, aber ausgegraut und ohne Wahrscheinlichkeiten, bis die Gates wieder erfüllt sind
- Neuschätzung nur nach festem Jahresplan
- ENTSCHEIDUNG

### PE12 Verbotene "Verfeinerungen"
Diese Änderungen sehen nach Verbesserung aus, verschlechtern aber erfahrungsgemäß die Out-of-sample-Genauigkeit und sind ohne neuen Prüfdurchlauf nach PE10 nicht erlaubt:
1. Unregulierte oder sehr tiefe Modelle (OLS auf allen 920 GKX-Merkmalen: R² −3,46 %; NN4/NN5 nicht besser als NN3)
2. Geschätzte Ensemble-Gewichte oder Auswahl des zuletzt besten Modells
3. Zufällige k-fache Kreuzvalidierung oder wiederholtes Nachjustieren auf dem Testzeitraum
4. Binäres Ziel statt kontinuierlicher Zielgröße
5. Häufiges, reaktives Neuschätzen auf kurzen Fenstern; Portfolios mit hohem Umschlag

### PE13 Tests

| Nr. | Test | Aufbau | Erwartet |
|---|---|---|---|
| T32 | Rangnormierung | Werte [5, 1, 3, NaN] | [1, −1, 0, 0]; Einzelwert [7] → [0]; Bindung [2, 2, 5] → [−0,5; −0,5; 1] |
| T33 | EDGAR point-in-time | Apple, NetIncomeLoss GJ 2008: 4.834 Mio. (10-K, eingereicht 20091027), 6.119 Mio. (10-K/A, eingereicht 20100125) | Stichtag 20091231 → 4.834 Mio.; Stichtag 20100201 → 6.119 Mio. |
| T34 | Plausibilitätsgrenze | ρ_S = 0,05 bzw. 0,08 → Pearson 0,052354 bzw. 0,083751; Rang am 95. Perzentil | Obergrenze 0,534359 bzw. 0,554976; Untergrenze am 5. Perzentil 0,465641 bzw. 0,445024 |
| T35 | Zeitplan und Purging | Monatliche Stichtage, h = 21 und 63, Jahreswechsel t0 | Kein Label eines Blocks endet nach dem Beginn des Folgeblocks; alle verwendeten Labels enden ≤ t0; gleiches gilt für IC-, ACI- und Überwachungsreihen |
| T36 | Veröffentlichungssperre | Merkmal mit Studie aus 2015 | Im Backtest erst ab 20151231 verfügbar |
| T37 | ACI-Überdeckung | Synthetische Reihe mit Strukturbruch, α = 0,2, γ = 0,1, Verzögerung 3 | Langfristige Überdeckung innerhalb der Schranke aus PE9 |
| T38 | Basislinien-Gates | Synthetisch: Ensemble = rangnormiert(B0 + Rauschen), also schlechter als B0; exakt wie das echte Ensemble aufgebaut, inklusive erneuter Rangnormierung | Gates 2 und 3 lehnen nicht ab (Fehlerrate ≤ 10 % über 1.000 Simulationen) |
| T39 | Look-ahead | Abschneide- und Störtest (Abschnitt 10) für jedes Merkmal, das Ziel, die Kalibrierung und die Aktienzahl-Fortschreibung | Keine Änderung der Werte bis t |
| T40 | Split in der Aktienzahl | 4:1-Split mit Ex-Tag zwischen zwei Meldungen | Marktkapitalisierung ab Ex-Tag korrekt (Aktienzahl × 4), nicht erst ab der nächsten Meldung |

---

## Anhang: Testdaten

**T13 Schlusskurse (StockCharts, QQQQ, 20091214–20100201):** 44,3389; 44,0902; 44,1497; 43,6124; 44,3278; 44,8264; 45,0955; 45,4245; 45,8433; 46,0826; 45,8931; 46,0328; 45,614; 46,282; 46,282; 46,0028; 46,0328; 46,4116; 46,2222; 45,6439; 46,2122; 46,2521; 45,7137; 46,4515; 45,7835; 45,3548; 44,0288; 44,1783; 44,2181; 44,5672; 43,4205; 42,6628; 43,1314

**T14 True-Range-Werte (StockCharts, QQQ, April 2010):** 0,91; 0,58; 0,51; 0,50; 0,58; 0,415; 0,26; 0,49; 0,60; 0,32; 0,93; 0,76; 0,45; 0,465; 1,10; 0,48; 0,35; 1,22

---

## Änderungsprotokoll

**v1.4 (20260925):** Ordertyp E12b (Schlusskurs-Order, MOC) mit Test T31d ergänzt, nötig für den Ausstieg der Intraday-Strategie I1 (Befund M7 der Katalog-Prüfung).

**v1.3 (20260925):**
- Abschnitt 13 (Prediction Engine) ergänzt, Offener Punkt zu S3 geklärt (N̂-Formel aus Anhang 3 verifiziert)
- Korrektur gegenüber der Recherche: Für EDGAR-Daten gilt der zuletzt vor t angenommene Wert, nicht der zuerst eingereichte, weil Korrekturen ab ihrer Veröffentlichung bekannt sind
- **Unabhängige Prüfung von Abschnitt 12 und 13** (3 kritische, 9 schwere, 8 leichte Befunde), alle eingearbeitet:
  - Kritisch: Kalibrierung lag im Testjahr und nutzte Labels vor ihrem Ende → expliziter Zeitplan mit Abständen und Grundregel label_end ≤ t (PE7)
  - Kritisch: Clark-West auf Rangwerten hätte auch ein schlechteres Modell durchgelassen → Hauptkriterium ist jetzt der IC-Differenztest, Clark-West nur mit Prognosen in Renditeeinheiten (PE6, PE10)
  - Kritisch: Das Rang-Ziel enthält den Benchmark nicht; eine Wahrscheinlichkeit "schlägt den Index" wäre unbestimmt gewesen → die App zeigt die Wahrscheinlichkeit, den Median des Universums zu schlagen, und die Index-Basisrate getrennt als Kontext (PE1, PE5)
  - Schwer: Plausibilitätsgrenze zweiseitig und mit Umrechnung Spearman → Pearson; ACI mit Renditeeinheiten, skaliertem Abweichungsmaß, größerem γ und ehrlicher Aussage zur Garantie; Newey-West-Lags in Monaten; Gleichgewichtungs-Kontrolle als Gate; Benchmark aus denselben Kurszeitpunkten; Aktienzahl mit Split-Fortschreibung und über alle Gattungen; Delisting-Rendite und Ungültigkeitsregel gegen Survivorship-Bias; Limit-Order nie günstiger als Market-Order und nie über dem Limit; Stop-Limit ohne Ausführung vor der Auslösung
  - Leicht: Reihenfolge bei Eröffnung jenseits eines Niveaus, Volumengrenze aus Vergangenheit, strikte Zeitregel, Limit muss um eine Kursstufe durchbrochen werden, Kapitalprüfung mit Reduktion, Dividende am Zahltag, Split-Rundung, Rangformel festgelegt, Kalibrierung ohne isotonische Regression, Annahmezeitpunkt über Belegnummer, Mapping-Versionierung, Veröffentlichungssperre ab 31. Dezember
  - Zitat Avramov et al.: Kernzahlen nur einfach geprüft (Volltext durch Recherche, Abstract durch Prüfung)

**v1.2 (20260925):** Abschnitt 12 (Ausführungsregeln für Backtest, Simulator und Paper Trading) ergänzt.

**v1.1 (20260925)** nach unabhängiger Prüfung (0 kritische, 9 schwere, 17 leichte Befunde):
- Toleranz für 6-stellige Regressionswerte korrigiert (absolut 5 · 10⁻⁷, volle Präzision in der Testdatei)
- Invariante "Call steigend in τ" auf b ≥ r beschränkt; T4f-Schrittweite und Toleranz korrigiert; IV-Invariante auf Vega/S > 10⁻⁶ beschränkt
- HAR: zwei getrennte Modelle (Proxy vs. echte RV) statt Vermischung; Tagesproxy statt eintägigem Yang-Zhang; Mehrtages-Bias-Korrektur per Simulation (die alte Formel hätte Optionen systematisch als zu teuer erscheinen lassen)
- Europäische Parität und IV-Formel nur noch für europäische Optionen; amerikanische IV per Baum-Inversion; Grenzprüfung auf Bid/Ask
- IV-Abbruch auf σ-Änderung statt Preisfehler
- Optionsentscheidung verschärft: keine antithetischen Pfade, Puffer aus empirischem Prognosefehler, nur Strukturen mit endlichem Maximalverlust
- Insider: EDGAR-Annahmezeitpunkt, Klassifikation nur mit bereits veröffentlichten Meldungen
- Kosten: Slippage additiv zum halben Spread, Corwin-Schultz mit Tagespaar (t−1, t), σ_bar nur aus Vergangenheit
- Weitere: Aufwärmphase nur für rekursive Filter, Scorecard-Regel an S1 angeglichen, SVI um Lee-Flügelbedingung, SSVI-φ und Forward-Bestimmung ergänzt, Rho für Black-76 und Dividenden ergänzt, GARCH-Innovationen standardisiert, pandas-Parameter für TSMOM präzisiert, 252 im Produktivbetrieb, VaR-Quantil und IV-Annahme festgelegt, Bruttohebel-Grenze, relative Baumtoleranz, Symbolkonflikt τ behoben, BS-2002-Regressionswerte ergänzt, PBO-Schwelle und DSR-Fundstelle als ENTSCHEIDUNG bzw. UNVERIFIZIERT markiert, fehlende Quellen ergänzt

---

## Quellen

- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance, 20*(4), 39–69. (Gelesen: überarbeitetes Working Paper, 2015.)
- Bailey, D. H., & López de Prado, M. (2012). The Sharpe ratio efficient frontier. *Journal of Risk, 15*(2), 3–44.
- Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management, 40*(5), 94–107.
- Bjerksund, P., & Stensland, G. (2002). *Closed form valuation of American options* [Working paper]. Norwegian School of Economics.
- Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics, 31*(3), 307–327.
- Breeden, D. T., & Litzenberger, R. H. (1978). Prices of state-contingent claims implicit in option prices. *Journal of Business, 51*(4), 621–651.
- Avramov, D., Cheng, S., & Metzker, L. (2023). Machine learning vs. economic restrictions: Evidence from stock return predictability. *Management Science, 69*(5), 2587–2619.
- Chen, A. Y., & Zimmermann, T. (2022). Open source cross-sectional asset pricing. *Critical Finance Review, 11*(2), 207–264.
- Chen, M., Hanauer, M. X., & Kalsbach, T. (2025). *Design choices, machine learning, and the cross-section of stock returns* [Working paper]. (Titel nach Recherche; vor Zitat in anderem Kontext prüfen.)
- Clark, T. E., & West, K. D. (2007). Approximately normal tests for equal predictive accuracy in nested models. *Journal of Econometrics, 138*(1), 291–311.
- Gibbs, I., & Candès, E. (2021). Adaptive conformal inference under distribution shift. *Advances in Neural Information Processing Systems, 34*.
- Gu, S., Kelly, B., & Xiu, D. (2020). Empirical asset pricing via machine learning. *Review of Financial Studies, 33*(5), 2223–2273.
- Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. *Proceedings of the 22nd International Conference on Machine Learning*, 625–632.
- Stock, J. H., & Watson, M. W. (2004). Combination forecasts of output growth in a seven-country data set. *Journal of Forecasting, 23*(6), 405–430.
- Cohen, L., Malloy, C., & Pomorski, L. (2012). Decoding inside information. *Journal of Finance, 67*(3), 1009–1043. (Gelesen: NBER Working Paper 16454.)
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics, 7*(2), 174–196.
- Cox, J. C., Ross, S. A., & Rubinstein, M. (1979). Option pricing: A simplified approach. *Journal of Financial Economics, 7*(3), 229–263.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79. (Gelesen: Working Paper 2006 und Update 2013.)
- Gatheral, J., & Jacquier, A. (2014). Arbitrage-free SVI volatility surfaces. *Quantitative Finance, 14*(1). https://doi.org/10.1080/14697688.2013.819986 (Seitenzahlen UNVERIFIZIERT; gelesen: arXiv 1204.0646v4.)
- Haug, E. G. (2007). *The complete guide to option pricing formulas* (2. Aufl.). McGraw-Hill. (Testwerte aus der 1. Auflage über die QuantLib-Testsuite.)
- Haug, E. G., Haug, J., & Lewis, A. (2003). Back to basics: A new approach to the discrete dividend problem. *Wilmott Magazine*, September, 37–47.
- Heston, S. L., & Sinha, N. R. (2017). News vs. sentiment: Predicting stock returns from news stories. *Financial Analysts Journal, 73*(3), 67–83.
- Hull, J. C. (2021). *Options, futures, and other derivatives* (11. Aufl., Global Edition). Pearson.
- Jäckel, P. (2015). Let's be rational. *Wilmott*. https://doi.org/10.1002/wilm.10395 (Band und Seiten UNVERIFIZIERT; gelesen: Preprint 2016, http://www.jaeckel.org/LetsBeRational.pdf.)
- López de Prado, M. (2018). *Advances in financial machine learning*. Wiley. (Kap. 7 über Code-Transkription.)
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics, 104*(2), 228–250.
- Newey, W. K., & West, K. D. (1994). Automatic lag selection in covariance matrix estimation. *Review of Economic Studies, 61*(4), 631–653. (Nicht eingesehen; Faustregel für die Lag-Zahl vor Implementierung prüfen.)
- Newcombe, R. G. (1998). Two-sided confidence intervals for the single proportion. *Statistics in Medicine, 17*(8), 857–872.
- Patton, A., Politis, D. N., & White, H. (2009). Correction to "Automatic block-length selection for the dependent bootstrap". *Econometric Reviews, 28*(4), 372–375.
- Politis, D. N., & White, H. (2004). Automatic block-length selection for the dependent bootstrap. *Econometric Reviews, 23*(1), 53–70.
- Rollinger, T. N., & Hoffman, S. T. (o. J.). *Sortino: A "sharper" ratio*. Red Rock Capital. https://www.cmegroup.com/education/files/rr-sortino-a-sharper-ratio.pdf
- StockCharts. (o. J.). *Relative Strength Index (RSI)* und *Average True Range (ATR)* [ChartSchool mit Berechnungstabellen].
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*(158), 209–212.

**Im Text genannt, nicht eingesehen** (bibliografische Angaben aus Sekundärwissen, vor Nutzung der jeweiligen Formel prüfen):
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review, 78*(1), 1–3.
- Corwin, S. A., & Schultz, P. (2012). A simple way to estimate bid-ask spreads from daily high and low prices. *Journal of Finance, 67*(2), 719–760.
- Garman, M. B., & Klass, M. J. (1980). On the estimation of security price volatilities from historical data. *Journal of Business, 53*(1), 67–78.
- Glosten, L. R., Jagannathan, R., & Runkle, D. E. (1993). On the relation between the expected value and the volatility of the nominal excess return on stocks. *Journal of Finance, 48*(5), 1779–1801.
- J. P. Morgan/Reuters. (1996). *RiskMetrics – Technical document* (4. Aufl.).
- Lee, R. W. (2004). The moment formula for implied volatility at extreme strikes. *Mathematical Finance, 14*(3), 469–480.
- Leisen, D. P. J., & Reimer, M. (1996). Binomial models for option valuation – examining and improving convergence. *Applied Mathematical Finance, 3*(4), 319–346.
- Murphy, A. H. (1973). A new vector partition of the probability score. *Journal of Applied Meteorology, 12*(4), 595–600.
- Parkinson, M. (1980). The extreme value method for estimating the variance of the rate of return. *Journal of Business, 53*(1), 61–65.
- Patton, A. J. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics, 160*(1), 246–256.
- Politis, D. N., & Romano, J. P. (1994). The stationary bootstrap. *Journal of the American Statistical Association, 89*(428), 1303–1313.
- Shumway, T. (1997). The delisting bias in CRSP data. *Journal of Finance, 52*(1), 327–340.
- Sortino, F. A., & van der Meer, R. (1991). Downside risk. *Journal of Portfolio Management, 17*(4), 27–31.
- Wilder, J. W. (1978). *New concepts in technical trading systems*. Trend Research.
- Yang, D., & Zhang, Q. (2000). Drift-independent volatility estimation based on high, low, open, and close prices. *Journal of Business, 73*(3), 477–491.
