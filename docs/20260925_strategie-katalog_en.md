---
title: Trading analysis app – strategy catalogue (Phase 0)
date: 20260925
status: v1.2 (v1.1 independently reviewed; v1.2 adds overlay variants for the "Anlegen" (Invest) core module)
owner: Henri
basis: 20260925_trading-app-plan-v9_en.md, 20260925_anlage-spezifikation_en.md, 20260925_rechenkern-spezifikation-v1.4.md
language: en
binding: this English text (since 20260925)
supersedes: archive/20260925_strategie-katalog.md (German original of v1.2, no longer binding)
---

# Strategy catalogue v1.2 (Phase 0)

**Binding text.** This English document is the binding strategy catalogue. The German original is archived in `archive/20260925_strategie-katalog.md` and no longer binding. German tax and legal terms (e.g. Abgeltungsteuer) are kept as proper nouns. The YAML keys and most YAML values are still German identifiers; they change only together with the code that will read them.

## 0. Summary

The catalogue formalises **8 core and candidate strategies**, **4 options strategies for Phase 7** and a **control group of 11 popular rules**. Each strategy has an exact rule with parameters from the primary source, an evidence grade, the explained deviations from the source and a YAML definition. Reproduction targets and look-ahead traps are collected in section 9. This fulfils the Phase 0 gate (at least 8 formalised strategies with evidence grade).

**What the research has shown:**
- **Robust and implementable with free data:** passive world portfolio with rebalancing; Faber trend filter (above all as drawdown protection); trend following on ETFs and gold ETCs
- **With significant limitations:** momentum across asset classes (constructed differently than in the source), equity momentum and 52-week high (survivorship bias, long side only, initially USA only), volatility-managed equity share (mixed out-of-sample evidence)
- **Dead after costs or since publication:** short-term reversal and post-earnings drift in large stocks; they remain in the control group as learning examples
- **Popular retail rules** (moving averages, golden cross, RSI, Bollinger, candlestick patterns): no evidence since 1987 after costs and multiple testing. The app tests them anyway so that you see this on real data
- **Intraday:** Only intraday momentum in the last half hour has peer-reviewed evidence, and even that disappeared in an out-of-sample study. The best-known intraday strategies come from non-peer-reviewed papers by authors with a commercial interest. **I1 can pass the gates at the earliest after about 3 years of own data**
- **Not implementable at 0 €:** commodity carry (needs futures curves)

| ID | Strategy | Module | Role | Evidence | Data at 0 € |
|---|---|---|---|---|---|
| L1 | Passive world portfolio with rebalancing | Long-term | Core and benchmark | A | Yes |
| L2 | Faber trend filter (GTAA 5) | Long-term | Core | B (drawdown), C (return) | Yes |
| L3 | Asset-class rotation by momentum | Long-term | Candidate | C | Yes |
| L4 | Volatility-managed equity share | Long-term | Candidate | C | Yes |
| S1 | Trend following (TSMOM 1/3/12), long/flat | Swing | Core | B | Yes |
| S2 | Equity momentum 12-1, long-only, USA | Swing | Candidate | C | Partly |
| S3 | 52-week-high momentum, long-only, USA | Swing | Candidate | C | Partly |
| I1 | Intraday momentum, last half hour | Intraday | Candidate | C | Own recording only |
| O1–O4 | Put credit spread, covered call, vertical spreads, protective put | Options | Candidates Phase 7 | C | Partly |
| K1–K11 | Popular rules, cost and decay examples | Control | Control | D | Yes |

**Verification status of the figures:** Most values were checked from two sides (full-text research, independent review). Checked from one side only are: Jegadeesh & Titman (1993), Barroso & Santa-Clara (2015), Daniel & Moskowitz (2016), Sullivan et al. (1999), Chague et al. (2020). They are marked "single-checked" in the text.

---

## 1. Evidence scale and roles

| Grade | Meaning |
|---|---|
| **A** | Several peer-reviewed studies, different markets and periods, holds after realistic retail costs |
| **B** | Peer-reviewed evidence with out-of-sample confirmation, but cost-sensitive, decaying or only partly implementable with retail instruments |
| **C** | Single study, mixed out-of-sample evidence, only documented gross, or modified so far from the source that its evidence applies only to a limited extent |
| **D** | No evidence, negative evidence after costs, vanished since publication, or only non-peer-reviewed claims by vendors |

| Role | Meaning in the app |
|---|---|
| Core | Is built and tested first; shows signals after passing the gates |
| Candidate | Is tested; shows signals only if all gates are passed |
| Control | Is tested with the same engine to show that the testing rejects nonsense; results appear in the "Evidence" area and in the learning module, **never** as a signal. If a control rule unexpectedly passes all gates, this is investigated as a possible error of the engine |
| Not implementable | Documented, but not built |

---

## 2. General rules for all strategies

**G1 Parameters from the source.** Each strategy starts with the parameters of its primary source. Variants are only allowed if they appear in the source itself or in peer-reviewed follow-up literature; they are listed in the catalogue in advance. Subsequent parameter search is forbidden.

**G2 Execution.** Signals on completed bars, execution at the earliest at the opening price of the next bar (C4, E1–E13). Many sources trade at the signal price; this deviation is intended and makes the app more conservative.

**G3 Instruments.** Funds only as UCITS ETFs or ETCs. No short selling and no leverage in long-term and swing as long as learning stage 5 has not been completed (R4). Long/short variants are marked as "Phase 5 variant". **Exception for the control group:** control rules are tested on the instruments of the source (e.g. US ETFs), because they never generate signals and only demonstrate the testing.

