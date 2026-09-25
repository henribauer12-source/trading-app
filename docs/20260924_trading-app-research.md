---
title: Trading-Analyse-App – Research zu Tools, Bausteinen, Medien-/Expertensignalen und Optionen
date: 20260924
status: Research v1 (Grundlage für Plan v2)
owner: Henri
---

# Research: Tools, Bausteine, Medien-/Expertensignale, Optionen

## Kernergebnisse

- **Kein bestehendes Tool deckt deinen Plan ab.** Kommerzielle Rating-Dienste bewerten fast nur US-Aktien, und ihre Performance-Zahlen sind selbst berichtete Backtests. Die bekannten Open-Source-LLM-Agenten sind Forschungsdemos ohne Live-Nachweis. Empfehlung: **kombinieren statt kaufen oder alles neu bauen.** Die Bausteine gibt es, die eigentliche Arbeit ist die Validierungslogik.
- **Medien und "Experten" liefern für einen Privatanleger mit Verzögerung keine belastbaren Kauf- oder Verkaufssignale nach Kosten.** News werden in Sekunden bis 1–2 Tagen eingepreist, Guru- und TV-Empfehlungen haben negative oder keine Evidenz. Nur langsame Signale haben schwache bis moderate Evidenz: opportunistische Insiderkäufe, wöchentlich aggregierter negativer Nachrichtenton und ausgewählte 13F-Positionen.
- **Konsequenz für die App:** Das Medien-/Experten-Modul wird ein **Kontext- und Risikomodul** mit kleinen, gedeckelten Tilts, kein Empfehlungsgenerator. LLMs fassen zusammen und klassifizieren, sie prognostizieren keine Renditen.
- **Optionen:** Kauf kurzlaufender Out-of-the-money-Optionen, 0DTE und Optionen vor Earnings hat nachweislich negativen Erwartungswert. Defined-Risk-Verkauf von Index-Volatilität hat eine kleine, dokumentierte Prämie mit Crash-Risiko. Die Bewertungslogik vergleicht implizite Volatilität mit einer eigenen Prognose und zeigt Erwartungswert nach Spread plus Tail-Risiko.
- **Steuer:** Die 20.000-€-Grenze für die Verlustverrechnung bei Termingeschäften ist durch das JStG 2024 rückwirkend für alle offenen Fälle entfallen.
- **Sicherheit:** Mehrere naheliegende Pakete sind zu meiden, u. a. `pandas-ta` (Repo gelöscht, PyPI-Historie bereinigt) und inoffizielle `ibapi`-Pakete auf PyPI.

---

## 1. Bestehende Tools

### 1.1 Kommerzielle Signal- und Rating-Dienste

| Tool | Was es tut | Preis (ca.) | Nachweis der Performance | Lücke zu deinem Plan |
|---|---|---|---|---|
| Danelfin | KI-Score 1–10 für US- und EU-Aktien/ETFs | 19–134 $/Monat | Nur eigener Backtest (Anbieter weist selbst auf fehlende Prognosekraft von Backtests hin) | Keine Rohstoffe, Futures, CFDs, Optionen; keine News-Begründung |
| Seeking Alpha Quant | Faktorbasierte Ratings + Autorenartikel | 269–299 $/Jahr (Premium) | Teils unabhängig: Working Paper findet Prognosekraft 2016–2022, nicht peer-reviewed, kein Kostentest gesehen | Nur US-Aktien, kein Timing |
| Zacks Rank | Rang 1–5 nach Gewinnrevisionen | – | Eigene Zahlen, selbst als "hypothetisch, unauditiert" gekennzeichnet. Unabhängig (Barber et al., 2001): brutto > 4 %/Jahr, **netto nicht verlässlich > 0** | Nur US-Aktien |
| Tickeron, Trade Ideas | KI-Mustererkennung, Intraday-Scanner | 45–178 $/Monat | Nur eigene Backtests, Reviewer nennt gezeigte Ergebnisse "cherry-picked" | Blackbox, US-Daytrading |
| TrendSpider, TradingView | Charting, Backtests, Bots | 15–240 $/Monat | Nicht anwendbar (Werkzeugkasten) | Signal-/Allokationslogik musst du selbst bauen |
| LevelFields | Alerts auf 24 Ereignistypen (Filings, FDA usw.) | ab 25 $/Monat | Nur eigener Backtest | Kommt "News → Signal" am nächsten, aber US-Aktien und Blackbox |
| Koyfin | Research-Dashboards | 0–79 $/Monat | Keine Signale | Nur Research |

