---
title: Trading Analysis App – Project Plan
date: 20260925
status: Draft v9 (replaces v8; basis: 20260925_anlage-spezifikation_en.md, 20260924_trading-app-qualitaetsstandards.md, 20260925_rechenkern-spezifikation-v1.4.md, 20260925_strategie-katalog_en.md (v1.2), 20260924_trading-app-research.md)
owner: Henri
language: en
binding: this English text (since 20260925)
supersedes: archive/20260925_trading-app-plan-v9.md (German original, no longer binding)
---

# Trading Analysis App – Project Plan v9

**Binding text.** This English document is the binding project plan. The German original is archived in `archive/20260925_trading-app-plan-v9.md` and no longer binding. German tax and legal terms are kept as proper nouns; everything the user sees in the app is English (20260925, no rule change).

## Changes compared with v8

- **New core module "Anlegen" (Invest)** (investment adviser for long-term and medium- to long-term investments), fully specified in `20260925_anlage-spezifikation_en.md`: profile and goals, order of finances, equity share per goal, building blocks, concrete ETF selection, savings plan and tax-optimised rebalancing, German tax engine, projection, monthly recommendation, investment policy statement, behavioural guardrails, retirement-provision notes
- The previous long-term module (L1–L4) becomes part of "Anlegen": L1 is the base portfolio, L2–L4 and S1 are optional overlays with an additional after-tax gate
- Information architecture: "Anlegen" is the first main area; the "Overview" page leads with the monthly recommendation
- Consistency cleaned up: architecture diagram updated to the v9 areas, unlocking of leverage (phase 5) and options (phase 7), area of the prediction engine (Trading)
- Roadmap: the first usable version (phases 1, 2, 3) is the investment adviser; trading, simulator, options and Prediction Engine follow **at unchanged depth**

## Changes from v7 to v8

- New: **Prediction Engine** for stocks (ranking with a calibrated probability of beating the median of the universe), section 4.16; full calculation rules in the specification v1.3, section 13
- Roadmap: new phase 8b; tech stack extended with LightGBM and scikit-learn

## Changes from v6 to v7

- New: **Simulator** with two modes, live practice depot on current prices and time travel through historical prices (section 4.15). Replaces the previous "paper portfolio from the signals"
- Calculation-core specification v1.2 extended with execution rules for orders (section 12 of the specification)
- Roadmap: new phase 3b

## Changes from v5 to v6

- No existing depot (brokerage account): the app starts in **signal mode** without a portfolio. Depot capture (manual, CSV, optionally IBKR) is present from the start and is used as soon as you have a depot
- Look: **own, matter-of-fact design**, not Henri Glass
- All open questions resolved

## Changes from v4 to v5

- Broker connection is **optional**: the app runs fully without a brokerage account, IBKR is a module that can be switched on
- New: **UI design** (section 4.14) with information architecture, design principles and a dedicated design phase before the first dashboard

## Changes from v3 to v4

- New: **quality standards** as a binding companion document (security, calculation core, look-ahead bias, intraday)
- New: **Phase 0b calculation-core specification**: all evaluation formulas are fixed with sources, conventions and reference values before programming
- New: **intraday** in addition to swing, with its own data recording from phase 1
- Security: review log per dependency, hash-pinned installation, IB Gateway in read-only mode
- Look-ahead bias: bitemporal data storage, point-in-time access as the only interface, automatic leakage tests on every build
- Removed: PMG/Factiva and the WMP connection; the block list remains as an optional, general function

## Changes from v2 to v3

- New: **learning module**. The tool explains every signal, guides you through a learning path and unlocks functions only after completed lessons (section 4.11)
- Budget set at **0 €**: delayed or end-of-day data, LLM local only, no paid options histories
- Capital is entered in the tool, not fixed in the plan
- Options: the module is built but stays locked until the options learning path has been completed
- Media sources in German and English

## Changes from v1 to v2

- New: **market intelligence module** (media, experts, insiders, filings, macro), designed as a context and risk module with small tilts, not as a recommendation generator
- New: **options module** with its own valuation logic
- Tech stack corrected: `pandas-ta` out (security concerns), TA-Lib, `bt`, `skfolio`, `edgartools`, `py_vollib`, `QuantLib` in
- Long-term universe fixed to **UCITS ETFs** (EU retail investors cannot buy US ETFs)
- Roadmap extended by two phases, open questions updated

## 1. Goal and scope

A private analysis tool with a clear core: **Every month it tells you what you should do with your money over the long term and the medium to long term, and why.** In addition there are evidence-based trading signals with hit rate, uncertainty and risk, and the app teaches you investing and trading. The connection to a brokerage account is optional. Modules on a shared engine, by priority:

| Module | Purpose | Cadence |
|---|---|---|
| **Anlegen (core)** | Investment adviser: profile and goals, equity share per goal, concrete ETFs, savings plan, tax-optimised rebalancing, projection, monthly recommendation, investment policy statement; base portfolio L1 plus optional overlays L2–L4, S1 (`20260925_anlage-spezifikation_en.md`) | Monthly and on events |
| Trading | Swing and intraday signals for gold/commodities, stocks, ETFs/ETCs, futures, CFDs | Swing: hourly to daily; intraday: minute bars |
| Market intelligence | Media, experts, insiders, filings, macro as context, warnings and small tilts | Daily/weekly |
| Options | Valuation of individual contracts and defined-risk strategies (locked until learning path completed) | On demand and daily |
| Learning | Explanation of every signal, learning path, quiz, trading journal, unlocking of functions, **simulator** (practice depot on real prices) | Ongoing |
| Prediction Engine | Stock ranking with a calibrated probability of performing better than the median of the large stocks over 1–3 months ("Trading" area, "Stock ranking" subpage) | Monthly |

Out of scope: crypto, passing on to third parties (would become relevant to BaFin), fully automated order execution. Execution is prepared but deactivated (section 4.10).

**Guiding principle:** The benchmark for every module is a low-cost, broadly diversified ETF. Whatever does not beat it after costs and on a risk-adjusted basis is not shown as a signal.

## 2. Decisions taken

| Item | Decision | Consequence |
|---|---|---|
| Products | As many tradable products as possible, incl. options | Instrument model with its own cost and risk profile per class; leveraged products (futures, CFDs) only from phase 5 with learning stage 5, options only from phase 7 with learning stage 6 |
| Broker | Optional: Interactive Brokers | Without a broker: free data sources, portfolio manually or via CSV import. With IBKR: depot sync, IBKR data, option chains, later optionally orders |
| Platform | Python + local Streamlit dashboard | Runs on your Mac, built with Claude Code |
| Execution | v1 signals only, orders as a later option | Execution adapter off via feature flag |
| Media/experts | Context + warnings + capped tilts | No primary buy/sell signals (state of the evidence, see research section 3) |
| LLM use | Summarising and classifying, no return forecasts | Protects against look-ahead bias and spurious precision |
| Trading time horizon | Swing and intraday | Swing can be fully validated with free data. Intraday records its own data from phase 1 and only produces signals after ≥ 12 months of its own history (quality standards section 4) |
| Budget | 0 € per month | Free data sources only; LLM local (FinBERT); options logic is validated forward instead of with purchased histories |
| Capital | Entered in the tool | The risk module calculates position sizes from it; futures and options are automatically hidden if capital is too small. Without an input the app shows risk in % instead of in euros |
| Depot | None yet; capture built in from the start | Signal mode without a portfolio: signals and recommendations for a watchlist, risk per signal based on the capital entered. As soon as a depot exists: manual input, CSV import or optionally IBKR sync; then target-vs-actual comparison, concentration risk and rebalancing suggestions are added |
| Look | Own, matter-of-fact design | No Henri Glass; calm, data-oriented design (section 4.14) |
| Options | Module built but locked | Unlocked only after the options learning path and quiz |
| Media sources | German and English | FinBERT is English; German texts need a German financial sentiment model or are only summarised, not scored |
| Block list | Optional, empty by default | You can exclude any securities you like; the tool shows nothing for these |
| Quality | Quality standards are binding | Security, calculation core and look-ahead protection are gates in every phase |


## 3. Broker and data

**Standard operation without a broker:** Prices from free sources (table below), portfolio via manual input or CSV import from any depot. All modules except depot sync and order execution work this way. Limitations: option chains then come from yfinance (unofficial, US options only, without Eurex), intraday recording only with delayed data.

**Optionally with a broker:** **Interactive Brokers** via `ib_async` (successor to `ib_insync`, BSD-2) with a locally running IB Gateway, initially in the paper account. Can be switched on in the settings; the broker adapter is an interchangeable module, so that other brokers with an official API can also be added later.

| Data type | Source | Cost |
|---|---|---|
| Prices live + historical | IBKR | Delayed data free; real-time subscriptions not needed for swing (check exact terms before opening the account) |
| Long histories for research | `yfinance` as a cached fallback | Free, rate-limited, private use only |
| Option chains, IV, Greeks | IBKR (`reqSecDefOptParams` + market data) | Delayed free; check before unlocking whether options market data can be used without a subscription |
| Historical option chains for backtests | – | With a 0 € budget this is dropped. The options logic is validated forward: log every valuation, evaluate after expiry |
| News | GDELT, Finnhub free tier, RSS feeds of press releases, central banks and supervisory authorities | Free |
| Insiders, 13F | SEC EDGAR via `edgartools`; German directors' dealings via the BaFin database or issuer notifications | Free |
| Macro | FRED (`fredapi`), ECB (`sdmx1`) | Free |