**G4 Data proxies and currency.**
- For backtests before the launch of a UCITS product, the index history is extended using a US-listed ETF with the same index basis. The splice point is marked in the result. Proxies serve **only** the backtest
- **Adjustments to the proxy:** The distributions of the US proxy are reduced by 15 % (withholding tax of an Irish UCITS fund on US dividends under the double taxation agreement; rate UNVERIFIZIERT, check before implementation), and the difference in ongoing charges (TER) is deducted daily
- **Conversion into EUR:** ECB reference rate of the same day (published around 16:00 CET, i.e. before the US closing price; no look-ahead, but up to 6 hours older than the closing price, which adds noise to daily statistics). On TARGET holidays without a reference rate, the last rate is carried forward and marked (K12). Before 19990104 a synthetic EUR rate is formed from the DM/USD rate (FRED) and the fixed conversion rate of 1.95583 DM/EUR
- **Evaluation calendar:** one calendar per strategy, namely that of the trading venue of the UCITS product held (usually Xetra). "Last trading day of the month" refers to this calendar
- ENTSCHEIDUNG

**G5 Cash and interest.** Uninvested capital earns the risk-free rate:
- from 20191001 €STR; from 19990104 to 20190930 EONIA − 8.5 basis points (the ECB defined EONIA from October 2019 as €STR + 8.5 basis points; the spread is also used retroactively as an approximation); before 1999 the Bundesbank's Frankfurt overnight money rate (availability as a free time series UNVERIFIZIERT)
- **Publication:** €STR is published on the following business day. At evaluation time t, only interest rates with available_at ≤ t are used; for the last day the previous day's rate applies

**G6 Publication effect and sample.**
- Each strategy has in its YAML the **end of the sample of its source** (`stichprobenende`), not just the publication year
- **The gates (G7) are tested exclusively on data after the end of the sample.** In this period the source did not choose its parameters. The full period is shown for information only
- If the period after the end of the sample is not sufficient for MinTRL (S4), the strategy is deemed "insufficiently supported" and shows no signals
- **Expected live effect** in the display: the active return relative to the benchmark (G8) after the end of the sample; if less than MinTRL is available for this, the active return of the full period with a **60 % haircut** (McLean & Pontiff, 2016: 58 % decline after publication). The haircut applies only to the active return, not to the market return
- ENTSCHEIDUNG

**G7 Gates (all must be met before a strategy shows signals):**
1. All leakage tests green (quality standards, section 3.3)
2. **Active return** (strategy minus gate benchmark according to G8, both after costs) with DSR ≥ 0.95 across all counted trials according to G9; PSR, DSR and MinTRL are calculated on the active return (SR* = 0 for the active return)
3. t-statistic of the mean active return (Newey-West) ≥ 3.0 (Harvey, Liu & Zhu, 2016, recommend this threshold because of the large number of factors tested; not inspected)
4. With doubled costs the active return remains positive, otherwise flagged "cost-sensitive"; in the intraday module then no signals
5. Available period after the end of the sample ≥ MinTRL
6. No "too good" alert (S10) open
7. **PBO ≤ 0.05 only if the app uses a variant instead of the source rule.** The source rule itself is not tested via PBO because it was not selected from the variants; the variants then serve only as a robustness report
8. **Risk gate for L2 and L4** (strategies whose benefit according to the source lies in risk), replaces gates 2 and 3:
   - Benchmark: static mix with the **average invested share of the strategy per asset class** over the test period, rebalanced monthly, remainder in cash. This way merely taking less risk cannot pass the gate
   - Criterion: Calmar ratio (CAGR / maximum drawdown) of the strategy minus that of the static mix > 0, one-sided 95 %, paired stationary bootstrap (S6) over the same time blocks
   - Note: The average invested share is calculated from the entire test period. This is permissible for an evaluation after the test, because the benchmark does not trade
- ENTSCHEIDUNG

**G8 Benchmarks.** The **first** benchmark in the YAML is the gate benchmark; further ones are shown for information. Exception: for S2 and S3 both benchmarks must be passed (as in PE10).

| Module | Gate benchmark |
|---|---|
| Long-term | L1 with the same equity share (equity share of the strategy = average of its equity share over the test period); for L2 and L4 the risk gate from G7 |
| Swing multi-asset (S1) | The same universe, always long, with the same inverse volatility weights, rebalanced monthly |
| Swing equities (S2, S3) | Cap-weighted **and** equal-weighted universe (PE2), same rebalancing dates and costs |
| Intraday (I1) | "Always long in the last half hour" on the same instrument |

**G9 Counting of trials.**
- A **trial** is a unique configuration (hash of the YAML file including data and cost version). Repeated runs of the same configuration do not count again
- **One common N across all families that can generate signals** (long-term, swing, intraday, options). The control group has its own N, because it never generates signals
- The selection of these strategies from the literature is itself a selection that cannot be counted cleanly; gate 3 (t ≥ 3) and gate 7 serve as compensation
- ENTSCHEIDUNG

---

## 3. YAML schema of the strategy library

```yaml
id: S1
name: "Trend following TSMOM 1/3/12, long/flat"
modul: swing                     # langfrist | swing | intraday | optionen | kontrolle
rolle: kern                      # kern | kandidat | kontrolle | nicht_umsetzbar
evidenz: B                       # or {drawdown: B, rendite: C}
quellen: [MOP2012, HOP2017]
stichprobenende: 2009-12         # end of the source sample (G6)
freischaltung: lernstufe_3
universum: {typ: liste, elemente: [GOLD_ETC, SILBER_ETC, ROHSTOFFE_BREIT]}   # or {typ: regel, regel: PE2}
daten: [tagesschluss_total_return, zins_eur]
kalender: XETRA
bewertung: {frequenz: monatlich, zeitpunkt: letzter_handelstag_schluss}
ausfuehrung: naechste_eroeffnung # C4, E1
aufwaermphase: {handelstage: 600}
signal: tsmom_kombiniert         # function in the calculation core
parameter: {}                    # fixed from the source
bindungen: {regel: hoehere_marktkapitalisierung}
varianten: []                    # only from the source or peer-reviewed follow-up literature (G1)
kosten_profil: etf_etc
benchmark: [gate_benchmark, info_benchmark]
gates: standard                  # or risiko_gate (G7 point 8)
abweichungen: []                 # list of the explained deviations from the source
phase5_variante: null
```