### 1.2 Backtest- und Algo-Plattformen

| Tool | Befund | Eignung |
|---|---|---|
| QuantConnect / LEAN | Open Source (Apache-2.0), native IBKR-Anbindung inkl. Futures, Optionen, CFDs. C#-Kern, lokal nur mit Docker. Cloud-Live-Betrieb realistisch 200–300 $/Monat | Mächtig, aber für deinen Python-Stack zu schwer. **Nicht empfohlen** für v1 |
| Portfolio Visualizer | Allokations-Backtests, bis 15 Assets kostenlos | **Nützlich zur Gegenprüfung** des Langfrist-Moduls |
| Composer | No-Code-Strategien | Nur für US-Einwohner, entfällt |

### 1.3 Open-Source-Projekte mit ähnlichem Ziel

| Projekt | Status | Bewertung |
|---|---|---|
| TradingAgents (Tauric) | Sehr populär, Apache-2.0. Paper testet 3 Monate auf ca. 5 US-Tech-Aktien; ein Release musste ein Leck "zukünftiger Reports in historischen Läufen" beheben (Look-ahead-Bias) | Forschungsdemo, keine Evidenz |
| ai-hedge-fund (virattt) | MIT, rein edukativ, handelt nicht | Ideengeber für die Agentenstruktur, nicht mehr |
| OpenBB | AGPL-3.0, produktionsreife Datenplattform | Datenlayer ohne Signale; schwere Abhängigkeiten |
| FinRobot, FinGPT | Research-Frameworks für LLM-Analyse | Frühphase |

**Unabhängige Evidenz zu LLM-Trading-Agenten:** Ein Survey (Mai 2026) findet in 19 Studien nur eine mit Transaktionskosten und keine mit Live-Trading. Langzeittests (2000–2024) zeigen, dass frühere Agentengewinne deutlich schrumpfen. Handelsagenten sind zudem per Prompt Injection und vergifteten Daten manipulierbar.

**Fazit Build vs. Buy:** Bezahlte Ratings sind keine verlässliche Edge-Quelle. Baue die App selbst aus geprüften Bausteinen, nutze Portfolio Visualizer zur Plausibilitätsprüfung.

---

## 2. Bausteine (GitHub/PyPI), geprüft am 20260924

Alle Angaben aus PyPI-Metadaten und GitHub-Seiten; nichts wurde installiert.

| Ebene | Empfehlung | Meiden | Anmerkung |
|---|---|---|---|
| Broker | `ib_async` 2.1.0 (BSD-2, Org ib-api-reloaded) | `ib_insync` (eingefroren), `ibapi` auf PyPI (Stand 2020), `ibapi-stable`/`ibapi-latest` (geben sich als IBKR aus, Platzhalter-Repo) | Offizielle IBKR-API nur von der IBKR-Website |
| Marktdaten | IBKR selbst; `yfinance` nur als gecachter Fallback | OpenBB vorerst (AGPL, schwer) | Stooq braucht seit März 2026 einen API-Key; yfinance wird rate-limitiert und ist laut README nur für private Nutzung |
| Indikatoren | TA-Lib 0.8.1 (BSD-2, Wheels enthalten die C-Bibliothek) oder eigene pandas-Funktionen | **`pandas-ta`**: Original-Repo gelöscht, PyPI-Historie bereinigt, keine Lizenz in Metadaten | Korrektur zu Plan v1, dort war `pandas-ta` vorgesehen |
| Backtest | `vectorbt` (Apache-2.0 + Commons Clause, nur Verkauf verboten) für Swing-Sweeps; `bt` (MIT) für Allokation | NautilusTrader v2 (noch Release Candidate) | backtesting.py ist AGPL, für private Nutzung unproblematisch |
| Validierung | `skfolio` (BSD-3, `WalkForward`, `CombinatorialPurgedCV`) + eigene Implementierung von Deflated Sharpe Ratio und PBO (je ca. 50 Zeilen nach Bailey & López de Prado) | mlfinlab (proprietär), pypbo (AGPL, veraltet) | |
| Portfolio | `skfolio` | – | Deckt Validierung gleich mit ab |
| News/Sentiment | FinBERT (ProsusAI, Apache-2.0) lokal über `transformers`; GDELT (kostenlos, 1 Anfrage/5 s); Finnhub Free Tier | NewsAPI Free (nur Entwicklung, nicht produktiv erlaubt); Loughran-McDonald-Wörterbuch (nur akademisch frei) | |
| Experten-/Filingdaten | `edgartools` (MIT, Form 4 Insider, 13F); SEC verlangt E-Mail im User-Agent, max. 10 Anfragen/s | – | Einzel-Maintainer-Risiko |
| Makro | `fredapi` (FRED), `sdmx1` (EZB) | `pandasdmx` (veraltet), `dbnomics` (AGPL) | |
| Optionen | `py_vollib` (IV, Greeks), `QuantLib` (amerikanische Optionen, Bäume), eigene numpy-Payoffs | `py_vollib_vectorized` (seit 2021 verwaist) | Optionsketten und IBKR-eigene Greeks über `ib_async` |
| Dashboard | Streamlit + Plotly; APScheduler 3.x | APScheduler 4 (Alpha) | Streamlit sammelt standardmäßig Nutzungsstatistiken: `browser.gatherUsageStats=false`, `server.address=127.0.0.1` |