**Not used:** PMG and Factiva.

## 4. Architecture

```
┌──────────────────────────── Dashboard (Streamlit, localhost) ────────────────────────────┐
│ Overview │ Anlegen │ Trading │ Portfolio │ Market │ Options │ Learn │ Evidence             │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
┌──────────────┐   ┌────────────────────────┴───────────────────────┐   ┌──────────────────┐
│ Data layer   │──▶│ Investment & signal engine                     │──▶│ Risk module      │
│ IBKR         │   │ Anlegen │ Trading │ Option valuation           │   │ Sizing, limits,  │
│ yfinance     │   └───────▲────────────────────────▲───────────────┘   │ exposure, stress │
│ EDGAR, FRED  │           │ Tilts / warnings       │                   └────────┬─────────┘
│ News APIs    │   ┌───────┴────────────────┐  ┌────┴─────────────────┐   ┌───────┴─────────┐
└──────┬───────┘   │ Market intelligence    │  │ Strategy library     │   │ Execution       │
       │           │ Ingest → classification│  │ (YAML)               │   │ adapter (OFF)   │
       ▼           │ → Scorecard → Tilts    │  └────┬─────────────────┘   └─────────────────┘
┌──────────────┐   └───────┬────────────────┘  ┌────┴─────────────────────────┐
│ DuckDB       │◀──────────┴───────────────────│ Backtest & validation        │
│ (point-in-   │                               │ engine (walk-forward, DSR,   │
│  time)       │                               │ PBO, costs)                  │
└──────────────┘                               └──────────────────────────────┘
```

### 4.1 Data layer
Adapter pattern: every source implements the same interface so that sources remain interchangeable. All data is stored **point-in-time**, i.e. with the time at which it was available (publication time, not event time). This is the precondition for news and filing signals being testable without look-ahead.

### 4.2 Instrument model

| Class | Particulars |
|---|---|
| Stocks, UCITS ETFs, ETCs | Fees, spread, trading hours, currency |
| Futures | Multiplier, rolling, margin, expiry |
| CFDs | Leverage (ESMA limit for gold 1:20), overnight financing, spread |
| Options | Style (European/American), multiplier, expiry, exercise/assignment, margin, dividend dates |
| Mining stocks | Like stocks, plus gold price correlation |

### 4.3 Strategy library
Strategies as YAML configuration: entry, exit, stop, timeframe, permitted product classes, evidence source and evidence grade.

### 4.4 Backtest and validation engine
A strategy or a tilt only goes live when all checks have been passed:
- Realistic costs per product class (fees, spread, slippage, financing, roll costs)
- Walk-forward and Combinatorial Purged CV (`skfolio`)
- Deflated Sharpe Ratio and PBO, implemented in-house following Bailey & López de Prado
- No look-ahead: only data available point-in-time
- **Publication haircut:** for published signals the expected effect is reduced by ≥ 50 % (McLean & Pontiff, 2016)
- Benchmark: low-cost broad ETF, after costs and risk-adjusted

### 4.5 Core module Anlegen and trading module