---

## 4. Long-term module

### L1 Passive world portfolio with rebalancing (core, benchmark)

**Evidence A.** Among 66,465 US households (1991–1996), the most active fifth achieved 11.4 % per year net, the market 17.9 %, the least active fifth 18.5 % (Barber & Odean, 2000). In Taiwan, retail investors lost 3.8 percentage points per year through trading (Barber et al., 2009).

**Rule:**
- Building blocks: world equities (UCITS ETF on a broad world index) and EUR government bonds (UCITS ETF, maturity mix)
- Target weights according to risk profile, default **70 / 30**, adjustable in steps of 10
- Monthly check on the last trading day; if a building block deviates from the target by more than 5 percentage points, the portfolio is rebalanced **to the target weights**; independently of this, annually on the last trading day of the year
- Savings plan (simulator and live operation only): contributions go first into the underweight building block. Backtests calculate time-weighted, without cash flows
- Rebalancing parameters: **ENTSCHEIDUNG** (no peer-reviewed evidence found for an optimal frequency or threshold)

```yaml
id: L1
name: "Passive world portfolio with rebalancing"
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
gates: keine                      # is the benchmark
abweichungen: ["Rebalancing rule is a self-defined specification, not a source rule"]
```

### L2 Faber trend filter, GTAA 5 (core)

**Evidence B for lower drawdown, C for higher return.**
- Faber (2007), 2013 update: 1973–2012 buy-and-hold 9.92 % return, 10.28 % volatility, Sharpe 0.44, maximum drawdown −46.00 %; with trend filter 10.48 %, 6.99 %, 0.73, −9.54 %. After the original sample (2006–2012): 3.94 % / 0.16 / −46.00 % versus 6.01 % / 0.61 / −9.42 %. Robustness across 3/6/9/12-month average: Sharpe 0.60/0.72/0.77/0.73
- Zakamulin (2014): measured with realistic costs and out-of-sample tests, trend-filter performance is considerably weaker; earlier backtests without both "heavily overstated" it. Clare et al. (2016): trend following across several asset classes better than buy-and-hold on a risk-adjusted basis

**Rule:**
- Five asset classes at 20 % each: US equities, developed-market equities ex USA, government bonds, broad commodities, global real estate equities
- For each class independently on the last trading day of the month: month-end price (total return) > average of the last 10 month-end prices including the current one → invested; < → cash; tie → previous state; **initial state cash** until the first unambiguous signal occurs
- Execution at the next open

**Deviations from the source:** UCITS products in EUR instead of US indices in USD, EUR instead of US government bonds, signal on the EUR price series (exchange rates feed in), execution at the next open instead of at the closing price, costs taken into account, cash with EUR interest rate instead of T-bills.

**Known weaknesses:** false signals in V-shaped markets; lags behind in strong bull markets (2006–2012 better in only 3 of 7 years); in Germany every exit realises Abgeltungsteuer (flat withholding tax) (not in the backtest, only in the display according to C8).

```yaml
id: L2
name: "Faber trend filter GTAA 5"
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
varianten:                        # Faber 2013, Fig. 15
  - {name: sma_3, sma_monate: 3}
  - {name: sma_6, sma_monate: 6}
  - {name: sma_9, sma_monate: 9}
  - {name: sma_12, sma_monate: 12}
kosten_profil: etf
benchmark: [risiko_gate_statische_mischung, buy_and_hold_gleiche_klassen, L1]
gates: risiko_gate
abweichungen: [ucits_eur, anleihen_eur, naechste_eroeffnung, kosten, cash_eur]
```

### L3 Asset-class rotation by momentum (candidate)

**Evidence C.** The source (Asness, Moskowitz & Pedersen, 2013, Table I) shows momentum **within** asset classes: country indices 8.7 % per year (t = 4.14, Sharpe 0.73), commodities 12.4 % (t = 3.29), bonds 0.4 % (t = 0.35, no effect); across all classes including individual stocks 5.0 % (t = 4.18, Sharpe 0.67). L3, by contrast, compares different asset classes **with each other** (equities vs bonds vs gold). This is a different strategy, for which the source applies only to a limited extent; hence grade C.

**Rule:**
- Universe: 10 asset classes: equities USA, Europe, Japan, Pacific ex Japan, emerging markets; EUR government bonds, EUR corporate bonds; gold; broad commodities; global real estate equities
- Signal MOM_2-12 = cumulative total-return return from month-end t−12 to t−1 (last month skipped)
- Only classes with at least 13 months of history are considered; the ⌈n/3⌉ classes with the highest signal are held, equally weighted. Ties: the class with the lower 12-month volatility first
- Evaluation on the last trading day of the month, execution at the next open

**Variants (from the source):** without skipping the last month (the authors report stronger results without skipping for non-equities). The absolute filter according to Antonacci ("Dual Momentum") is **not peer-reviewed** and is therefore not a variant under G1; it is only explained in the learning module.