**Installationshygiene:** Versionen mit Hashes pinnen (`pip-compile --generate-hashes`), `pip-audit` laufen lassen, Paketnamen aus den offiziellen Repos kopieren statt tippen (Typosquats wie `yfinnace` waren Malware), IB Gateway und Streamlit nur auf localhost, Schlüssel in `.env` außerhalb von Git.

---

## 3. Evidenz: Medien, Experten, Social Media

Bewertung aus Sicht eines Privatanlegers, der mit Stunden bis Tagen Verzögerung und realistischen Kosten handelt.

| Quelle | Zentrale Studien | Befund | Bewertung |
|---|---|---|---|
| Medienstimmung (Markt) | Tetlock (2007) | Pessimismus sagt kurzfristig tiefere Kurse voraus, danach Umkehr | Schwach (nur Kontext) |
| Firmennews | Tetlock et al. (2008); Heston & Sinha (2017) | Tägliche News wirken 1–2 Tage; **wöchentlich aggregierter negativer Ton** wirkt ca. ein Quartal | Schwach bis moderat (wöchentlich) |
| Geschwindigkeit | Busse & Green (2002) | TV-Berichte in Sekunden bis ca. 1 Minute eingepreist | Zeigt, warum verzögertes Handeln auf News nicht lohnt |
| LLM-News-Scores | Lopez-Lira & Tang (2023, Working Paper) | Brutto ca. 34 Bp/Tag, nach Kosten von 20 Bp unprofitabel; Sharpe fällt von 6,5 (2021) auf 1,2 (2024) | Schwach für Privatanleger |
| Look-ahead in LLMs | Glasserman & Lin (2023); Gao et al. (2025) | Backtests auf Trainingsdaten des Modells sind aufgebläht; Firmennamen verzerren die Stimmung | Warnung: LLM-Backtests vor dem Trainings-Cutoff sind wertlos |
| Seeking Alpha | Chen et al. (2014) | Negativer Ton sagt Renditen über ca. 3 Monate voraus (2005–2012) | Moderat historisch, heute unbelegt |
| Twitter/StockTwits | Bartov et al. (2018); Cookson et al. (2024) | Wirkung nur 1 Tag; hohe Aufmerksamkeit sagt **niedrigere** Renditen voraus | Schwach (als Warnsignal nutzbar) |
| WallStreetBets | Bradley et al. (2024) | Vor GameStop Prognosekraft, danach **vollständig verschwunden** | Keine |
| Analysten-Revisionen | Womack (1996); Altınkılıç et al. (2016) | Drift nach Revision seit 2003 ca. null | Schwach |
| Analysten-Konsens | Barber et al. (2001) | Brutto > 4 %/Jahr, **netto nicht verlässlich > 0** | Schwach |
| Kursziele | Bradshaw et al. (2013) | Ca. 15 Prozentpunkte zu optimistisch, nur 38 % nach 12 Monaten erreicht | Negativ |
| TV (Jim Cramer) | Engelberg et al. (2012) | Übernacht-Sprung, der sich über Monate umkehrt | Negativ |
| Newsletter | Metrick (1999) | Keine signifikante Stock-Picking-Fähigkeit | Negativ |
| Markt-Gurus | CXO Advisory (nicht peer-reviewed) | 46,9 % Trefferquote über 6.582 Prognosen | Negativ |
| US-Insider | Lakonishok & Lee (2001); Cohen et al. (2012) | Käufe informativ, Verkäufe nicht; **opportunistische** Käufe ca. 82 Bp/Monat, routinemäßige ca. 0; vor allem Small Caps | **Moderat** (Käufe, Haltedauer Monate) |
| Deutsche Directors' Dealings | Betzer & Theissen (2009) | Abnormale Renditen, aber nach Bid-Ask-Kosten nicht ausnutzbar | Schwach |
| 13F-Kopieren | Frank et al. (2004); Agarwal et al. (2013) | Kopierer erreichen die Fonds nach Kosten etwa, sparen aber nur Gebühren; beste Ideen werden verzögert gemeldet | Schwach bis moderat |
| Publikationseffekt | McLean & Pontiff (2016) | Prognosekraft sinkt nach Veröffentlichung um 58 % | ≥ 50 % Abschlag auf jedes publizierte Signal |
| Gold/Rohstoffe | Smales (2014); Chi et al. (2024) | Gold reagiert auf News am selben Tag; "recycelte" News führen zu Überreaktion mit Umkehr über ca. 30 Tage | Schwach für Gold-Timing |