**Anlegen (core)** is fully specified in `20260925_anlage-spezifikation_en.md`. Summary of the process:
1. **Profile and goals** following the structure of the ESMA suitability guidelines, with the loss question in euros instead of self-assessment
2. **Order of finances:** expensive debt, emergency fund, then investing
3. **Equity share per goal** = minimum of the horizon, capacity and tolerance limits
4. **Building blocks:** world equities at market weight plus a safety building block; satellites (gold, factors, individual stocks, tactics) together at most 20 % of the risk budget
5. **Concrete ETFs** via hard filters and a transparent scoring (tracking difference before TER), from a candidate list maintained in accordance with the rules
6. **Savings plan** with cash-flow rebalancing, annual review, tax-optimised sales, use of the Sparer-Pauschbetrag (saver's allowance)
7. **Tax engine** for Germany (Abgeltungsteuer (flat withholding tax), Günstigerprüfung (most-favourable-assessment test), NV-Bescheinigung (non-assessment certificate), Teilfreistellung (partial exemption), Vorabpauschale (advance lump sum), gold under § 23, Verlusttöpfe (loss pots))
8. **Projection** via block bootstrap from multi-country history, centred on conservative assumptions, in today's euros
9. **Monthly recommendation**, **investment policy statement (IPS)**, **behavioural guardrails**, **retirement-provision notes**

The base portfolio corresponds to strategy L1; L2–L4 and S1 are optional overlays that must additionally pass an after-tax gate and may only lower the equity share, never raise it.

**Trading** remains at full depth as described in the strategy catalogue (S1–S3, I1, control group) and in the calculation-core specification.

| | Trading | Anlegen |
|---|---|---|
| Strategy families | Time-series momentum, stock momentum, 52-week high, intraday momentum | Base portfolio L1; overlays L2 (trend filter), L3 (rotation), L4 (volatility), S1 (trend following) |
| Output | Direction, entry, stop, target, hit rate with confidence interval | Monthly recommendation with concrete purchases, savings plan allocation, rebalancing, tax effect, projection |

### 4.6 Market intelligence module (new)

**Pipeline:**
1. **Ingest** (scheduled via APScheduler): news (GDELT, Finnhub), SEC Form 4 and 13F, macro data, optionally selected research sources. Every entry is given a publication timestamp.
2. **Classification:** FinBERT locally for English sentiment; for German texts a local German-language financial model (selection to be checked in phase 4) or only a summary without a sentiment score. Summaries via a local open-weight LLM (free, runs on the Mac) or manually with Claude in the chat. A paid LLM API is not planned with a 0 € budget. Company names are anonymised before the sentiment scoring.
3. **Aggregation:** weekly news tone per security/asset, clusters of opportunistic insider purchases (non-routine purchases, method following Cohen et al., 2012), 13F positions of selected funds.
4. **Categorisation by evidence grade** (from research section 3):

| Category | Contents | Effect in the app |
|---|---|---|
| Tilt (small, capped) | Opportunistic insider purchases, weekly negative news tone | Max. ±10–20 % change in the position size of an existing signal, never a signal of its own (the cap is set in the backtest) |
| Watchlist | Selected 13F positions | Candidates for the strategy engine |
| Risk warning | Attention spikes in social media, TV/forum hype, extreme media pessimism, recycled commodity news | Notice "don't chase / reversal possible" |
| Context | Analyst consensus, strategist/guru statements, macro news | Display "What is being said", without influence on signals |
| Excluded as input | TV tips, newsletters, WallStreetBets, price targets | Not shown or only with a warning notice |

5. **Expert scorecard:** every logged expert statement with a clear direction (source, asset, direction, horizon, timestamp) is automatically evaluated against the outcome and a benchmark. After enough observations the app shows a hit rate with confidence interval per source. A source is only given weight if it passes the test live.
6. **Weekly briefing:** short summary per held asset and watchlist, every point with source and evidence grade.

**Security rule:** Texts from news and filings are data, not instructions. The LLM may not trigger any actions (protection against prompt injection via manipulated articles).

### 4.7 Options module (new)

**Model choice:** Black-Scholes-Merton (European), Black-76 (futures options), binomial tree/Bjerksund-Stensland (American), SVI fit for the smile. Implementation with `py_vollib` (IV, Greeks) and `QuantLib` (American options).

**Valuation logic per contract or strategy:**
1. Liquidity filter (spread/mid ≤ 10 %, open interest ≥ 500, remaining term ≥ 7 days)
2. Volatility forecast with HAR-RV, GARCH as a cross-check, earnings jump term
3. Volatility edge: IV (SVI) minus forecast, vega-weighted
4. Fair value with own forecast; tradable edge after bid/ask, fees and model-error buffer
5. Monte Carlo distribution: expected value after spread, probability of profit (risk-neutral and real-world side by side), CVaR 95 %
6. Maximum loss and stress tests (price ±5–30 %, IV ±, IV crush, historical replays), early-exercise check
7. Decision: Go / Warning / Block (details in research section 4.4)

**Starter set:** covered calls, cash-secured index puts, vertical spreads with defined risk, protective puts as insurance.

**Locked until further notice:** naked short calls, short straddles/strangles, 0DTE/weeklies, buying options before earnings, cheap OTM calls, uncovered short puts, ratio/backspreads, calendars, futures options, US ETF options.

**Underlyings:** SPX/XSP, Eurex indices (ODAX, OESX), liquid large caps.

**Validation:** Since historical option chains cost money, the logic is initially validated forward: every valuation is logged and checked against the outcome after expiry. Buying historical data is optional (budget, section 8).

### 4.8 How the percentages come about
Unchanged: hit rate with 95 % confidence interval and n, calibration status (reliability diagram, Brier score), expected value after costs. For options, additionally the separation of risk-neutral vs. real-world.

### 4.9 Risk module
- Position size from stop distance, max. 1 % capital risk per trade
- Options: maximum loss ≤ 2 % of the portfolio per position, stress loss must be bearable without a forced sale
- Leverage limit per class, stricter than the broker limit
- Total exposure and correlation check, incl. option deltas (e.g. gold ETC + gold future + mining stock + short put on mining stock = one concentration risk)
- Daily loss limit with signal stop

### 4.10 Execution adapter (prepared, deactivated)
Activation only after ≥ 3 months of successful paper trading, initially in the paper account, every order with your confirmation, hard limits and kill switch, credentials only in `.env`. Options additionally only within the starter set and IBKR permission levels 1–3.

### 4.11 Learning module (new)

The tool is meant to teach you trading and long-term investing. It is built so that learning and using interlock:

**1. Every signal explains itself.** Next to every signal there is a "Why?" panel: which rule triggered, the evidence behind it (study, evidence grade), the risk in euros at your capital and what the signal does *not* know. Technical terms are linked to a glossary.

**2. Learning path with unlocking.** Functions are only unlocked after the matching lesson and a short quiz:

| Stage | Content | Unlocks |
|---|---|---|
| 1: Foundations | Return and risk, order of finances (debt, emergency fund), diversification, costs and tracking difference, compound interest, savings plan, world portfolio with UCITS ETFs, taxes (Abgeltungsteuer, Sparer-Pauschbetrag, Teilfreistellung, Vorabpauschale, Anlage KAP), investment policy statement | Core module Anlegen (base portfolio, savings plan, projection) |
| 2: How to read evidence | Backtest vs. reality, overfitting, confidence intervals, publication effect, why gurus don't work, life-cycle vs. all-equity view, factors and individual stocks (Bessembinder) | Evidence and backtest view; overlays and satellites in the core module |
| 3: Swing trading | Trend following, momentum, mean reversion, position size, stops, expected value | Trading module (stocks, ETFs, ETCs) |
| 4: Market intelligence | How news is priced in, insider signals, recognising hype | Tilts and scorecard |
| 5: Leveraged products | Futures, CFDs, margin, obligation to make additional payments (Nachschusspflicht), financing costs | Futures and CFDs in the trading module |
| 6: Options | Payoffs, Greeks, implied volatility, volatility premium, starter set, taxes on derivatives transactions (Termingeschäfte) | Options module (starter set only) |

**3. Trading journal.** Every paper or real trade is given a short rationale in advance (signal, expectation, stop). The tool evaluates the journal and shows you typical behavioural errors with evidence from your own data: overtrading, taking profits too early and holding losses too long (disposition effect), deviating from signals.

**4. Weekly review.** What the signals said, what happened, what you learn from it. Plus a quiz question on the week's material (spaced repetition).

**5. Content created at no cost.** Lessons and quiz questions are written as static content, with sources, while building with Claude Code. No paid API is needed at runtime.

### 4.12 Block list (optional)

A self-maintained list of securities that the tool hides completely: no signals, no analyses, orders are blocked. Empty by default.

### 4.13 Quality standards

Security, calculation core and look-ahead protection are laid down in `20260924_trading-app-qualitaetsstandards.md` and apply to every module. Summary:
- **Security:** review log per dependency, allowlist, hash-pinned installation, read-only API until execution is approved
- **Calculation core:** specification before code; four levels of checks (reference values, two independent implementations, invariants, data checks); independent second review of every calculation module
- **Look-ahead:** bitemporal, append-only data storage; strategies see data only via `PointInTimeView(t)`; truncation, perturbation and delay tests on every build; sealed holdout

### 4.15 Simulator (new)

A practice depot with virtual money on real prices. It uses the same data layer, the same cost model and the same execution rules as the real tool, so that what is practised carries over to real trading.

**Two modes:**

| Mode | What happens | What for |
|---|---|---|
| **Live practice depot** | You trade on current prices (delayed by approx. 15 minutes when free); the depot continues in real time | Build a routine, trade along with the app's signals, practise swing and intraday |
| **Time travel** | You start at a date in the past and trade forward day by day (or bar by bar); the app shows only what was known up to that point in time | Practise years in hours, experience crashes and sideways phases, train long-term investing |

**Functions:**
- Order types: market, limit, stop, stop-limit, stop-loss and profit target at entry
- Several practice depots in parallel (e.g. "Swing", "Long-term savings plan", "Gold"), each with its own starting capital
- Dividends, splits, costs and a rough tax estimate are taken into account as in the real tool
- **Scenarios** for time travel: financial crisis 2008, COVID crash 2020, interest-rate turnaround 2022, sideways market, random starting point
- **Evaluation** after every session: return against the benchmark (buy-and-hold) and against what the app's signals would have done; plus the trading journal with your typical mistakes
- Options in the simulator only after learning stage 6, as in the real tool

**Rules against self-deception:**
1. **Blind mode for time travel (default):** security and date are hidden, prices normalised to 100. Anyone who knows it is March 2020 "practises" with knowledge of the recovery. Revealed at the end of the session
2. **No rewinding:** decisions are final; a session can only be restarted, and this is noted in the journal
3. **Realistic execution:** orders are executed at the earliest on the next bar, with spread, slippage and commission (specification section 12). In the live practice depot with delayed data, an order is executed at the price that actually applied at the time of the order, as soon as this price becomes visible, not at the stale displayed price
4. **Clear separation:** simulation mode is marked throughout the interface by a coloured band and the label "Simulation", so that you never confuse real and simulated depots. Sending orders to a broker from the simulator at a later stage is technically impossible
5. **No mixing with the evidence:** results from the simulator never feed into the evaluation of strategies (otherwise time travel, in which you have seen data, would contaminate the sealed holdout). The period of the sealed holdout is locked in time travel until it has been opened for strategy testing

**Effort:** The simulator uses the building blocks that are planned anyway (`PointInTimeView` for time travel, cost model, depot management). What is new is essentially the execution logic for order types, session control and the evaluation.

### 4.16 Prediction Engine (new)

**What it does:** Once a month it ranks the large, liquid stocks (USA: top 500; Europe: largest stocks) by their chance of performing better than the median of these stocks over 1 or 3 months. For each stock it shows rank, quintile, a calibrated probability with interval, a forecast interval for the return and the three most important reasons for the assessment. Alongside, clearly separated, it shows as context how often stocks have historically beaten the index.

**What it does not do:** price targets or price forecasts. Research shows a small but measurable advantage. Correctly calibrated probabilities therefore almost always lie between 45 and 55 %. The app shows this framing directly next to the ranking.

**How it becomes as accurate as possible** (details in the specification, section 13):
- Clean point-in-time data (EDGAR with filing time, publication embargo for features)
- Features from the literature rather than from our own backtest, rank-normalised per reference date
- Continuous, rank-based target variable; probabilities only via calibration on a later, strictly separated time block
- Equal-weighted ensemble (ridge + LightGBM with several seeds) instead of a single "optimised" model
- Expanding training, annual re-estimation, embargo, every variant counted for the overfitting tests
- Hard gates: the engine must statistically beat a simple momentum ranking and, after costs, be better than the index **and** than an equal-weighted portfolio of all stocks, otherwise it does not go live
- Ongoing monitoring with automatic status "Under observation" in the event of a loss of performance

**Limitations:** Free price data contain hardly any delisted stocks (survivorship bias). The app therefore forms the historical universe from SEC reporting entities, applies a delisting return for stocks that have disappeared and declares periods with too many gaps invalid. For European stocks, free point-in-time fundamental data are lacking; there the engine works only with price and volume features.

**Learning module:** Stage 2 ("How to read evidence") gets a lesson on the Prediction Engine: why 55 % is a lot, what calibration means and why a ranking is not a buy list.

### 4.14 UI design

**Goal:** Clear and illustrative, few buttons, uncluttered. Submenus rather than everything on one surface, but at most two levels deep.

**Information architecture (max. 2 levels):**

| Main area | Subpages | Answers the question |
|---|---|---|
| Overview | – | What matters today? Leads with the **monthly recommendation** (core message in one sentence, actions), then portfolio status, trading signals, warnings, learning prompt |
| **Anlegen** | Recommendation · Goals & portfolio · Projection · Investment policy statement | What should I do with my money, how do I stand in relation to my goals, what can I expect? |
| Trading | Swing · Intraday · Stock ranking | What do the trading strategies and the Prediction Engine say, and why? |
| Portfolio | Positions · Risk · Journal | Where do I stand, how much risk am I carrying? Without a depot: entry point "Set up depot" (manual, CSV, IBKR). In simulation mode this area shows the practice depot |
| Market | Briefing · Insider & filings · Expert scorecard | What is happening, and which of it is reliable? |
| Options | Chain & valuation · Strategies (locked until learning stage 6) | Is this contract fairly valued, what can I lose? |
| Learn | Learning path · Simulator · Glossary · Quiz | What do I need to understand and practise before I use this? |
| *Bottom, set apart* | Evidence & backtests · Data quality · Settings | Is the basis sound? (broker optional, capital, block list, security) |

**Design principles:**
- **One core message per page.** Every page answers exactly one question from the table; everything else is one level deeper.
- **Progressive disclosure:** card with key figure → click opens details (chart, "Warum?", evidence, risk). No tables with 20 columns on the first level.
- **At most 1–2 primary actions per page.** Filters and settings in collapsible sections.
- **Signal card as the basic building block:** security, direction, hit rate with confidence interval, risk in euros, status (new/active/expired), "Warum?" link. Structured the same way everywhere.
- **Uncertainty visible, not hidden:** confidence intervals as bars, "no signal" as an equal-ranking, calm state instead of an error message.
- **Colour with meaning:** restrained base surface, colour only for direction and warnings; never only red/green (colour vision deficiency), always with a symbol or text.
- **Numbers easy to read:** tabular figures, German number format, units always included.
- **Light and dark mode.**

**Design process:**
1. **Research** before the first dashboard: Mobbin (via the connected connector) for patterns from finance, portfolio and trading apps, in particular overview pages, watchlists, detail views and onboarding; in addition the frontend design skill for a distinctive aesthetic direction instead of a standard dashboard look.
2. **Mockups** of the six core pages (Overview with monthly recommendation, Anlegen: Goals & portfolio, Projection, signal detail, briefing, Learning path) as well as of the onboarding (profile, loss question, investment policy statement) as a design artefact to click through and comment on before any code is written.
3. **Implementation** only after you have approved the mockups.
4. **Design review** before every release: check against the principles above, screenshots in both modes and at a narrow window width.

**Technical limitation you should be aware of:** Streamlit is fast and gets by without JavaScript dependencies, which fits well with the security standards. In terms of design, however, it is limited (layout, animations, custom components). Recommendation: **v1 with Streamlit** (page-based navigation with sections, custom theme, sparing CSS). Because engine and interface are separate, the interface can later move to a custom web frontend if Streamlit cannot carry the design. That would, however, bring in a JavaScript ecosystem with its own supply-chain risk and must then be decided deliberately.

## 5. Tech stack

| Area | Tool | Note |
|---|---|---|
| Language | Python 3.12+ | |
| Broker | `ib_async` + IB Gateway | Not `ibapi` packages from PyPI |
| Data | pandas, DuckDB; `yfinance` as fallback | |
| Indicators | TA-Lib or own functions | **Not** `pandas-ta` |
| Backtest | `vectorbt` (swing), `bt` (allocation) | |
| Validation/portfolio | `skfolio` + own DSR/PBO | |
| News/sentiment | `transformers` + ProsusAI/FinBERT, GDELT, Finnhub | Local open-weight LLM for summaries, no paid API |
| Filings/macro | `edgartools`, `fredapi`, `sdmx1` | |
| Options | `py_vollib`, `QuantLib` | |
| Prediction engine | `lightgbm` (MIT, Microsoft), `scikit-learn` (BSD-3) | Check before adding to the allowlist: according to research, the LightGBM repository has moved to a new GitHub organisation (lightgbm-org); confirm that the PyPI page points there and that the move was announced by the previous maintainers |
| Dashboard | Streamlit + Plotly | Telemetry off, localhost only |
| Scheduling | APScheduler 3.x | |
| Development | Claude Code, Git | |

**Installation hygiene:** see quality standards section 1 (review protocol, allowlist, `--require-hashes`, wheels only, 7-day waiting period for updates, `pip-audit`).

## 6. Roadmap

| Phase | Content | Gate |
|---|---|---|
| 0: Research | Tools, building blocks, evidence (done, 20260924); formalise strategies (done, 20260925: `20260925_strategie-katalog_en.md`) | ≥ 8 formalised strategies with evidence grade (met: 8 core/candidate strategies, 4 options strategies, 11 control rules, independently reviewed) |
| 0b: Calculation-core specification | All formulas with primary sources, conventions, edge cases and reference values for tests; a separate research step | Every formula has at least one published reference value and an independent second review |
| 1: Foundation | Bitemporal data layer, `PointInTimeView`, instrument model, DuckDB, leakage tests, start of intraday recording | 20 years of daily data for gold, 10 UCITS ETFs, 20 stocks loaded cleanly; leakage tests green |
| 2: Backtest engine | Costs, walk-forward, DSR, PBO; event-driven confirmation loop | Exact tests on synthetic series with an analytically known result; qualitative reproduction of the Faber trend filter over the freely available period (exact reproduction not possible because the original data is licensed, see calculation-core specification section 11); all calculation-core tests green |
| 2b: UI concept | Mobbin research, aesthetic direction, mockups of the six core pages and of the onboarding | Mockups approved by you |
| 3: **"Anlegen" (Invest) core module + learning stages 1–2** — first usable version | Investment specification A1–A13: onboarding (profile, loss question, goals), preconditions, equity share, building blocks, ETF selection with a curated candidate list, savings plan and rebalancing, tax engine, projection, monthly recommendation, investment policy statement (IPS), guardrails; base portfolio L1; overlays L2–L4 (off by default); first dashboard according to the approved UI concept, "Why?" panels, glossary | All tests TA1–TA22 green; tax engine and projection independently reviewed; monthly recommendation is generated from real data; overlays active only if they pass the gates and the after-tax gate; lessons 1–2 complete; design review passed |
| 3b: Simulator | Time travel (with blind mode and scenarios) and live practice depot, order types, evaluation; possible in parallel with phase 3 | All execution tests from specification section 12 green; simulator and backtest deliver identical results for identical orders; holdout lock effective |
| 4: Market intelligence v1 | Ingest, classification, briefing, scorecard logging; possible in parallel with phase 3 | Pipeline runs stably for 4 weeks, all entries with timestamp and source |
| 5: Trading module swing + learning stage 3, journal | Gold & co., then futures/CFDs with learning stage 5 | As phase 3, plus financing and roll costs |
| 5b: Trading module intraday | Research on hourly bars and own recordings, stricter cost model | ≥ 12 months of own intraday data; gates as in phase 3 with lower "too good" thresholds |
| 6: Broker connection (optional) | IBKR paper account, depot (brokerage account) sync, IBKR data, option chains; dropped if you work without a broker | Live signals match the backtest behaviour |
| 7: Options module + learning stage 6 | Valuation logic, starter set, forward logging; stays locked until the quiz is passed | Logic reproduces IBKR Greeks and IV within a tight tolerance |
| 8: Activate tilts | Market intelligence tilts through the validation engine | Tilt improves the walk-forward result after costs and haircut |
| 8b: Prediction engine | EDGAR fundamental data point-in-time, features, baselines, LightGBM ensemble, calibration, prediction intervals, monitoring | All gates from specification PE10 met in walk-forward (rank IC significant, beats the momentum baseline, top quintile beats both the cap-weighted and the equal-weighted benchmark after costs with DSR ≥ 0.95, PBO ≤ 0.05); calibration passes S9; all tests T32–T40 green |
| 9: Paper trading | ≥ 3 months, all modules without real money | Live results within the backtest confidence range |
| 10: Execution (optional) | Activate adapter, paper account first | Safety rules from 4.10 implemented |

All phases run on free data. Costs arise only when you later make real trades (fees) or deliberately decide on a data subscription.

## 7. Risks and countermeasures

| Risk | Countermeasure |
|---|---|
| Overfitting | Walk-forward, DSR, PBO, paper trading gate |
| Look-ahead bias | Bitemporal data, `PointInTimeView`, automatic leakage tests, sealed holdout, no LLM backtests before the training cutoff (quality standards section 3) |
| No strategy or tilt survives | Valid result; app shows "no signal", base portfolio L1 of the "Anlegen" core module remains the basis |
| Leverage and options | Futures/CFDs only from phase 5 with learning stage 5, options only from phase 7 with learning stage 6; starter set, maximum-loss rules, stress tests |
| Scope too large | Strict sequence; each module counts as "done" only when its gate is reached |
| Manipulated content (prompt injection, pump articles) | LLM without action rights, source whitelist, hype as a warning rather than a signal |
| Data costs grow | Budget 0 €; every paid source requires an explicit decision |
| Supply-chain attacks | Review protocol, allowlist, hash pinning, read-only API (quality standards section 1) |
| Calculation errors in the evaluation | Specification before code, four levels of checks, independent second review (quality standards section 2) |
| Intraday with too little data | Own recording, signals only after ≥ 12 months of history |
| Tax errors | IBKR does not withhold German tax; export trades, Anlage KAP; for options, a tax adviser if necessary |
| False sense of security from learning progress | Unlocking means "understood", not "profitable"; the paper trading gate still applies |
| False precision of the prediction engine | Calibration on a held-out time block, plausibility cap derived from the measured rank IC, status "Under observation" on loss of performance, no percentage figure without a passed calibration |
| Survivorship bias in free price data | Universe from SEC filers, delisting return, invalidity rule, notice on every result; cannot be fully eliminated |
| Overloaded interface | Information architecture with max. 2 levels, mockup approval before code, design review per phase |
| Illusory learning in the simulator (hindsight bias, overly optimistic execution) | Blind mode, no rewinding, conservative execution rules, comparison with a benchmark |
| Confusing the simulation with the real depot | Consistent labelling throughout, no order route out of the simulator |

## 8. Open questions

None. All decisions are in section 2.

## Sources

See `20260925_anlage-spezifikation_en.md` (sources for the core module), `20260924_trading-app-research.md` (complete source list) and `20260924_trading-app-qualitaetsstandards.md`. In addition:
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance, 20*(4), 39–69.
- Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management, 40*(5), 94–107.
- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management, 9*(4), 69–79.
- Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics, 104*(2), 228–250.