```yaml
id: L3
name: "Asset-class rotation by momentum"
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

### L4 Volatility-managed equity share (candidate)

**Evidence C (mixed).**
- Moreira & Muir (2017), market portfolio 1926–2015: alpha 4.86 % per year; with 10 basis points of costs 3.98 %; **without leverage (weight ≤ 1): alpha 2.12 %, break-even costs 110 basis points, Sharpe 0.52 versus 0.42 for the market** (confirmed in the JF version)
- Cederburg et al. (2020): across 103 strategies, managed portfolios do not systematically beat the unmanaged ones; real-time versions mostly worse
- Barroso & Detzel (2021): after costs only the management of the market portfolio remains robust, and only when investor sentiment is high

**Rule:**
- Share of the world equity ETF w_t = min(1; c_t / σ̂²_t), remainder in cash; no leverage
- σ̂²_t = sum of the squared deviations of the simple daily returns from the monthly mean over the trading days of month t
- c_t: chosen so that the **uncapped** managed series has the same volatility as the unmanaged market on all data up to month-end t (expanding window). The source determines c over the full period, which contains look-ahead; this is exactly what Cederburg et al. criticise
- Warm-up phase: 120 months of data before the first signal (stability of c_t)
- Evaluation on the last trading day, execution at the next open; the weight for month t+1 uses only data up to t (no look-ahead)

**Deviations:** world equities in EUR instead of US market in USD; cash with EUR interest rate instead of T-bills; c in real time instead of over the full period; cap at 1.

```yaml
id: L4
name: "Volatility-managed equity share"
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

### Overlay variants for the "Anlegen" (Invest) core module (v1.2)

Since plan v9, the long-term module has been part of the "Anlegen" (Invest) core module (`20260925_anlage-spezifikation_en.md`). L1 is the base portfolio there. In addition, there are two **own, registered variants** that only temporarily reduce the weight of the world equity building block K1. **Name clash:** K1 here means building block K1 from anlage spec A4.1, not control rule K1 from section 8; in code, building blocks are `block_K1`, `block_K2`, control rules `control_K1` to `control_K11`. They count as separate trials under G9 and are not equated with L2 or L4 respectively, because universe and weighting are different.

| ID | Rule | Gate |
|---|---|---|
| OV-L2 | Month-end: total-return price of K1 above the average of the last 10 month-end prices → w(K1) as planned; otherwise w(K1) × 0.5, remainder into the €STR money market ETF; execution at the next open | Risk gate G7 point 8 (Calmar ratio against a static mix with the same average invested share), **before and after German tax** with the same metric (investment specification A8.11) |
| OV-L4 | w(K1) = planned weight × max(0.5; min(1; c_t / σ̂²_t)), c_t and σ̂²_t as in L4 | as OV-L2 |

- End of sample as for L2 or L4 respectively; variants of the source (Faber: SMA 3/6/9/12) only as a robustness report (G7 point 7)
- **Taxes:** For these overlays and for strategies held as satellite S-Taktik in the core module (L3, S1), the after-tax gate applies in addition; the other strategies of the catalogue continue to show taxes only in the display (C8)

---

## 5. Swing module

### S1 Trend following, time-series momentum 1/3/12, long/flat (core)

**Evidence B.**
- Moskowitz, Ooi & Pedersen (2012): 58 futures, signal = sign of the 12-month excess return; alpha 1.58 % per month (t = 7.99); out-of-sample 1966–1985 Sharpe 1.1
- Hurst, Ooi & Pedersen (2017): 67 markets 1880–2016, combination of 1-, 3- and 12-month signals: 11.0 % per year excess return after estimated costs (before fees); Sharpe after costs and hypothetical fees 0.76, **2010–2016 only 0.41**
- Criticism: Huang et al. (2020) find little evidence in individual tests per asset; Kim, Tse & Wald (2016) attribute the alpha mainly to volatility scaling

**Rule:**
- Universe (7): gold ETC, silver ETC, broad commodities, equities USA, equities Europe, equities emerging markets, EUR government bonds
- Excess return per asset and horizon k ∈ {1, 3, 12} months: total return minus cumulative EUR interest (G5) over the same period
- s_k = +1 if excess return > 0, otherwise −1; s = (s_1 + s_3 + s_12) / 3; long/flat: s⁺ = max(s; 0) ∈ {0; ⅓; 1}
- Weight w_i = s⁺_i · (1/σ̂_i) / Σ_j (1/σ̂_j), sum over **all** 7 assets, σ̂ according to I7 (EWMA, centre of mass 60 days, annualised with 252). If all assets are fully long, the portfolio is 100 % invested; the share of flat assets is held in cash
- Evaluation on the last trading day, execution at the next open; warm-up phase 600 trading days (10 × centre of mass, recursive filter)

**Deviations:** The sources trade futures long and short with leverage across dozens of markets and scale the portfolio to 10 % volatility. Without leverage this target cannot be reached (with all 7 assets long, volatility would be about 5–8 %); the app therefore uses inverse volatility weights without a portfolio target. Only 7 UCITS products instead of broad diversification. The expected effect is significantly smaller than published.

**Phase 5 variant:** futures or CFDs with short side (s instead of s⁺) and a portfolio volatility target of 10 % under R4, only after learning stage 5.

```yaml
id: S1
name: "Trend following TSMOM 1/3/12, long/flat"
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
  - {name: nur_12m_signal_mop, lookbacks_monate: [12]}   # signal according to MOP, weighting as above
kosten_profil: etf_etc
benchmark: [immer_long_inverse_vol_gleiches_universum]
gates: standard
abweichungen: [long_flat_statt_long_short, kein_hebel_kein_vol_ziel, sieben_ucits_statt_futures, zins_eur]
phase5_variante: futures_long_short_vol_ziel_10
```

### S2 Equity momentum 12-1, long-only, USA (candidate)