### Folgen für das Design

1. **Keine primären Kauf-/Verkaufssignale aus Medien oder Experten.** Kern bleibt die regelbasierte, validierte Strategie-Engine.
2. **Erlaubte Tilts (klein, gedeckelt, mit ≥ 50 % Abschlag):** Cluster opportunistischer Insiderkäufe, wöchentlicher negativer Nachrichtenton, ausgewählte 13F-Positionen als Watchlist.
3. **Als Risikowarnungen:** Aufmerksamkeitsspitzen in Social Media, TV-/Forum-Hype, extremer Medienpessimismus, recycelte Rohstoff-News.
4. **Nicht als Renditeinput:** Guru- und Strategen-Prognosen, TV-Tipps, Newsletter, WallStreetBets, Kursziele, einzelne Analystenrevisionen. Höchstens als "Was gesagt wird", jeweils mit sichtbarer Trefferbilanz.
5. **LLMs fassen zusammen und klassifizieren.** Firmennamen werden bei der Stimmungsbewertung anonymisiert, jede Aussage wird mit Zeitstempel geloggt und live gegen eine Benchmark gemessen, bevor sie Gewicht bekommt.

---

## 4. Optionen

### 4.1 Was mit Privatanlegern passiert

- Privatanleger machen über 60 % des US-Optionsvolumens aus, bevorzugen billige, kurzlaufende Optionen, zahlen im Schnitt ca. 12,6 % Spread und verlieren im Mittel (Bryzgalova et al., 2023).
- Rund um Earnings verlieren Privatanleger 5–9 %, bei hoher erwarteter Volatilität 10–14 % (de Silva et al., 2026).
- Über 75 % der Retail-Trades in S&P-500-Optionen sind 0DTE, ca. 60 % der Verluste sind Transaktionskosten (Beckmeyer et al., Working Paper).
- Am erfolgreichsten ist bei Privaten wie Institutionen der Verkauf von Volatilität (Hu et al., 2024).
- Gegenposition (Cboe-finanziert): Mit Preisverbesserung waren Retail-Trades 2020–2023 leicht, aber nicht signifikant profitabel. Die Höhe der Verluste ist also umstritten, die Richtung nicht.

### 4.2 Evidenz pro Strategietyp

| Strategie | Bewertung | Anmerkung |
|---|---|---|
| Kauf kurzlaufender OTM-Optionen, 0DTE, Optionen vor Earnings | **Negativer Erwartungswert** (starke Evidenz) | Mehrere unabhängige Datensätze |
| Cash-gedeckter Index-Put-Verkauf | Kleine positive Prämie | Volatilitätsprämie; Crash-Jahre wie 2008, 2020 |
| Covered Calls (Index, Large Caps) | Etwa neutral bis leicht positiv | Überwiegend Aktienbeta, Aufwärtspotenzial gedeckelt (Israelov & Nielsen, 2015) |
| Dauerhafte Schutzputs | Teuer | Als Versicherung vertretbar, nicht als Renditequelle (Israelov, 2019) |
| Vertikale Spreads | Dünne Evidenz | Spread wird auf zwei Legs gezahlt |
| Volatilitätsverkauf auf Einzelaktien | Dünne Evidenz | Gap- und Sprungrisiko |

### 4.3 Modellwahl

