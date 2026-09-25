# Trading-Analyse-App

A private, local analysis tool. Evidence-based signals (long-term, swing, intraday), market
intelligence, an options module, a stock-ranking prediction engine, a practice simulator and a
learning path. Python + a local Streamlit dashboard. Broker connection (Interactive Brokers) is
optional and disabled by default.

**Not investment advice. Not shared with anyone. Data budget: 0 €.**

---

## Status

**Phase 0 and 0b complete and independently reviewed.** No application code exists yet — this
repository currently holds the specification, which is the deliverable of those phases.

| Phase | What | State |
|---|---|---|
| 0 | Research, tooling and evidence survey | done |
| 0b | Quality standards, calculation-core spec v1.4, strategy catalogue, plan v8 | done |
| 1 | Foundation: bitemporal data layer, `PointInTimeView`, instrument model, DuckDB, leakage tests, start of intraday recording | next |
| 2 | Backtest engine: cost model, execution rules, performance statistics, walk-forward | planned |
| 2b | UI concept and mockups | planned |
| 3–5b | Long-term module, swing module, intraday module | planned |
| 6–8b | Market intelligence, options module, prediction engine | planned |
| 9 | Paper trading, ≥ 3 months, no real money | planned |
| 10 | Execution adapter (optional, off by default) | planned |

Detailed gates per phase: `docs/20260925_trading-app-plan-v8.md` §6.

---

## What the app does

| Area | Content |
|---|---|
| **Long-term investing** | Trend-filtered allocation across broad UCITS ETFs, risk budgeting, rebalancing rules |
| **Trading** | Swing signals (hourly to daily) and intraday signals (minute bars) for gold and commodities, equities, ETFs/ETCs, futures, CFDs |
| **Prediction engine** | Monthly ranking of large liquid stocks by their calibrated probability of beating the universe median over 1 and 3 months |
| **Market intelligence** | News briefing, insider filings, an expert scorecard that tracks whether loud public forecasts actually came true |
| **Options** | Chain valuation, greeks, fair-value assessment; strategy templates locked until learning stage 6 |
| **Portfolio** | Positions, risk, journal — manual entry, CSV import, or optional IBKR sync |
| **Learning path** | Staged curriculum; several modules stay locked until the matching stage is passed |
| **Simulator** | A live practice account on real (≈ 15 min delayed) prices |

Out of scope: crypto, passing signals to third parties (would make it BaFin-relevant), fully
automatic order execution.

**Guiding principle:** the benchmark for every module is a cheap, broadly diversified ETF.
Anything that does not beat it after costs and risk-adjusted is not shown as a signal.

---

## The rules this project runs on

These are the non-negotiables. They exist because a backtest is trivially easy to fake by
accident.

- **Spec before code.** If code needs a rule the spec does not contain, the spec changes first
  (new version + changelog entry), then the code. Anything marked `UNVERIFIZIERT` is checked
  against its primary source before it is implemented.
- **Point-in-time only.** Strategy and model code reads data exclusively through
  `PointInTimeView(t)` — rows with `available_at <= t`. Storage is bitemporal and append-only.
  Three leakage tests (truncation, future perturbation, delay) run on every build.
- **Execution never at the signal price.** Next bar at the earliest, plus spread, fee and
  slippage (spec C4, E1–E13).
- **No dependency without an audit.** Every package needs an entry in `DEPENDENCIES.md`
  following the audit protocol (standards §1.1) and explicit approval. Lockfile with hashes,
  `--require-hashes`, wheels only, `pip-audit` clean.
  Banned: `pandas-ta`, `ibapi`/`ibapi-stable`/`ibapi-latest` from PyPI, `ib_insync`,
  `py_vollib_vectorized`, `mlfinlab`.
- **Every calculation module** passes its reference-value tests, a second independent
  implementation where the spec demands one, property-based invariants, and a review by an
  agent that did not write the code.
- **Broker safety.** IB Gateway on `127.0.0.1` with Read-Only API while execution is disabled;
  paper account first; secrets in `.env` outside the repo or in the macOS keychain.
- **Honest numbers.** No probability is displayed without passed calibration. "No signal" is a
  normal, calm state — not an error.

---

## Two design decisions worth knowing up front

### The intraday clock

Free data gives roughly 8 days of 1-minute bars, 60 days of 2–90-minute bars and 730 days of
hourly bars. Sixty days of minute data cannot validate an intraday strategy — the sample is far
too short for the statistics in spec §S1–S10 to mean anything.

So intraday runs on a clock instead of a shortcut:

1. **Record from phase 1.** The app writes its own intraday bars point-in-time, every trading
   day, starting the moment the foundation exists.
2. **Research** on hourly bars (2 years available) and on the growing self-recorded history.
3. **Signals** only after **≥ 12 months** of own data and passed gates — and then paper trading
   first.

The consequence: every day the recorder is not running is a day the intraday module ships later.
It is the only part of the roadmap with a real-world clock attached, which is why it starts in
phase 1 rather than in phase 5b where the rest of the intraday work sits.

Intraday also carries a stricter cost model (spread, per-trade fee, slippage on every fill) and
lower "too good to be true" thresholds, because the post-cost evidence for intraday strategies is
weaker than for swing.

### The prediction engine

Once a month it ranks large liquid stocks (US: top 500 by point-in-time market cap; Europe:
largest domestic names) by their chance of outperforming the **median of that universe** over 1
and 3 months. Per stock it shows rank, quintile, a calibrated probability with a 95 % interval,
an 80 % prediction interval for the return, and the three features that contributed most.

What it deliberately does **not** do: price targets, price forecasts, or claims about beating the
index (its target variable does not contain the index — spec PE5).

**The number that matters:** the best published method reaches an out-of-sample monthly R² of
0.40 % across all US stocks, 0.70 % among the largest 1,000 (Gu, Kelly & Xiu 2020). After
excluding micro caps and after costs, the edge shrinks further. A correctly calibrated
probability of beating the universe median therefore sits almost always between **45 % and
55 %**. At a rank-IC of 0.05, the stock at the 95th percentile has a 53.4 % probability.
**If the app ever shows 70–80 %, it is miscalibrated** — that is a bug, not a good day.

How it is kept honest (spec §13, PE0–PE11):

- Point-in-time fundamentals from SEC EDGAR using the acceptance timestamp, never the `frames`
  API (which silently serves restated figures)
- Features taken from the literature, not from the own backtest, rank-normalised per date, with a
  publication embargo until 31 December of each study's publication year
- Continuous rank-based target; probabilities appear only through calibration on a strictly
  later, separate time block
- Equal-weighted ensemble (Ridge + LightGBM over several seeds) — no estimated weights, no single
  "optimised" model
- Expanding training window, annual re-estimation, embargo, every variant counted as a trial for
  the deflated Sharpe ratio
- **Hard gates:** it must statistically beat a plain momentum ranking, and beat both the
  cap-weighted and the equal-weighted benchmark after costs (DSR ≥ 0.95, PBO ≤ 0.05). Otherwise
  it does not go live.
- Continuous monitoring with an automatic "under observation" status on performance decay
- Survivorship-bias handling: the historical universe is built from SEC filers at each date, a
  −30 % delisting return is applied to stocks that vanish, and any date missing more than 5 % of
  universe market cap invalidates the backtest for that period

A lesson in learning stage 2 explains why 55 % is a lot, what calibration means, and why a
ranking is not a shopping list.

---

## Repository layout

```
CLAUDE.md          Operating contract for AI agents working in this repo
docs/              The specification — see docs/README.md for precedence order
.gitignore         Secrets, heavy artefacts, iCloud conflict copies
```

Tickets and the working spec live outside the repository in
`~/claude/.scratch/trading-app/` (`spec.md` and `issues/NN-*.md`), one per phase.

### Storage split

Source and docs live in iCloud. Everything heavy or frequently written lives in
`~/claude-local/trading-app/` and is never synced: the virtualenv, the DuckDB database, recorded
intraday bars, caches, backtest outputs. A database inside iCloud gets corrupted by sync
conflicts. Git history lives outside iCloud too:

```
git init --separate-git-dir=~/claude-local/trading-app/git
```

---

## Tech stack (fixed in plan v8 §5, not yet installed)

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Storage | DuckDB (bitemporal, append-only) |
| Backtesting | vectorbt / bt |
| Portfolio | skfolio |
| ML | LightGBM, scikit-learn |
| Dashboard | Streamlit + Plotly (telemetry off, localhost only) |
| Scheduling | APScheduler 3.x |
| Broker | `ib_async`, optional, disabled |

Nothing on this list is installed yet. Each entry passes the audit protocol first.

---

## Commands

None yet — ticket 01 defines `test`, `lint`, `audit` and `run`.

---

## Disclaimer

Private project, built for one user. No investment advice, no recommendation to buy or sell any
security. Backtested results are not indicative of future performance. The author is not a
licensed financial adviser and the tool is never distributed.