**Evidence C** (the source is strong, but the long-only implementation on an equal-weighted top-500 universe deviates significantly).
- Jegadeesh & Titman (1993), NYSE/AMEX 1965–1989: 6/6 strategy 0.95 % per month (t = 3.07); 12/3 with a one-week gap 1.49 % (t = 4.28) (single-checked). Persistence in the 1990s (Jegadeesh & Titman, 2001)
- Crash risk: winners minus losers 1927–2013 skewness −4.70, April 2009 −45.52 % (Daniel & Moskowitz, 2016; single-checked). Crashes stem mainly from the loser side, which is not held in long-only
- After costs: 1.33 % gross, **0.68 % net per month (t = 2.45)**, cap-weighted across all stocks with NYSE breakpoints (Novy-Marx & Velikov, 2016). Most effective cost reduction there: buy only in the top decile, sell only after exit from the top quintile (10 %/20 % rule)

**Rule:**
- Universe: PE2, **initially USA only** (for Europe, free share counts and prices of delisted stocks are missing; a ranking by market capitalisation is not possible point-in-time)
- Signal: cumulative return from month-end t−12 to t−1
- Buy: top decile; hold until the stock leaves the top quintile (Novy-Marx & Velikov); equally weighted, reset to equal weight every month
- Ties at the decile or quintile boundary: higher market capitalisation first
- Evaluation on the last trading day, execution at the next open; stocks need 13 months of price history

**Deviations:** long-only instead of winners minus losers; equal-weighted top-500 universe instead of cap-weighted portfolios across all stocks; survivorship treatment according to PE2. Risk management according to Barroso & Santa-Clara (2015) is **not** adopted: their rule scales a long/short factor; for a long-only portfolio there is no source rule, and a self-made transfer would violate G1. This remains an open research question.

```yaml
id: S2
name: "Equity momentum 12-1 long-only USA"
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
benchmark: [universum_kapitalgewichtet, universum_gleichgewichtet]   # both must be passed
gates: standard
abweichungen: [long_only, gleichgewichtet_top500, keine_risikosteuerung, survivorship_pe2]
phase5_variante: long_short_cfd
```

### S3 52-week-high momentum, long-only, USA (candidate)

**Evidence C.** George & Hwang (2004), all CRSP stocks 1963–2001: measure = price / highest price of the last 12 months; top minus bottom 30 %, (6,6) overlap: 0.45 % per month (t = 2.00), excluding January 1.23 % (t = 7.06), in January −8.27 %; no long-term reversal. Internationally profitable in 18 of 20 markets, after costs no longer significant in most of them (Liu, Liu & Ma, 2011).

**Rule:**
- Universe: PE2, initially USA only (as S2)
- Measure M_i,t = closing price at month-end t / highest closing price of the 252 trading days up to and including month-end t (split-adjusted; the source uses prices, not total return)
- One cohort each month: top 30 % by M, equally weighted, held for 6 months; the portfolio is the average of the 6 running cohorts
- Ties at the 30 % boundary: higher market capitalisation first; stocks need 252 trading days of history
- Execution at the next open

```yaml
id: S3
name: "52-week-high momentum long-only USA"
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

### Not included in the swing module
- **Commodity carry** (Koijen et al., 2018; Sharpe 0.62–0.67): needs historical prices of individual futures contracts, for which there is no complete free source
- **Gold timing via real interest rates or inflation:** Erb & Harvey (2013) show that gold is an unreliable inflation hedge over practical horizons; the correlation with real US yields (−0.82, 1997–2012) does not establish a causal relationship. Gold is included in S1 and L3; real interest rates appear only as context in market intelligence

---

## 6. Intraday module

**Up front in the learning module:**
- Of 1,551 Brazilians who day-traded index futures on more than 300 days, 97 % lost money after fees; 1.1 % earned more than the minimum wage (Chague et al., 2020; single-checked). In Taiwan, fewer than 1 % of day traders were able to earn profits reliably after fees (Barber et al., 2014)
- Anyone who is flat in the evening forgoes the overnight portion of the equity premium: US market 1993–2013 on average 0.55 % per month overnight and 0.38 % during the day; for the largest stocks practically the entire premium accrued overnight (Lou, Polk & Skouras, 2019)

### I1 Intraday momentum in the last half hour (candidate)

**Evidence C.**
- Gao, Han, Li & Zhou (2018), SPY 1993–2013: the return from the previous day's close to 10:00 ET predicts the last half hour (R² 1.6 %); rule with long on a positive and short on a negative morning return: 6.67 % per year, Sharpe 1.08, hit rate 54.4 %; after the spread, from July 2001, 4.46 % per year
- Baltussen et al. (2021), 17 equity index futures as an equally weighted long/short portfolio 1974–2020: the stronger signal is the return from the previous day's close to 30 minutes before the close; 6.86 % per year, Sharpe 1.73, gross. **A single market long/flat will deliver considerably less**
- Rosa (2022): the predictability disappears in the out-of-sample period and depends on the market regime. Internationally mixed: present in China and Japan, weak in Korea, absent in Hong Kong and Singapore (Limkriangkrai, Chai & Zheng, 2023)

**Rule (Baltussen variant):**
- Data: own recording in **1-minute bars** from Phase 1
- Test market 1: DAX UCITS ETF on Xetra. Signal r_ROD = return from the previous day's close to 17:00 CET. If r_ROD > 0, buy in the first 1-minute bar after 17:00 (E1), sell via a closing-price order in the closing auction (E12b); otherwise flat
- Test market 2: S&P 500 UCITS ETF on a trading venue with evening trading. Signal and exit times follow **NYSE time** (signal 15:30 ET, exit at the price at 16:00 ET), not the close of trading on the German venue; in the weeks with differing daylight saving time this shifts in CET. Liquidity and spreads at this time UNVERIFIZIERT; check before the test
- Costs: spread and commission on entry, commission and slippage on exit

**Realistic expectation:** With a Sharpe ratio of 1.08 as in Gao et al., MinTRL (95 %) requires about 2.3 years of data; at 0.5 about 11 years. **I1 can pass the gates at the earliest after about 3 years of own recording**, probably later or never. Until then I1 runs only as an observation in the "Evidence" area.

```yaml
id: I1
name: "Intraday momentum last half hour"
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