- **Black-Scholes-Merton:** europäische Optionen (SPX, XSP, Eurex-Indexoptionen)
- **Black-76:** Optionen auf Futures
- **Binomialbaum (≥ 200 Schritte) oder Bjerksund-Stensland:** amerikanische Optionen (US-Einzelaktien, Eurex-Aktienoptionen), inkl. diskreter Dividenden
- **SVI-Fit** für den Volatility Smile; Heston nur optional für Research
- **IV-Rank/-Perzentil** nur beschreibend, ohne eigene Prognosekraft
- **"Probability of Profit"** aus Optionspreisen ist eine risikoneutrale Wahrscheinlichkeit. Die App zeigt deshalb drei Werte nebeneinander: risikoneutral, real-world aus eigener Volatilitätsprognose und Erwartungswert mit 1 %/5 %-Tail-Verlust.

### 4.4 Bewertungslogik (Vorschlag)

1. **Liquiditätsfilter:** Kontrakt verwerfen bei (Ask − Bid)/Mid > 10 %, Open Interest < 500 oder Restlaufzeit < 7 Tage
2. **Volatilitätsprognose:** HAR-RV (Corsi, 2009) auf realisierter Varianz, GARCH als Gegencheck, bei Earnings in der Laufzeit ein separater Sprungterm
3. **Volatilitäts-Edge:** IV aus dem SVI-Fit minus Prognose, umgerechnet in einen vega-gewichteten Geldbetrag
4. **Fairer Wert** mit dem passenden Modell und der eigenen Prognose. Handelbarer Edge = fairer Wert minus Ask (Kauf) bzw. Bid minus fairer Wert (Verkauf), muss Gebühren plus Modellfehler-Puffer übersteigen
5. **Real-World-Verteilung** per Monte Carlo: erwarteter P&L nach Spread, Gewinnwahrscheinlichkeit, CVaR 95 %
6. **Maximalverlust und Stresstests:** Basiswert ±5/10/20/30 %, IV +10/+20 Punkte und −50 % IV-Crush, historische Replays (1987, 2008, 20240805, April 2025), Frühausübungscheck
7. **Entscheidungsregeln:** Go nur bei positivem Netto-Erwartungswert, Edge über Puffer, Maximalverlust ≤ 2 % des Portfolios und tragbarem Stressverlust; Warnung bei dünner Liquidität oder Earnings; Block bei unbegrenztem Verlust. Jeder Trade wird geloggt, Prognose gegen Ergebnis.

### 4.5 Starter-Set und Ausschlüsse

**Erlaubt:** Covered Calls, cash-gedeckte Index-Puts, vertikale Spreads mit definiertem Risiko, Schutzputs nur als bepreiste Versicherung.

**Ausgeschlossen für den Einstieg:** nackte Short Calls, Short Straddles/Strangles, 0DTE und Weeklys, Optionskauf vor Earnings, billige OTM-"Lottoscheine", ungedeckte Short Puts auf Margin, Ratio-/Backspreads und Calendars, Optionen auf Futures, US-ETF-Optionen (PRIIPs-Status unklar).

### 4.6 Deutschland/EU

- **Handelbar bei IBKR:** Eurex-Index-, Aktien- und Futuresoptionen sowie US-Einzelaktien- und Indexoptionen (die OCC veröffentlicht PRIIPs-KIDs). US-ETF-Optionen (SPY, QQQ) für EU-Privatkunden **unklar**, direkt bei IBKR prüfen. Stattdessen SPX/XSP oder Eurex.
- **Optionsscheine sind keine echten Optionen:** Emittentenrisiko, Emittent ist Market Maker und setzt den Spread, kein Stillhaltergeschäft möglich.
- **Steuer:** Die JStG-2024-Änderung strich die 20.000-€-Grenze für Termingeschäfte rückwirkend für alle offenen Fälle. Verluste fließen in den allgemeinen Kapitalertragstopf; der separate Topf für Aktienveräußerungsverluste bleibt. Stillhalterprämien sind bei Zufluss steuerpflichtig (BMF-Schreiben vom 20250514). IBKR behält keine deutsche Abgeltungsteuer ein, alles läuft über Anlage KAP (gängige Praxis, nicht offiziell verifiziert). Ich bin kein Steuerberater.
- **IBKR-Berechtigungsstufen:** Level 1 Covered Calls, Level 2 Long-Optionen und Debit Spreads, Level 3 Short Puts und Credit Spreads, Level 4 nackte Positionen. Die genauen Schwellen (Erfahrung, Vermögen) sind nicht verifiziert.

---

## 5. Nicht verifiziert oder offen

