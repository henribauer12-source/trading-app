# Trading-Analyse-App

A private, local analysis tool for Henri: evidence-based signals (long-term, swing, intraday),
market intelligence, an options module, a stock-ranking prediction engine, a practice simulator
and a learning path. Python + local Streamlit dashboard. Broker connection (Interactive Brokers)
is optional. Budget for data: 0 €. Nothing here is investment advice, and the app is never shared.

## Knowledge engine — report after every session

Before coding, search `~/claude/code_logs/` and `~/claude/INDEX.md` for a prior instance — reuse
the pattern, cite it. After any task that took more than one edit, was environment-specific, or
failed before it worked: write a facts-only report to `~/claude/code_logs/_inbox/` (template
`~/claude/code_logs/_inbox/_report-template.md`) plus one line in
`~/claude/logs/vscode/<YYYYMMDD>.md`. Skip trivial changes. Full contract:
`~/claude/docs/agents/claude-code-operator.md`.

## Source of truth (read before any work)

All in `docs/`. When they disagree, the higher one wins; raise the conflict instead of choosing.

1. `20260924_trading-app-qualitaetsstandards.md` — security, calculation-core rigour,
   look-ahead-bias rules, intraday data limits. Binding for every phase.
2. `20260925_rechenkern-spezifikation-v1.4.md` — every formula, convention, cost/execution rule,
   the prediction engine, and the test catalogue (T1–T40) with reference values and tolerances.
3. `20260925_strategie-katalog.md` — every strategy as an exact rule plus its YAML definition,
   evidence grade, gates (G1–G9) and benchmarks.
4. `20260925_trading-app-plan-v8.md` — modules, architecture, UI information architecture,
   roadmap with phase gates.
5. `20260924_trading-app-research.md` — background evidence (tools, building blocks, media/expert
   signals, options). Context, not rules.

The documents are in German; code, identifiers and comments are English; everything the user
sees in the app is German.

Specs and tickets: `~/claude/.scratch/trading-app/spec.md` and `issues/NN-*.md` (one per
phase, `Status:` line per `~/claude/docs/agents/triage-labels.md`).

## Non-negotiables

- **Spec before code.** If code needs a rule the spec does not contain, change the spec first
  (new version, changelog entry), then the code. Items marked UNVERIFIZIERT must be checked
  against the primary source before they are implemented.
- **Point-in-time only.** Strategy and model code reads data exclusively through
  `PointInTimeView(t)` (rows with `available_at <= t`). Bitemporal, append-only storage. The
  leakage tests (truncation, future perturbation, delay) run on every build.
- **Execution never at the signal price.** Next bar at the earliest (spec C4, E1–E13).
- **Dependencies.** None without an entry in `DEPENDENCIES.md` (audit protocol, standards §1.1)
  and Henri's explicit approval. Lockfile with hashes, `--require-hashes`, wheels only where
  possible, `pip-audit` clean. Banned: `pandas-ta`, `ibapi`/`ibapi-stable`/`ibapi-latest`
  from PyPI, `ib_insync`, `py_vollib_vectorized`, `mlfinlab`.
- **Every calculation module** passes its reference-value tests, a second independent
  implementation where the spec asks for one, property-based invariants, and a review by a
  separate agent that did not write the code.
- **Broker safety.** IB Gateway on 127.0.0.1 with Read-Only API while execution is disabled;
  paper account first; secrets in `.env` outside the repo or the macOS keychain.
- **Honest numbers.** No probability shown without passed calibration; "no signal" is a normal,
  calm state, not an error.

## Storage (iCloud + local cache)

Source code and docs live here in iCloud. Everything heavy or frequently written lives in
`~/claude-local/trading-app/` and is never synced: the Python virtualenv, the DuckDB database,
recorded intraday bars, caches, backtest outputs. A database inside iCloud gets corrupted by sync
conflicts. Git history likewise lives outside iCloud
(`git init --separate-git-dir=~/claude-local/trading-app/git`, as in ADR-0003).

## Commands

None yet — ticket 01 defines them (`test`, `lint`, `audit`, `run`).