## 7. Options module (Phase 7, locked until learning stage 6)

Each contract is additionally assessed under O10 of the specification (tradable edge, maximum loss ≤ 2 % of capital under R4, stress tests). The rules here determine which structures are examined at all. All strategies have a **finite maximum loss known in advance**.

| ID | Strategy | Evidence | Rule (short version) |
|---|---|---|---|
| O1 | Put credit spread on an index | C | Monthly, sell a put near the money and buy a lower put (European index, Eurex); strike distance such that the maximum loss is ≤ 2 % of capital. The basis is the volatility premium in index options (Carr & Wu, 2009; Bakshi & Kapadia, 2003; not re-checked in this phase). An uncovered, "cash-secured" put is excluded: with a point value of 5 €, one DAX contract corresponds to around 120,000 € notional value, which violates R4 |
| O2 | Covered call on a held index ETF | C | Monthly, a call slightly out of the money (delta ≈ 0.30) on the position held; return mostly equity beta, upside potential capped (Israelov & Nielsen, 2015) |
| O3 | Bull call spread as implementation of a long signal | C | Only with an active long signal from S1 or L2, term 30–60 days, maximum loss ≤ 2 %. Bear put spreads only with short signals of the Phase 5 variants |
| O4 | Protective put as insurance | C (negative as a return) | Only on request, as a priced hedge of a position; the app shows the expected costs per year (Israelov, 2019) |

**In the simulator**, for every short option the full obligation (strike × contract size minus the purchased hedge) is carried as tied-up capital, not just the margin.

The precise formalisation (strike selection, roll rules, YAML) takes place before Phase 7.

---

## 8. Control group

Tested on the instruments and periods of the respective source (G3), with the same costs and gates; own N (G9). Expectation from the literature: no rule passes.

**Finding:** The rules of Brock, Lakonishok & LeBaron (1992) were highly significant before costs in the Dow Jones 1897–1986. Sullivan, Timmermann & White (1999) examined 7,846 rules with a correction for data snooping: out-of-sample 1987–1996 the best Brock rule was no longer significant (White p = 0.154), nor was the best rule of the entire universe (p = 0.341) (single-checked). Bajgrowicz & Scaillet (2012): even in-sample, the performance is entirely eaten up by low transaction costs.

| ID | Rule | Exact parameters | Source and finding | Evidence |
|---|---|---|---|---|
| K1 | Moving averages (VMA) | Price or short versus long average: (1,50), (1,150), (5,150), (1,200), (2,200), band 0 % and 1 %; long as long as short > long × (1 + band); otherwise cash. Long/flat adaptation of the source's buy-minus-sell measurement (explained) | Brock et al. (1992); Sullivan et al. (1999) | D |
| K2 | Golden cross | Long from SMA(50) crossing above SMA(200), cash from crossing downwards | Part of the Sullivan grid; on ETFs weaker than buy-and-hold (Huang & Huang, 2020) | D |
| K3 | Trading range breakout | Buy when the closing price exceeds the high of the last 50, 150 or 200 days by the band (0 %/1 %); hold for 10 days | Brock et al. (1992) | D |
| K4 | RSI(14) 30/70 | Buy when the RSI falls below 30 and rises back above 30; sell when it rises above 70 and falls back below 70; hold for at most 10 days (as in the source, following Brock et al.). Long/flat adaptation of the buy-minus-sell measurement (explained) | Chong, Ng & Liew (2014): buy-minus-sell difference in the DAX −0.914 %, negative in several of the 5 markets | D |
| K5 | Bollinger bands | Buy on a closing price below the lower band (20; 2), sell on a closing price above the middle band | Lento et al. (2007): after costs consistently worse than buy-and-hold; parameters of the study UNVERIFIZIERT, rule here ENTSCHEIDUNG | D |
| K6 | Candlestick patterns | Patterns and trend definition (10-day EMA) following Marshall, Young & Rose (2006); entry at the next open, hold for 10 days; take the number and definition of the patterns from the appendix before implementation | "No value" for investors | D |
| K7 | Short-term reversal (cost example) | Weekly: buy the bottom decile of the previous week's return in universe PE2 (USA), hold for one week; variant with a holding buffer (hold until exit from the lower half, following de Groot et al.) | Novy-Marx & Velikov (2016): net −1.28 % per month; de Groot et al. (2012): positive only with institutional costs | D |
| K8 | Post-earnings drift (decay example) | SUE = (EPS_q − EPS_{q−4}) / standard deviation of this difference over the 8 preceding quarters; diluted EPS from EDGAR; **event time = acceptance time of the 10-Q or 10-K filing** (the figures from the earlier 8-K press release are not machine-readable in EDGAR); **Q1–Q3 only** (Q4 EPS cannot be cleanly derived from the annual minus the 9-month value); buy when SUE is above the 90th percentile of the SUE distribution **of the preceding quarter**; hold for 60 trading days | Bernard & Thomas (1989); Martineau (2022): disappeared for large stocks since 2006; Novy-Marx & Velikov: net 0.26 % (t = 1.60). The late event time additionally weakens the rule compared with the source (explained) | D |
| K9 | Opening range breakout | Following Zarattini & Aziz (2023) on QQQ (source instrument): direction of the first 5-minute bar from 09:30 ET, entry at the open of the second bar, no position on a doji, stop at the extreme of the first bar, target 10R, otherwise exit at the close; 1 % risk per trade; **without leverage** (source up to 4x) | Not peer-reviewed; authors with a commercial interest; basic version across all stocks Sharpe 0.48 (Zarattini, Barbon & Aziz, 2024) | D |
| K10 | "Noise Area" | Following Zarattini, Aziz & Barbon (2024) on SPY: σ per time of day = mean over the last 14 days of \|price(time of day) / open − 1\|; upper band = max(open, previous close) × (1 + σ), lower band = min(open, previous close) × (1 − σ); decisions only on the hour and half hour; long above the upper band, short below the lower band (long/flat in the app); stop = max(upper band, VWAP); close at 16:00; **base size 100 % of capital without dynamic leverage** | Not peer-reviewed; authors with a commercial interest | D |
| K11 | Fibonacci and Elliott waves | Cannot be defined as an unambiguous rule; **not tested**, only explained in the learning module | No peer-reviewed evidence of profitability found | D |