- IBKR: US-ETF-Optionen für EU-Retail, Optionsberechtigungs-Schwellen, Marktdatenkosten
- Finnhub: welche Endpunkte (Insider, Analysten) im Free Tier enthalten sind
- Chen et al. (2014): Effektgröße und Wirkung nach Kosten
- Lopez-Lira & Tang: Journal-Publikation konnte ich nicht bestätigen, zitiert wird die Working-Paper-Fassung
- Historische Optionsketten für Backtests sind kostenpflichtig (Anbieter nicht recherchiert). Ohne sie lässt sich die Optionslogik nur vorwärts im Paper Trading prüfen.
- Point-in-time-News-Archive für saubere Backtests: GDELT ist frei, aber grob; kommerzielle Archive nicht recherchiert.

---

## Quellen (Auswahl, APA)

- Barber, B., Lehavy, R., McNichols, M., & Trueman, B. (2001). Can investors profit from the prophets? *Journal of Finance, 56*(2), 531–563.
- Bradley, D., Hanousek, J., Jame, R., & Xiao, Z. (2024). Place your bets? The value of investment research on Reddit's WallStreetBets. *Review of Financial Studies.*
- Bradshaw, M. T., Brown, L. D., & Huang, K. (2013). Do sell-side analysts exhibit differential target price forecasting ability? *Review of Accounting Studies, 18*(4), 930–955.
- Bryzgalova, S., Pavlova, A., & Sikorskaya, T. (2023). Retail trading in options and the rise of the big three wholesalers. *Journal of Finance, 78*(6), 3465–3514.
- Busse, J. A., & Green, T. C. (2002). Market efficiency in real time. *Journal of Financial Economics, 65*(3), 415–437.
- Chen, H., De, P., Hu, Y., & Hwang, B.-H. (2014). Wisdom of crowds: The value of stock opinions transmitted through social media. *Review of Financial Studies, 27*(5), 1367–1403.
- Cohen, L., Malloy, C., & Pomorski, L. (2012). Decoding inside information. *Journal of Finance, 67*(3), 1009–1043.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics, 7*(2), 174–196.
- de Silva, T., Smith, K., & So, E. C. (2026). Losing is optional: Retail option trading and expected announcement volatility. *Review of Finance, 30*(2).
- Engelberg, J., Sasseville, C., & Williams, J. (2012). Market madness? The case of Mad Money. *Management Science, 58*(2), 351–364.
- Heston, S. L., & Sinha, N. R. (2017). News vs. sentiment: Predicting stock returns from news stories. *Financial Analysts Journal, 73*(3), 67–83.
- Israelov, R., & Nielsen, L. N. (2015). Covered calls uncovered. *Financial Analysts Journal, 71*(6), 44–57.
- Lopez-Lira, A., & Tang, Y. (2023). *Can ChatGPT forecast stock price movements? Return predictability and large language models* [Working paper]. https://arxiv.org/abs/2304.07619
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Metrick, A. (1999). Performance evaluation with transactions data: The stock selection of investment newsletters. *Journal of Finance, 54*(5), 1743–1775.
- Tetlock, P. C. (2007). Giving content to investor sentiment: The role of media in the stock market. *Journal of Finance, 62*(3), 1139–1168.
- Tetlock, P. C., Saar-Tsechansky, M., & Macskassy, S. (2008). More than words: Quantifying language to measure firms' fundamentals. *Journal of Finance, 63*(3), 1437–1467.
- Womack, K. L. (1996). Do brokerage analysts' recommendations have investment value? *Journal of Finance, 51*(1), 137–167.
- Bundesministerium der Finanzen. (20250514). *Einzelfragen zur Abgeltungsteuer* [BMF-Schreiben].
- Flick Gocke Schaumburg. (o. J.). *Update zum JStG 2024: Rückwirkender Entfall der Verlustverrechnungsbeschränkung für Termingeschäfte.* https://www.fgs.de/en/news-and-insights/blog/detail/update-zum-jahressteuergesetz-2024-jstg-2024-rueckwirkender-entfall-der-verlustverrechnungsbeschraenkung-fuer-termingeschaefte-und-forderungsausfaelle-im-privatvermoegen
- Tool- und Paketangaben: jeweilige GitHub-/PyPI-Seiten, Stand 20260924 (u. a. github.com/ib-api-reloaded/ib_async, github.com/ta-lib/ta-lib-python, github.com/polakowo/vectorbt, skfolio.org, github.com/dgunning/edgartools, github.com/vollib/py_vollib).