**Deliberately not included:** head-and-shoulders and other chart formations. Detection requires elaborate smoothing methods (Lo, Mamaysky & Wang, 2000, moreover do not test profitability); for stocks no independent profit was found (Savin, Weller & Zvingelis, 2007).

---

## 9. Reproduction targets and look-ahead traps per strategy

Exact reproduction is not possible with free data (different instruments, periods, currencies). The goal is to match the **direction and order of magnitude** of the source in the overlapping period. If the result deviates strongly, the engine is checked first.

| ID | Reproduction target (qualitative) | Look-ahead traps |
|---|---|---|
| L1 | None (benchmark); rebalancing turnover and costs plausible | Rebalancing with prices of the valuation day, execution only on the following day |
| L2 | Considerably lower volatility and maximum drawdown than buy-and-hold of the same classes, with similar or somewhat lower return | Month-end closing prices must be final; total-return adjustment only with distributions known by then (calculation-core specification K4) |
| L3 | Positive advantage, but considerably smaller than in the source; result depends on the share of equity classes | Classes without 13 months of history must not enter the ranking via retroactively extended proxies if the proxy was not known at the time |
| L4 | Lower drawdown than the unmanaged market; Sharpe advantage smaller than in the source (real-time c) | c_t only up to month-end t; variance of month t determines the weight from the open of t+1 |
| S1 | Positive but small active return versus "always long"; main benefit in bear markets (2008, 2022) | σ̂ only from daily data up to t; interest rate with publication lag (G5) |
| S2 | Top decile beats the equally weighted universe gross; questionable after costs; slumps in momentum crashes (2009) | Universe and market capitalisation point-in-time (PE2); delisted stocks with delisting return |
| S3 | Small positive effect, January weak | High including the valuation day is permissible (closing price is final); split adjustment only with known splits |
| I1 | Hit rate just above 50 %, active return after costs close to zero | Entry at the earliest one minute after the signal; closing-price order before the order cut-off |
| K1–K10 | No significant active return after costs in the period after 1987 or after the source sample | K8: event time = 10-Q/10-K acceptance, percentile thresholds from the preceding quarter |

---

## 10. Order of implementation

| Phase | Strategies |
|---|---|
| 2 (engine validation) | L1, L2 as first tests; K1, K2 as negative control |
| 3 (long-term) | L1–L4 |
| 3b (simulator) | L1 and L2 as signal suggestions in the practice depot |
| 5 (swing) | S1, then S2, S3; K3–K8 |
| 5b (intraday) | I1, K9, K10, with own recording from Phase 1 |
| 7 (options) | O1–O4 |

---

## 11. Open points

| Point | When to clarify |
|---|---|
| Specific UCITS products per asset class (costs, replication, trading venue) and data proxies | Phase 1 |
| Withholding tax rate of Irish UCITS funds on US dividends (G4) | Phase 1 |
| Availability of the Frankfurt overnight money rate before 1999 as a free time series (G5) | Phase 1 |
| Liquidity of an S&P 500 UCITS ETF in evening trading (I1, test market 2) | Before Phase 5b |
| Candlestick pattern definitions (K6) | Before Phase 5 |
| Risk management for long-only momentum (S2) | Open research question |
| Formalisation of O1–O4 | Before Phase 7 |

---

## Changelog

**20260925, no rule change:** this English text becomes binding and the German original moves to `archive/`. Editorial: Abgeltungsteuer kept as a German term; labels shown in the app in English; the marker "single-checked" used in all five places; the I1 YAML name translated like the other names.

**v1.2 (20260925):** Overlay variants OV-L2 and OV-L4 added for the "Anlegen" (Invest) core module; after-tax gate for overlays and the satellite S-Taktik. Found and corrected during translation: K10 short **below** the lower band; Zakamulin finding stated the right way round; K4 reference at L2 pointed to the calculation-core specification; name clash building block K1 / control rule K1 resolved.

**v1.1 (20260925)** after independent review (4 critical, 9 serious, many minor findings), all incorporated:
- Critical: cash-secured index put (O1) violated the 2 % loss limit → replaced by a put credit spread; in the simulator the full obligation is tied up as capital
- Critical: post-earnings drift (K8) had double look-ahead → event time of the 10-Q/10-K filing, percentile thresholds from the preceding quarter, Q1–Q3 only
- Critical: the PBO gate would have systematically blocked the core strategies → PBO now only when the app selects a variant
- Critical: the drawdown gate would have let mere less-risk pass as a strategy → comparison with a static mix of the same investment ratio via the Calmar ratio
- Serious: gates on active return instead of absolute Sharpe; testing only after the source sample; 60 % haircut on the active return; one common N across all signal-capable families and t ≥ 3; L3 declared as a separate, modified strategy (grade C); S1 without an unattainable volatility target; S2 to grade C, without its own risk management, initially USA only; I1 with 1-minute data, closing-price order and an honest time estimate; proxy rules for currency, withholding tax and calendar; K9/K10 on the source instruments with complete rules
- Minor: citation of Rosa (2022) corrected and international findings assigned to the correct source; Chong et al. described correctly; variants without a source basis removed (G1); YAML standardised; starting states, warm-up phases, binding rules and interest-rate series before 2019 specified; reproduction targets and look-ahead traps added for all strategies

---

## Sources

- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). Value and momentum everywhere. *Journal of Finance, 68*(3), 929–985.
- Bajgrowicz, P., & Scaillet, O. (2012). Technical trading revisited: False discoveries, persistence tests, and transaction costs. *Journal of Financial Economics, 106*(3), 473–491.
- Baltussen, G., Da, Z., Lammers, S., & Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics, 142*(1), 377–403.
- Barber, B. M., Lee, Y.-T., Liu, Y.-J., & Odean, T. (2009). Just how much do individual investors lose by trading? *Review of Financial Studies, 22*(2), 609–632.
- Barber, B. M., Lee, Y.-T., Liu, Y.-J., & Odean, T. (2014). The cross-section of speculator skill: Evidence from day trading. *Journal of Financial Markets, 18*, 1–24.
- Barber, B. M., & Odean, T. (2000). Trading is hazardous to your wealth. *Journal of Finance, 55*(2), 773–806.
- Barroso, P., & Detzel, A. (2021). Do limits to arbitrage explain the benefits of volatility-managed portfolios? *Journal of Financial Economics, 140*(3), 744–767.
- Barroso, P., & Santa-Clara, P. (2015). Momentum has its moments. *Journal of Financial Economics, 116*(1), 111–120.
- Bernard, V. L., & Thomas, J. K. (1989). Post-earnings-announcement drift: Delayed price response or risk premium? *Journal of Accounting Research, 27*(Suppl.), 1–36. (Not consulted.)
- Brock, W., Lakonishok, J., & LeBaron, B. (1992). Simple technical trading rules and the stochastic properties of stock returns. *Journal of Finance, 47*(5), 1731–1764.
- Cederburg, S., O'Doherty, M. S., Wang, F., & Yan, X. (2020). On the performance of volatility-managed portfolios. *Journal of Financial Economics, 138*(1), 95–117.
- Chague, F., De-Losso, R., & Giovannetti, B. (2020). *Day trading for a living?* [Working paper]. SSRN 3423101.
- Chong, T. T.-L., Ng, W.-K., & Liew, V. K.-S. (2014). Revisiting the performance of MACD and RSI oscillators. *Journal of Risk and Financial Management, 7*(1), 1–12.
- Clare, A., Seaton, J., Smith, P. N., & Thomas, S. (2016). The trend is our friend: Risk parity, momentum and trend following in global asset allocation. *Journal of Behavioral and Experimental Finance, 9*, 63–80.
- Daniel, K., & Moskowitz, T. J. (2016). Momentum crashes. *Journal of Financial Economics, 122*(2), 221–247.
- de Groot, W., Huij, J., & Zhou, W. (2012). Another look at trading costs and short-term reversal profits. *Journal of Banking & Finance, 36*(2), 371–382.
- Erb, C. B., & Harvey, C. R. (2013). The golden dilemma. *Financial Analysts Journal, 69*(4), 10–42.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79. (Read: 2013 update.)
- Gao, L., Han, Y., Li, S. Z., & Zhou, G. (2018). Market intraday momentum. *Journal of Financial Economics, 129*(2), 394–414.
- George, T. J., & Hwang, C.-Y. (2004). The 52-week high and momentum investing. *Journal of Finance, 59*(5), 2145–2176.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). … and the cross-section of expected returns. *Review of Financial Studies, 29*(1), 5–68. (Not consulted.)
- Huang, D., Li, J., Wang, L., & Zhou, G. (2020). Time series momentum: Is it there? *Journal of Financial Economics, 135*(3), 774–794.
- Huang, J.-Z., & Huang, Z. (2020). Testing moving average trading strategies on ETFs. *Journal of Empirical Finance, 57*, 16–32.
- Hurst, B., Ooi, Y. H., & Pedersen, L. H. (2017). A century of evidence on trend-following investing. *Journal of Portfolio Management, 44*(1), 15–29.
- Israelov, R. (2019). Pathetic protection: The elusive benefits of protective puts. *Journal of Alternative Investments, 21*(3), 6–. (End page not checked.)
- Israelov, R., & Nielsen, L. N. (2015). Covered calls uncovered. *Financial Analysts Journal, 71*(6), 44–57.
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers: Implications for stock market efficiency. *Journal of Finance, 48*(1), 65–91.
- Jegadeesh, N., & Titman, S. (2001). Profitability of momentum strategies: An evaluation of alternative explanations. *Journal of Finance, 56*(2), 699–720.
- Kim, A. Y., Tse, Y., & Wald, J. K. (2016). Time series momentum and volatility scaling. *Journal of Financial Markets, 30*, 103–124.
- Koijen, R. S. J., Moskowitz, T. J., Pedersen, L. H., & Vrugt, E. B. (2018). Carry. *Journal of Financial Economics, 127*(2), 197–225.
- Lento, C., Gradojevic, N., & Wright, C. S. (2007). Investment information content in Bollinger Bands? *Applied Financial Economics Letters, 3*(4), 263–267.
- Limkriangkrai, M., Chai, D., & Zheng, G. (2023). *Pacific-Basin Finance Journal, 80*, 102086. (Title not checked.)
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
- Not re-checked, cited only for O1: Bakshi, G., & Kapadia, N. (2003). *Review of Financial Studies, 16*(2); Carr, P., & Wu, L. (2009). *Review of Financial Studies, 22*(3).
