---
title: Trading Analysis App – Investment Specification (Core Module Investment Adviser)
date: 20260925
status: v1.7; independently reviewed up to v1.2, findings incorporated; additions in v1.3 (A5.1, A5.2), v1.4 (A5.1, A5.2, A5.3, A5.5), v1.5 (A1 P18, A2.5–A2.7, TA23–TA27), v1.6 (A5.1, A5.2, A15) and v1.7 (A5.2 on 2, A5.5) not yet independently reviewed
owner: Henri
basis: 20260925_trading-app-plan-v9_en.md, 20260925_rechenkern-spezifikation-v1.4.md, 20260925_strategie-katalog_en.md, 20260924_trading-app-qualitaetsstandards.md
language: en
binding: this English text (since v1.4)
supersedes: archive/20260925_anlage-spezifikation.md (German original of v1.3, no longer binding)
---

# Investment Specification v1.7 – "Anlegen" (Invest) Core Module

**Binding text.** This English document is the binding investment specification. The German original (v1.3) is archived in `archive/20260925_anlage-spezifikation.md` and no longer binding. German tax and legal terms (Vorabpauschale, Teilfreistellung, Günstigerprüfung, NV-Bescheinigung, Abgeltungsteuer, Sparer-Pauschbetrag, Verlusttöpfe, Aktienfonds, all § references) are kept as proper nouns, because a German tax adviser has to review them.

**Note:** This document specifies a private analysis tool. It is not investment or tax advice. The tax rules have been derived to the best of our knowledge from the statutory text and BMF-Schreiben (BMF circulars) and must be checked with a tax adviser before productive use.

## 0. Purpose and principles

The "Anlegen" module is the core of the app. Each month it answers one question: **What should I do with my money, and why?** It translates personal information into a strategic allocation, selects concrete products, plans the savings plan and rebalancing in a tax-optimised way, shows honest projections and records everything in a personal investment policy statement (IPS).

**Principles:**
1. **Evidence-backed simplicity before sophistication.** The default recommendation is a broadly diversified, low-cost global equity portfolio plus a safety building block. Deviations (tactical overlays, factors, individual stocks, gold) are limited, justified and only permitted if they have passed their test.
2. **The order of finances matters more than the choice of product:** expensive debt, emergency fund, then investing.
3. **Everything after costs and after German tax.** A measure that is better before tax and worse after tax is not recommended.
4. **Uncertainty is shown, not hidden.** Projections as ranges in today's euros, never as a point forecast.
5. **"Doing nothing" is a fully valid recommendation.** In most months it reads: the savings plan continues, no rebalancing needed.
6. **Henri makes the decision.** The app recommends, explains and documents; it does not act on its own.

**Status labelling** as in the calculation-core specification: VERIFIZIERT (primary source read), REPRODUZIERT, ENTSCHEIDUNG (reasoned own determination), UNVERIFIZIERT (check before implementation).

**Rounding and arithmetic:** All tax and money amounts with `Decimal`, not with floating point (in the review, floating point produced cent deviations in the solidarity surcharge). Rounding rules per quantity in section A8.

---

## 1. Overall flow

```
A1 Profile & goals ──► A2 Preconditions ──► A3 Equity share per goal ──► A4 Building blocks & weights
                                                                                               │
A11 Investment policy statement (IPS) ◄── A10 Monthly recommendation ◄── A9 Projection ◄── A5 Product selection
          │                                   ▲                                                │
          └──► A12 Guardrails                 └── A6 Savings plan & rebalancing ◄──────────────┘
                                              └── A7 Tactical overlays (strategy catalogue)
                                              └── A8 Tax engine (for A6, A7, A9, A10)
```

Every output is stored with timestamp, input data, parameters and code version (quality standards 2.4), so that every recommendation can be traced later.

---

## A1 Profile and goals

### A1.1 Inputs

**Structure according to the ESMA guidelines on the suitability assessment** (ESMA35-43-3172, applicable since 20231003; para. 24: marital status, age, employment, liquidity needs, knowledge and experience, financial situation including ability to bear losses, objectives including risk tolerance, sustainability preferences). VERIFIZIERT.

| No. | Item | Type | Use |
|---|---|---|---|
| P1 | Year of birth | Number | Horizon plausibility, retirement-provision notes (A13) |
| P2 | Net income per month, type of income (fixed / fluctuating / side job / studies) | Number, selection | Capacity (A3.2), tax check (A8) |
| P3 | Necessary expenses per month | Number | Emergency-fund target (A2) |
| P4 | Available liquid funds (current account, instant-access savings (Tagesgeld)) | Number | Emergency-fund status |
| P5 | Debts with interest rate (overdraft (Dispo), credit card, loans, BAföG loan) | List | Precondition (A2) |
| P6 | Dependants who depend on you financially | Yes/No | Capacity |
| P7 | Does your income depend on the stock market or on a particular industry? | Selection | Capacity, country diversification |
| P8 | Goals: name, amount (optional), target date or "long-term/retirement provision" | List | Horizon per goal (A3.1) |
| P9 | Monthly savings amount and planned increase per year | Number, % | Savings plan (A6), projection (A9) |
| P10 | Lump sums (available or expected) | List | Implementation (A6.4) |
| P11 | Loss question in euros (A1.2) | Number | Tolerance (A3.3) |
| P12 | Risk tolerance scale (A1.3) | Questionnaire | Tolerance (A3.3) |
| P13 | Two comprehension questions (A1.4) | Selection | Consistency, learning module |
| P14 | Tax details: church tax (none / 8 % / 9 %), expected taxable income, depot (brokerage account) at a German or foreign bank | Selection, number | A8 |
| P15 | Preferences: distributing/accumulating, sustainability, gold yes/no, individual stocks yes/no, savings-plan-eligible at the broker | Selection | A4, A5 |
| P16 | Do you receive BAföG? | Yes/No | Asset limit (A6.3) |
| P17 | Are you covered by non-contributory family insurance? | Yes/No | Income limit (A6.3) |
| P18 | Do you have a property loan? If yes: nominal Sollzinssatz, fixed or variable rate, date of full receipt of the loan, contractual Sondertilgung allowance | Yes/No, number, selection, date, number | A2.7 |

### A1.2 Loss question in euros

The app shows a bar with the expected depot value in 5 years (B5, according to the A9 base scenario) and below it the same value after a decline of 50 %. Question: **"Up to what loss in euros would you hold on without selling?"** Input L€.
Rationale: ESMA guidelines para. 44, 46, 48 require practical loss scenarios with "concrete figures" instead of self-assessment. VERIFIZIERT.

### A1.3 Risk tolerance scale

- Complete 13-question scale according to Grable & Lytton (1999); reliability in the original study α = 0.75, in the 15-year evaluation (n = 160,279) α = 0.77. VERIFIZIERT
- Use **only in full** (a subset is not validated) and as an orientation, not as the sole basis: questionnaires explain only a small part of actual risk behaviour (Klement, 2015: 13.1 %). VERIFIZIERT
- Check the **usage rights** of the scale before implementation (UNVERIFIZIERT). If not usable: the scale is dropped, A3.3 relies solely on the loss question

### A1.4 Comprehension and consistency check

- Two comprehension questions (e.g. "What happens to a global ETF if stock markets fall 40 %?"; "What does an equity share of 80 % mean?"), according to ESMA para. 52
- Contradiction check according to ESMA para. 51: e.g. high willingness to accept losses with a horizon < 3 years, or high scale scores with incorrectly answered comprehension questions → notice and follow-up question, the lower result applies until clarified. VERIFIZIERT (structure), rules ENTSCHEIDUNG

### A1.5 Repetition

- Annual review of the profile (reminder at the IPS review date)
- **No re-profiling during a drawdown** without a waiting period (A12): risk aversion rises markedly after crises (Guiso, Sapienza & Zingales, 2018); lowering the equity share at the trough realises losses. VERIFIZIERT (finding), rule ENTSCHEIDUNG

---

## A2 Preconditions (order of finances)

| Step | Condition | Recommendation |
|---|---|---|
| V1 | Debts with an interest rate above 5 % p.a. nominal (overdraft, credit card, consumer loan) | Repayment before investing; at most a token savings plan (e.g. 25 €) to build the habit |
| V2 | Liquid funds < starter reserve R_S = max(1,000 €; 1 × P3) | 100 % of the monthly savings amount into the reserve |
| V3 | Liquid funds < target reserve R_Z = max(R_S; 3 × P3), or max(R_S; 6 × P3) with fluctuating income or dependants | 50 % of the monthly savings amount into the reserve, 50 % into the investment plan (distributed across the pots like their planned monthly savings amounts) |
| V4 | Reserve reached | 100 % of the monthly savings amount into the investment plan |

- **Rationale V1:** Repayment yields a **certain** return equal to the interest rate. From about 5 % nominal it is of the same order of magnitude as the **uncertain** equity return (base assumption 4 % real at the median, with around 2 % inflation about 6 % nominal, A9.2) and is superior to it on a risk-adjusted basis. The threshold is derived in A2.6 from the after-tax expected return; it is recomputed, not hard-coded. Threshold ENTSCHEIDUNG
- **Reserve** is held in an instant-access savings account at a bank with statutory deposit protection (100,000 € per depositor and bank; VERIFIZIERT, BMF). It does **not** count towards the equity share and not towards the depot
- **BAföG loans** (interest-free, § 18 Abs. 2 Satz 1 BAföG) are not expensive debt (V1 does not apply). The app gives no advice on BAföG repayment; the discount on early repayment under § 18 Abs. 10 Satz 2 BAföG is deliberately out of scope
- **Evidence:** An emergency fund is associated with higher financial well-being (Vanguard survey 2024, correlational, not peer-reviewed); the Verbraucherzentrale (consumer advice centre) recommends 2–3 net monthly salaries. There is no peer-reviewed derivation of an optimal number of months. VERIFIZIERT (sources), thresholds ENTSCHEIDUNG

### A2.5 Financing guide (explanatory, no computation)

A panel on the preconditions step. Static text, no inputs, no state. It explains why the order of finances is what it is, because a rule the user does not understand is a rule they abandon in the first bad month (A12).

The order — expensive debt, then reserve, then investing — follows from comparing a **certain** return against an **uncertain** one:

1. **Repaying debt yields a certain return equal to the interest rate**, and that return is not taxed. No Abgeltungsteuer arises on money never paid to a lender.
2. **Investing yields an uncertain return, and the gain is taxed** (A8). The base assumption is 4 % real at the median, about 6 % nominal (A9.2).
3. **The reserve is not an investment.** It buys the ability to leave the depot untouched during an income shock, which is what protects a long horizon in practice.

This is why V1 uses a threshold instead of "always repay first": below it the uncertain return is plausibly higher, above it the certain one wins on a risk-adjusted basis.

### A2.6 Repayment versus investing (the hurdle rate)

**Rule:** compare the loan's nominal Sollzinssatz against the **after-tax** expected return of the investment plan, not against the pre-tax return. A loan cheaper than the hurdle may be kept.

| Step | Quantity | Value |
|---|---|---|
| Expected nominal return (A9.2) | r | 6.00 % |
| Teilfreistellung for Aktienfonds (§ 20 Abs. 1 Satz 1 InvStG) | — | 30 % of the Erträge exempt |
| Taxable share | — | 70 % |
| Abgeltungsteuer incl. Solidaritätszuschlag, k = 0 (TA1) | s | 26.3750 % |
| Effective burden on the gain | 0.70 × s | 18.4625 % |
| **After-tax expected return** | r × (1 − 0.70 s) | **4.8923 %** |

- The hurdle is **recomputed** from the tax engine (A8), never hard-coded: it moves with r, the Teilfreistellung, the Abgeltungsteuer rate, church tax k, and with Günstigerprüfung or an NV-Bescheinigung where those apply. The 5 % in V1 is the rounded presentation of this computation, not an independent constant.
- Computed with `Decimal` under the A8 rounding rules; no floating point.
- Displayed as a range, not a point value (principle 4): 6 % is a median, not a promise.
- **Asymmetry, to be stated plainly in the UI:** the repayment return is certain, the investment return is a median. Equal numbers do not make equal decisions — a tie favours repayment.

### A2.7 Property loans (only if P18 is set)

Behind a toggle, off by default, so that onboarding does not grow for users without a property loan. The two rules below are statutory, not preferences.

| Step | Condition | Recommendation |
|---|---|---|
| V5 | Immobiliar-Verbraucherdarlehen with a **fixed** Sollzinssatz, inside the fixed-rate period | Overpayment beyond the contractual Sondertilgung allowance is generally **not available**; A2.6 does not apply to this loan. The monthly amount follows V3/V4 |
| V6 | Ten years since full receipt of the loan have passed or are approaching | Termination with six months' notice is possible without a Vorfälligkeitsentschädigung; show the date, recompute A2.6 from it |

- **V5, § 500 Abs. 2 BGB:** a consumer may repay a Verbraucherdarlehen early at any time, in whole or in part (Satz 1). For an Immobiliar-Verbraucherdarlehen with a fixed Sollzinssatz, early repayment during the fixed-rate period requires a **berechtigtes Interesse** (Satz 2). The app therefore asks for the contractual Sondertilgung allowance instead of assuming one. VERIFIZIERT (statutory text)
- **V6, § 489 Abs. 1 Nr. 2 BGB:** ten years after **full receipt**, termination in whole or in part with six months' notice. If the Sollzinssatz or the repayment schedule is renegotiated afterwards, the date of that agreement **replaces** the date of receipt and the ten years start again (Halbsatz 2). The anchor date is therefore stored as its own field (P18) and never derived from the origination date. This right cannot be excluded or made harder by agreement (§ 489 Abs. 4 Satz 1). VERIFIZIERT (statutory text)
- **§ 489 Abs. 3 BGB:** the termination is deemed not given if the amount is not repaid within two weeks of it taking effect. The exit therefore requires the money to be ready, which is a planning input, not a footnote.
- The computed § 489 date is shown as a **date on the timeline, not as a recommendation**. Whether terminating is worthwhile depends on the rate available at that time, which the app does not forecast.
- **Out of scope:** refinancing optimiser, amortisation schedule, what-if simulator, Riester, Rürup, Bausparvertrag, KfW programmes.

---

## A3 Strategic equity share per goal

Each goal (P8) gets its own pot p with horizon h_p (years until the planned withdrawal) and its own risk share q_p. Default goal without a date: "Long-term wealth / retirement provision" (h = 30).

**q_p = min(q_Horizont(h_p), q_Kapazität, q_Toleranz,p), rounded down to 10 percentage points.** The risk share q_p is the budget for global equities and all satellites (A4); the displayed pure equity share may be lower if gold is included.

### A3.1 Horizon cap (glide path)

Anchor points, **linearly interpolated monthly** in between:

| Horizon h | q_Horizont |
|---|---|
| ≥ 15 years | 100 % |
| 10 years | 80 % |
| 5 years | 60 % |
| 3 years | 30 % |
| ≤ 1 year | 0 % |

- q_Horizont is recalculated **monthly**. Because q_p is rounded down to 10 percentage points, the effective share falls in steps of 10 percentage points; the interpolation determines **when** the next step is due (between 10 and 5 years roughly every 30 months, between 5 and 1 year roughly every 8 months). This prevents a single large rebalancing on one cut-off date
- Implementation of a step: first via new monthly savings amounts (A6.1); sales according to A6.2 including the glide-path rule for the last 36 months, spread across tax years as far as the schedule allows, in order to use the Sparer-Pauschbetrag (saver's allowance) each time
- **Rationale for the direction:** Real equity drawdowns of over 70 % have occurred (Dimson, Marsh & Staunton, Yearbook 2026). After 1929, US equities remained below their peak in real terms until 1945 (about 15.5 years); the Japanese Nikkei price index (without dividends) took 34 years to regain its 1989 level. Over 30 years, a broadly diversified investor in 39 developed countries had a probability of 12 % of losing in real terms (Anarkulova, Cederburg & O'Doherty, 2022); in the associated working paper "Long-Horizon Losses", 13 % for domestic and 4 % for international equities. VERIFIZIERT (findings)
- Anchor points ENTSCHEIDUNG (no single source)

### A3.2 Capacity cap

- Fluctuating income (P2) or dependants (P6): q_Kapazität = 70 %
- Income strongly correlated with the stock market (P7): q_Kapazität = 80 % and a note on international diversification (Anarkulova et al., working paper: with a correlation of 0.5 between income and home market, the optimal home share falls from 33 % to 18 %)
- otherwise 100 %
- Levels ENTSCHEIDUNG; direction supported by evidence: for young people with a secure income, human capital acts like a bond (Cocco, Gomes & Maenhout, 2005). VERIFIZIERT

### A3.3 Tolerance cap (jointly across all pots)

1. **B5 per pot** deterministic and without circular reasoning: B5_p = current value of the pot + planned contributions over the next 5 years, compounded at 4 % real at **q = 100 %**. This is the upper estimate and thus the cautious choice for the cap
2. **D_Stress** = real stress drawdown of the global equity portfolio; placeholder **0.60**, until it is calibrated in phase 1 from the pooled history (A9.1) as the largest real decline of the global portfolio (UNVERIFIZIERT until then)
3. **Allocation of the loss budget L€ across the pots**, longest horizon first (that is where risk is most bearable): for pots in descending order of h_p, q_Toleranz,p = min(1; L_rest / (D_Stress × B5_p)), then L_rest = L_rest − q_Toleranz,p × D_Stress × B5_p
4. If the Grable-Lytton score is in the lower third, each q_Toleranz,p is reduced by 20 percentage points, not below 0
5. **Floor:** If Σ_p B5_p < 1,000 €, the tolerance cap does not apply; instead, the app shows a notice to repeat the loss question after one year
6. **Stability:** q_Toleranz,p and q_Kapazität are recalculated only at the annual profile review; a resulting change in q_p only takes effect if it amounts to at least 10 percentage points (hysteresis). **q_Horizont is exempt from this** and is evaluated monthly (A3.1), so that the reduction before the target date does not lag behind by up to a year. This way the share does not fall step by step every year merely because the depot grows; instead, the app asks whether L€ still fits
- ENTSCHEIDUNG

### A3.4 Default result and context

For a long-term goal (≥ 15 years), stable income, no expensive debt, a full reserve and sufficient willingness to accept losses, the result is **q = 100 % risk budget in the depot**, with the reserve as the safety building block outside it. Relative to all liquid funds, the equity share is considerably lower at the start (example: reserve 3,000 €, depot 1,000 € gives 25 %) and rises as soon as the depot clearly exceeds the reserve.

Two perspectives are presented openly in the learning module:
- **Life-cycle view** (Cocco et al., 2005; Vanguard glide path 2022: about 90 % equities up to age 40): the equity share declines over the course of life
- **All-equity view** (Anarkulova, Cederburg & O'Doherty, working paper "Beyond the Status Quo", first published 2023, revised 2026, not peer-reviewed): 100 % equities throughout life, one third of it in the home market, delivers more wealth in the 39-country bootstrap with a lower probability of running out of money in old age (7.0 % versus 19.7 % for the target-date fund); the authors themselves cite a possible drawdown in retirement of 74 % (95th percentile) and the risk of giving up in a crash. Criticism (Asness, press only): diversification across asset classes is superior per unit of risk
- VERIFIZIERT (figures), default rule ENTSCHEIDUNG

---

## A4 Building blocks and weights

### A4.1 Core (always)

| Building block | Content | Share |
|---|---|---|
| K1 Global equities | One ETF on a market-capitalisation-weighted global index including emerging markets (MSCI ACWI or FTSE All-World) **or** developed markets + emerging markets at market weight (about 88/12) | q_p − Σ satellites |
| K2 Safety in the depot | According to the pot's horizon: < 3 years €STR money-market ETF (or instant-access savings outside the depot); 3–10 years EUR government bonds or global bonds EUR-hedged, maturity matching the horizon; > 10 years (only if q < 100 %) EUR government bonds or global bonds EUR-hedged | 1 − q_p |

- **Market weight instead of home bias:** investors worldwide overweight their home market; for a German investor, a global index is already the correction (Vanguard, 2021; French & Poterba, 1991). VERIFIZIERT
- **Emerging-market overweighting** (e.g. 70/30) is an active bet without robust evidence; only as an explicit user choice, counted as a satellite. Rule ENTSCHEIDUNG
- **Foreign-currency bonds only EUR-hedged:** currency hedging almost always reduces risk for bonds (Vanguard, 2026). VERIFIZIERT
- **State of the indices (factsheets 20260831):** MSCI World 1,280 constituents, USA 72.14 %, top 10 26.61 %; MSCI ACWI 2,458 constituents, USA 63.59 %, emerging markets about 11.9 %; FTSE All-World 4,264 constituents, USA 61.71 %. The app displays the current country and concentration structure of the selected index (concentration warning for the USA and the top 10). VERIFIZIERT

### A4.2 Satellites (optional, only on explicit request)

All satellites of a pot together at most **20 % of the risk budget q_p** (i.e. 0.20 × q_p of the pot). Caps per satellite likewise relative to q_p.

| Satellite | Cap (share of q_p) | Evidence | Condition |
|---|---|---|---|
| S-Gold | 10 % | Over practicable horizons, gold is an unreliable inflation hedge (Erb & Harvey, 2013); benefit as diversification, not as a source of return | Only physically backed gold ETCs with an **exclusive** claim to delivery or to the proceeds of the deposited gold (BMF 20250514 Rn. 57); tax-free after > 1 year (A8.7) |
| S-Factor | 10 % | Factor premiums shrink by about 58 % after publication (McLean & Pontiff, 2016); 65 % of 452 anomalies already fail at t = 1.96 (Hou, Xue & Zhang, 2020); smart-beta indices no longer show any added value after ETF launch (Huang, Song & Xiang); US value lagged by around −56 % in 2007–2020; profitability (Novy-Marx, 2013) is the most robust | Only quality/profitability or multi-factor; written IPS commitment to a holding period of ≥ 15 years |
| S-Einzelaktien | 10 % in total, 2 % per stock | 57 % of US stocks performed worse over their lifetime than one-month T-bills; the entire net wealth creation since 1926 comes from 4 % of stocks (Bessembinder, 2018) | Only if the pot is ≥ 25,000 € (otherwise 2 % is below typical order sizes); each position is measured against K1; base rate shown in the purchase dialogue |
| S-Taktik | 10 % | Strategy catalogue L3 (rotation), S1 (trend following) as independent sub-portfolios with their own universe | Only strategies that have passed their gates **and** the after-tax gate (A8.11) |
| S-EM-Übergewicht | 10 % | no robust evidence | user choice only |

VERIFIZIERT (figures), caps ENTSCHEIDUNG. The overlays from A7 change weights temporarily; they are not satellites and do not count towards the 20-% limit.

### A4.3 Target weights

For each pot with risk budget q_p:
- w(K2) = 1 − q_p
- Σ_j w(S_j) ≤ 0.20 × q_p, each satellite ≤ its cap × q_p
- w(K1) = q_p − Σ_j w(S_j)
- Displayed separately: equity share = w(K1) + equity satellites; gold share; safety share
- ENTSCHEIDUNG

### A4.4 Pots and sub-depots

For tax purposes, FIFO applies **per depot, with a sub-depot counting as a separate depot** (BMF 20250514 Rn. 97–98; VERIFIZIERT by the review). Pots that exist only in the app share the FIFO order within the same depot. The app therefore recommends **one sub-depot per pot**; without sub-depots, it applies FIFO across the entire depot and points out that a sale "from pot A" affects, for tax purposes, the oldest units of the whole depot.

---

## A5 Product selection (concrete ETFs and ETCs)

### A5.1 Data acquisition (compliant with terms)

- **Curated candidate list** of about 30 ISINs across all building blocks, updated **quarterly** from freely published mandatory documents: PRIIPs key information document (KID) and the issuer's factsheet, manually or as individual downloads of public PDFs at low frequency
- Stored per field: value, source URL, as-of date, retrieval date (bitemporal, K2)
- **Time axes and precedence** (v1.3): the point-in-time key is the **retrieval date**, not the as-of date; a value counts as known from its retrieval onwards. This is conservative: the actual publication lies between as-of date and retrieval and usually cannot be read from the document. A retrieval before the as-of date is not permitted. A correction is a new entry with a later retrieval date; nothing is overwritten. If several values of a field are known, the KID rule below decides first; otherwise the one with the latest as-of date applies, and for equal as-of dates the one retrieved last. Annual values (tracking difference per calendar year) carry their year and cannot have an as-of date before 31 December of that year. ENTSCHEIDUNG
- **Precedence by document class** (v1.4 as KID before factsheet, extended in v1.6; implemented): if a field is known from several documents, the **class of the document** decides first, whatever the as-of dates; only within a class does the latest as-of date decide, then the latest retrieval, then the latest write. The order, highest first:

  1. **STATUTE** — the law itself. No document describing the law may override it; this matters for statutory values such as the Teilfreistellung rates
  2. **KID** — mandated by the PRIIPs Regulation, prescribed calculation method, issuer liability
  3. **ANNUAL_REPORT** — audited and reports realised figures
  4. **PROSPECTUS** — legally binding offering document, but less current on costs
  5. **FACTSHEET** — marketing material
  6. **ISSUER** — other issuer communication
  7. **EXCHANGE** — venue data
  8. **SECONDARY** — third party; can never be VERIFIED anyway (A5.1)

  Up to v1.4 the rule was binary — KID before everything else — which kept the ranking total but put an audited annual report behind a possibly stale KID whose cost figures are partly estimates. The classes above keep the order total and rank the reason for trusting a document rather than only its origin. When two documents disagree, both are stored, so the disagreement stays visible in the field's history instead of being silently resolved. The order is defined **once** in the code and the SQL is built from it; a new source type that is not classified fails the test suite instead of silently sorting last. ENTSCHEIDUNG

- **Verification status is deliberately not part of the ranking** (v1.6): a VERIFIED value of a lower class does not overtake an UNVERIFIED value of a higher one. Reason: an UNVERIFIED winner makes the dependent check come out **open**, which is the conservative outcome. Letting a verified lower-class value win would make checks pass more often, not less. Whether a verified value should beat an unverified one within the *same* class remains an open point in A15. ENTSCHEIDUNG
- **Verification status per value** (v1.3): VERIFIED if the value was read in the primary document (KID, factsheet, prospectus, annual report, publication of the issuer or the exchange, statutory text); otherwise UNVERIFIED (second hand, e.g. a comparison portal, or not yet checked). Second-hand values may be stored but are never VERIFIED. ENTSCHEIDUNG
- **Fund size in a foreign currency** (v1.4; implemented in v1.5): fund size gets a currency conversion, with USD as the primary reporting currency to convert from. The value is stored as published, in the currency of the document. For the hard filter (A5.2 no. 3) and the score (A5.3) it is converted into EUR at the rate **of the value's own as-of date**, never at today's rate; otherwise a stored fund size would silently change on every re-run. Rate source: the ECB euro foreign exchange reference rates (free, published daily). The rate is stored as a value with its own provenance like every other value (value, source URL, as-of date, retrieval date, verification status) and counts as known only from its retrieval, so at a cut-off date a converted fund size exists only if both the fund size and the rate were retrieved by then. ENTSCHEIDUNG

- **Missing rate: holiday or data gap** (v1.6, implemented): if the as-of date of a value has no ECB reference rate, the last published rate is carried forward (decided in v1.5, as in strategy catalogue G4) — but **only across days on which TARGET was actually closed**. The TARGET closing days are Saturdays, Sundays and exactly six days: New Year's Day, Good Friday, Easter Monday, 1 May, 25 December, 26 December (source: the ECB's list of public holidays, where the closing days are the ones marked with an asterisk; Ascension Day, Whit Monday, Corpus Christi, Day of German Unity, All Saints' Day, 24 and 31 December are ECB staff holidays on which TARGET stays open and rates are published). Good Friday and Easter Monday are movable and are computed, not tabulated, so the calendar does not expire.

  If **any** TARGET business day lies between the rate found and the requested date, a rate should exist for it and does not. That is a **data gap**, not a holiday, and it is reported as an error naming the requested date, the date of the rate found and the number of missing business days — instead of silently converting at a rate weeks too old. In the hard filter (A5.2 no. 3) a gap leaves the check **open**, with a reason distinguishing "no rates at all" from a gap of a stated length. ENTSCHEIDUNG
- **Prohibited:** automated queries at justETF (AGB § 3.1 prohibits "Einsatz von Programmen zur automatisierten Kursabfrage" (use of programs for automated price queries)) and Vanguard (terms of use prohibit automated access); undocumented internal APIs of issuers (e.g. iShares). VERIFIZIERT (research; not re-checked by the review)
- **Prices:** delayed data from Deutsche Börse (MiFIR mandatory publication, JSON download) after checking the licence terms for private use (UNVERIFIZIERT), otherwise free sources from the calculation core or broker export
- Identifier matching ISIN ↔ ticker symbol via OpenFIGI (free of charge, 25 requests per minute without a key; terms of use UNVERIFIZIERT)

### A5.2 Hard filters (yes/no per building block)

1. UCITS fund or, for gold, an ETC under German law with an exclusive claim to delivery of or proceeds from deposited gold; tradable on Xetra or a German trading venue; KID available in German
2. Index matches the building block (table A5.5)
3. Fund size (AUM) ≥ 100m € (break-even size according to industry figures, Lipper 2025, VERIFIZIERT); for K1 and money market ≥ 500m € (ENTSCHEIDUNG; in Germany a fund closure realises gains and ends the tax deferral)
4. At least 3 full calendar years of history; younger funds only with the label "new" and with net costs assessed via the TER with a 5-point deduction
5. Equity ETFs meet the Aktienfonds (equity fund) definition (> 50 % equity participations, § 2 Abs. 6 InvStG) → 30 % Teilfreistellung (partial exemption). VERIFIZIERT
6. Foreign-currency bonds: EUR-hedged
7. Optional: savings-plan-eligible at the user's broker (P15)

**Evaluation** (v1.3): every check ends as *fulfilled*, *violated* or *open*. It is open if the value is missing at the cut-off date or is UNVERIFIED: a second-hand value never lets a filter pass, but does not exclude the product for good either. A product is eligible only if no check is violated and none is open. An exception would let a single unchecked value block the evaluation of all candidates; a mere warning would let the product through. Clarifications:
- On 1: not tradable on Xetra → open, because another German trading venue is permitted but is not recorded as a field
- On 2: the index name from the document is **normalised** before comparison and then matched against the canonical name of the building block or one of its registered aliases (v1.7). Normalisation folds case and the separators/diacritics that providers vary freely (`€STR` = `ESTR`, `&` = `and`), and drops the decorations that carry no identity: a trailing `Index`, the return-variant suffixes `(Net)`, `(Net Total Return)`, `(TR)`, `(TRN)`, `(Gross)`, `(Price)`, and a trailing currency or hedging parenthesis. The decorations are not discarded silently — the return variant and the hedging tag are **extracted into their own fields** and checked separately (net vs gross against A5.5, hedging against filter 6), because the same index name with a different return variant is a different series. What is **never** normalised away is anything that changes the constituent set: `Sector Neutral`, `Screened`, `ESG`, `SRI`, `Leveraged`, `Short`, `Hedged` as a name component, a maturity band such as `1-3` or `10+`, or a region qualifier. Such a name only matches if it is registered as the canonical name or as an explicit alias, so a differently-composed index is still violated. Rationale (v1.7): up to v1.6 the comparison was exact against the A5.5 spelling, so the real spellings in the documents — `MSCI ACWI Index (Net)` for A5.5's `MSCI ACWI`, `ESTR Compounded` for `€STR` — came out as *violated*. That is a false rejection of a correct fund, the worst direction of error for a filter that decides what may be bought, and it affected K1 and K2 money market, which were considered implemented. An alias is data, not code: it is recorded per building block with the document class and as-of date it was read from (A5.1), so an alias rests on a real document and not on a guess. An unknown name is never guessed into a match — it stays **open** with the normalised form in the reason, which makes the missing alias visible instead of hiding it as a rejection
- On 2, status (v1.7): the matcher is implemented for all six building blocks. What is still missing is not code but **documents**: the alias table is filled from the KIDs and factsheets of the real candidates, and until a building block has at least one alias read from a document, its candidates stay *open*, not *violated*. The alternative MSCI World + MSCI EM (A5.4, at the user's request) is not modelled
- On 3: the thresholds are in EUR; a fund size published in another currency is converted as set out in A5.1 (v1.4, implemented in v1.5). If the rate is missing because of a data gap rather than a TARGET closing day, the check stays **open** and the reason names the length of the gap (v1.6)
- On 4: counted are the calendar years lying entirely between launch date and cut-off date; the current year never counts. Younger funds are not excluded but labelled "new"
- On 5: applies to K1 and S-Factor. On 6: applies to K2 global bonds
- On 7: user-specific (P15), not part of the instrument master data and not checked there
- ENTSCHEIDUNG

### A5.3 Scoring on fixed scales (0–100)

**Peer group:** only funds on the **same index** (tracking differences against different indices are not comparable). The choice between indices is a separate decision (A5.4).

**Fixed, absolute scales** instead of min-max normalisation (so that small differences among few candidates are not artificially inflated and adding a fund does not re-rank the others). Tracking difference TD = fund NAV total return − index net total return in percentage points per year (positive = fund better), rounded to 0.05 percentage points (**materiality threshold**: smaller differences count as equal).

| Criterion | Weight | Points | Rationale |
|---|---|---|---|
| Net costs (TD, average of the last 3 calendar years) | 40 % | clamp(50 + 250 × TD; 0; 100): TD 0 → 50, +0.20 → 100, −0.20 → 0 | TD includes TER, withholding tax, securities lending and trading costs; iShares Core MSCI World (TER 0.20 %) outperformed its net index in every year 2016–2025, on average by 0.083 percentage points (factsheet); costs are the most reliable characteristic (Morningstar, 2024). VERIFIZIERT |
| Stability of the TD | 5 % | clamp(100 − 500 × standard deviation of the 3 TDs; 0; 100) | Three values are not very robust, hence low weight |
| Fund size | 20 % | clamp(50 × log10(volume / 100m €); 0; 100): 100m → 0, 1bn → 50, 10bn → 100 | Closure risk |
| Liquidity | 10 % | clamp(100 − 5 × XLM in basis points; 0; 100) | Trading costs; published free of charge. VERIFIZIERT |
| Structure and counterparty risk | 10 % | fully physical 100, optimised physical 90, synthetic with multiple counterparties and transparent collateral 75, synthetic with one counterparty 60 | UCITS limits counterparty risk to 10 % of fund assets (Art. 52 Richtlinie 2009/65/EG, VERIFIZIERT). The withholding-tax advantage of synthetic ETFs is already contained in the TD and is not rewarded additionally |
| History | 5 % | 10 × min(full calendar years since launch, counted as in A5.2 no. 4; 10) | Robustness of the TD. Full calendar years (v1.4, as in A5.2 no. 4): the TD is published per calendar year, so the history score counts the years for which a usable TD value exists. ENTSCHEIDUNG |
| Transaction costs according to the KID | 5 % | clamp(100 − 500 × transaction costs in percentage points; 0; 100) | standardised, comparable |
| User preference | 5 % | 100 if accumulating/distributing as desired, otherwise 0 | essentially tax-neutral (A8.4) |

- **Gold:** instead of TD, the annual holding costs: clamp(100 − 200 × costs in %; 0; 100) (e.g. 0 % → 100, 0.36 % → 28), plus delivery conditions as a note
- **Money market:** TD against €STR; counterparty weight 15 % (at the expense of size)
- All scales and weights are ENTSCHEIDUNG, supported by the evidence cited; they are displayed in the app. **Ties:** higher net-cost points, then larger volume

### A5.4 Index choice for K1

MSCI ACWI and FTSE All-World are equivalent for this purpose (very similar country and sector structure). The app determines the best candidate per index (A5.3) and chooses between the two by TER; if the TERs differ by less than 0.05 percentage points, by fund size. ACWI IMI (including small caps) and World + EM at market weight are equivalent alternatives at the user's request. ENTSCHEIDUNG

### A5.5 Index mapping per building block

| Building block | Canonical index | Return variant | Notes |
|---|---|---|---|
| K1 Global equities | MSCI ACWI, MSCI ACWI IMI, FTSE All-World; alternatively MSCI World + MSCI EM at market weight | net | the alternative is not modelled (A5.2 on 2) |
| K2 Money market | €STR | — | **€STR itself is not investable** (v1.7): it is the ECB's overnight rate, and funds track a derived tradable series — a compounded index or a swap index at a spread. Such a name matches only as a registered alias of this building block |
| K2 EUR government bonds | FTSE EMU Government Bond Index (EGBI), all maturities or one of its maturity bands 1–3, 3–5, 5–7, 7–10, 10+ years | net | the band is part of the identity and is never normalised away; the band chosen must match the horizon (A4.1) |
| K2 Global bonds | Bloomberg Global Aggregate, EUR-hedged | net | the hedging tag belongs to the index name here, not only to the share class; an unhedged name violates filter 6 |
| S-Gold | physical gold, deliverable; reference price LBMA Gold Price PM, set by ICE Benchmark Administration at 15:00 London. The USD price is the auction price; LBMA's euro prices are indicative only | — | no index; filter 2 checks the reference price, the delivery claim is checked by filter 1 |
| S-Factor | MSCI World Sector Neutral Quality (selection criteria: return on equity, stable year-over-year earnings growth, low financial leverage) | net | **corrected in v1.7**, see below |

**Correction to S-Factor** (v1.7): up to v1.6 this table named *MSCI World Quality*. That index exists (MSCI 702787), but it is not the one the real products track — they track *MSCI World Sector Neutral Quality* (MSCI 705169), which applies the same three selection criteria **within each GICS sector**, so the sector weights stay close to the parent index. The two are different indices with different constituents; under the exact matching of v1.6 the v1.4 spelling would have rejected every actual candidate. The selection criteria named in v1.4 match the sector-neutral variant's published description, so the intent of the decision is unchanged and only the name is corrected. The likely source of the error: the products are *named* "Quality Factor" while their benchmark is not. UNVERIFIZIERT until read from a KID — until then S-Factor candidates stay open (A5.2 on 2, status)

**Starting indices** (v1.4): up to v1.3 this table named only index families for K2 EUR government bonds ("euro government bond index"), K2 global bonds ("Global Aggregate or Global Government, EUR-hedged"), S-Gold ("physical gold, deliverable") and S-Factor ("MSCI World Quality or multi-factor indices"). The EGBI was chosen because it has the maturity bands that K2 needs for "maturity matching the horizon" (A4.1). ENTSCHEIDUNG

### A5.6 Product switch

An existing product is not replaced solely because of a better score. **New monthly savings amounts always go into the best product.** A sale in order to switch is recommended if:
- the old product violates a hard filter (e.g. announcement of closure), or
- the **after-tax terminal wealth at the pot's horizon** with a switch is higher than without a switch by more than 0.5 % of the position (at least 50 €). Calculation with A8: "Keep" = old net costs until the horizon, tax on the sale at the end; "Switch" = tax now (after using the Sparer-Pauschbetrag and, where applicable, the Günstigerprüfung (most-favourable-assessment test)), new net costs, tax at the end. The tax on switching is predominantly a **prepayment** (it would be due at the end anyway), not a lost amount; the disadvantage lies in the lost tax deferral
- ENTSCHEIDUNG

### A5.7 Domicile

For German taxation, the fund domicile is neutral (§§ 2, 16, 18, 20 InvStG apply regardless of domicile; VERIFIZIERT). It is relevant only via withholding tax at fund level (Irish funds 15 % on US dividends, Luxembourg and German funds 30 %; UNVERIFIZIERT), which is reflected in the TD.

---

## A6 Savings plan, lump sums and rebalancing

### A6.1 Allocation of the monthly savings amount (cash-flow rebalancing)

Given: target weights w_i (Σ w_i = 1), current values V_i, total value V = Σ V_i, contribution C ≥ 0.
1. Target values after contribution: T_i = w_i × (V + C)
2. Shortfalls: F_i = max(0; T_i − V_i). Since Σ T_i = V + C, Σ F_i ≥ C always holds
3. Contribution x_i = C × F_i / Σ F_i; if Σ F_i = 0 (only possible if C = 0), x_i = 0. x_i ≤ F_i holds; overshooting the target is ruled out
4. **Minimum amount** per savings-plan position (user setting, e.g. 25 €): positions with x_i below the minimum amount receive 0 in this month; their amount is distributed proportionally across the remaining x_j. The deferred amounts are carried forward per position as an "open entitlement" and paid out in the month in which entitlement + x_i reaches the minimum amount, so that no position is permanently left out
5. **Implementation as a standing order:** the app tracks the savings plan actually set up at the broker (user input) and only suggests a change if the calculated allocation differs from it by more than 10 % of the monthly savings amount (half the sum of the absolute differences per position)
- Rationale: contributions to underweighted building blocks achieve most of the risk control at considerably lower cost (Vanguard, 2010; 2022); in Germany they also avoid taxes on sales. VERIFIZIERT (finding, industry sources)

### A6.2 Review, rebalancing by selling, and withdrawals

- **Once a year** (date in the IPS), the app checks the weights after the year's inflows
- Rebalancing by selling is recommended if a building block deviates from its target by more than **min(5 percentage points; 25 % of its target weight)** (the relative limit applies to small building blocks such as satellites)
- Outside the review date, such a deviation is only **displayed**; a recommendation for action is then given only if a satellite exceeds its cap by more than 25 %, or under the glide-path rule
- **Glide-path rule for the last 36 months** of a pot: the app checks the pot **quarterly**. If a new 10-percentage-point step of q_Horizont (A3.1) lowers the target share and the monthly savings amounts of the next 3 months are not sufficient to bring the deviation within the band, a sale is recommended in the same quarter. At the latest **12 months before the target date**, q_p = 0 has been implemented; a sale that triggers tax is not postponed to the next tax year for this purpose. Rationale: a decline of 50 % in the last year can no longer be recovered before the withdrawal; the tax saving from spreading, by contrast, is small. ENTSCHEIDUNG
- Sales **tax-optimised** (A8.10) and spread over several tax years if the deviation is not urgent
- **Withdrawals** (C < 0): sell first from overweighted building blocks, then in order of the lowest tax per euro withdrawn (A8.10)
- Rationale: an annual review with a threshold requires very few transactions and achieves almost the same risk control as frequent rebalancing; annual rebalancing is favourable for investors without a loss-offsetting strategy (Vanguard, 2010; 2022; industry sources, academic evidence thin)
- With only one global ETF and no safety building block in the depot, rebalancing does not apply

### A6.3 Sparer-Pauschbetrag, Günstigerprüfung and tax-free gain realisation

- The app estimates the year's investment income (distributions, Vorabpauschale (advance lump sum), planned sales) and recommends how to allocate the exemption order (Freistellungsauftrag) (1,000 €) across the German banks, or checks entitlement to an NV-Bescheinigung (non-assessment certificate) (A8.3)
- **Tax-free gain realisation:** If tax-free headroom remains at year-end, a sale followed by a repurchase can raise the cost basis.
  - **Permissibility:** A sale and repurchase on the same day at different prices is not an abuse of legal arrangements under § 42 AO (BFH IX R 60/07 of 20090825); the BMF-Schreiben of 20250514 contains no wash-sale rule. VERIFIZIERT (by the review). Condition: execution via the exchange, no prearranged trades at the same price with the same counterparty
  - **Headroom:** at least the unused Sparer-Pauschbetrag; **with the Günstigerprüfung, additionally the unused basic personal allowance (Grundfreibetrag)** (for working students with low income often the bigger lever). The app calculates the headroom with A8.3
  - **Number of units:** lot by lot according to FIFO (A4.4); to realise X € of taxable income from an equity ETF, a gross gain of X / 0.7 is needed (Teilfreistellung)
  - **Benefit:** the tax saved later only arises on the later sale and only if that sale would be taxable; it is discounted at 3 % p.a. and weighted by the probability that the later sale is taxable (default 0.8, user setting). Recommendation only if this benefit exceeds trading costs plus spread at least threefold. ENTSCHEIDUNG
- **Check side effects** (P16, P17): investment income can count towards total income for non-contributory **family insurance** in statutory health insurance (§ 10 SGB V); depot and reserve count as **assets under BAföG** (§§ 27–29 BAföG). The app shows the respective limits as soon as they are verified and warns against exceeding them. UNVERIFIZIERT (limit amounts)

### A6.4 Lump sums

- **Default: invest immediately**, allocated according to A6.1 with C = lump sum
- Rationale: lump-sum investing beat staggered investing over 12 months in about two thirds of historical cases (Vanguard 2012: USA 67 %, UK 67 %, Australia 66 %; average lead 2.3 / 2.2 / 1.3 %); staggered investing is theoretically inferior (Constantinides, 1979). VERIFIZIERT
- **Option:** spreading over 6 or 12 months as a deliberate behavioural decision; the app shows beforehand that in about two thirds of cases this costs return
- A monthly savings plan out of income is not staggered investing but investing as soon as the money is there

### A6.5 Increasing the monthly savings amount

Optional, following "Save More Tomorrow" (Benartzi & Thaler, 2004: savings rate rose from 3.5 % to 13.6 % in 40 months): automatic increase of the monthly savings amount by a fixed percentage with every income increase, set out in the IPS. VERIFIZIERT (finding)

---

## A7 Tactical overlays on the core

Overlays temporarily change the weight of K1 in favour of K2 (money market). They are **separate, registered variants** in the strategy catalogue (section 'Overlay variants for the "Anlegen" (Invest) core module') and are counted and tested there like any strategy.

| Overlay | Rule | Basis |
|---|---|---|
| OV-L2 Trend filter on K1 | Month-end: if the total-return price of K1 is above the average of the last 10 month-end closing prices, w(K1) is as in A4.3; otherwise w(K1) × 0.5, the other half goes into the money-market ETF | Faber (2007), applied to one building block; halving instead of a full exit limits false-signal costs and tax |
| OV-L4 Volatility targeting on K1 | w(K1) = (q_p − Σ satellites) × max(0.5; min(1; c_t / σ̂²_t)), c_t and σ̂²_t as in strategy L4 | Moreira & Muir (2017), market portfolio without leverage |

- **Only lower, never raise:** both overlays can at most halve the weight of K1
- **Gate:** the overlay must pass against the static mix with the same average investment ratio (strategy catalogue G7 item 8, Calmar ratio), namely **before and after German tax** with the same metric (A8.11)
- L3 and S1 are not overlays (own universes), but can be held as the S-Taktik satellite (A4.2)
- **Off** by default; activation only on explicit request and after learning stage 2, with display of the pre-tax and after-tax results
- ENTSCHEIDUNG

---

## A8 Tax engine (Germany, as of 2026)

All rules with their statutory provision; values with the year of validity in a versioned table. **Future values that are not yet available (e.g. base rate (Basiszins) 2027) are never estimated**, but flagged as "not yet published"; projections then use an explicitly marked assumed value.

### A8.1 Abgeltungsteuer (flat withholding tax), solidarity surcharge, church tax

- Income tax on capital income: **ESt = (e − 4q) / (4 + k)** (§ 32d Abs. 1 S. 4 EStG), e = capital income after Teilfreistellung and Sparer-Pauschbetrag, q = creditable foreign tax, k = church tax rate **as a decimal number** (0; 0.08; 0.09). The decimal form follows necessarily from § 32d Abs. 1 S. 1–3 (ESt = 0.25 e − 0.25 × k × ESt ⇒ ESt = e / (4 + k)); the notation in the BMF-Schreiben (BMF circular) (Rn. 133: "9 × 1/12 = 0,75") is abbreviated. If church membership covers only part of the year, k is reduced on a pro-rata basis in twelfths (Rn. 133). VERIFIZIERT (by derivation)
- Solidarity surcharge (SolZ): 5.5 % of the tax, **always** applied under the Abgeltungsteuer (the exemption threshold (Freigrenze — all-or-nothing, unlike an allowance) does not apply; § 3 Abs. 3 S. 2, § 4 SolZG), rounded down to the cent. VERIFIZIERT
- Church tax: k × ESt. Which federal state levies 8 % or 9 % is a user setting (mapping UNVERIFIZIERT)
- **Total burden** (recalculated twice): without church tax 26.3750 %; with 8 % 27.8186 %; with 9 % 27.9951 %

### A8.2 Sparer-Pauschbetrag

1,000 € (individual assessment), 2,000 € (joint assessment); no deduction of actual income-related expenses; at most up to the amount of the income (§ 20 Abs. 9 EStG). VERIFIZIERT

### A8.3 Günstigerprüfung and NV-Bescheinigung

- **Günstigerprüfung** (§ 32d Abs. 6 EStG): on application, all capital income of the year is taxed at the personal income tax rate if that is more favourable. The app always calculates both variants and shows the more favourable one. VERIFIZIERT
- **Tax scale 2026** (§ 32a Abs. 1 EStG), taxable income (zvE) x rounded down to full euros, tax rounded down to full euros:
  - x ≤ 12,348: 0
  - 12,349 ≤ x ≤ 17,799: (914.51 × y + 1,400) × y, y = (x − 12,348) / 10,000
  - 17,800 ≤ x ≤ 69,878: (173.10 × z + 2,397) × z + 1,034.87, z = (x − 17,799) / 10,000
  - 69,879 ≤ x ≤ 277,825: 0.42 × x − 11,135.63
  - from 277,826: 0.45 × x − 19,470.38
  - VERIFIZIERT (research), formula boundaries recalculated twice
- Solidarity surcharge under the income tax scale: exemption threshold of 20,350 € income tax (2026, individual assessment). VERIFIZIERT
- **When it helps:** the marginal tax rate of the scale reaches 25 % at a taxable income of about 20,774 € (2026). For students with low income, taxation at the personal rate is almost always more favourable. VERIFIZIERT (calculation)
- **NV-Bescheinigung** (§ 44a Abs. 2 S. 1 Nr. 2 EStG): prevents tax withholding without any amount limit if, even with the Günstigerprüfung, no tax is expected to arise; valid for at most 3 years, ends on 31 December. **Check in the app:** expected taxable income including capital income (after Teilfreistellung and Sparer-Pauschbetrag) ≤ basic personal allowance (Grundfreibetrag) (2026: 12,348 €; 2025: 12,096 €). Deductions for working students (Werkstudenten) include, among others, the employee lump-sum allowance (Arbeitnehmer-Pauschbetrag) of 1,230 € (§ 9a) and the special-expenses lump-sum allowance (Sonderausgaben-Pauschbetrag) of 36 € (§ 10c). VERIFIZIERT
- **Note:** the NV-Bescheinigung only has an effect at German banks; with foreign brokers, taxation takes place in the tax return

### A8.4 Investment funds (InvStG 2018)

- **Fund types** (§ 2 InvStG): Aktienfonds > 50 % equity participations; mixed funds (Mischfonds) ≥ 25 %; real estate funds (Immobilienfonds) > 50 % real estate. VERIFIZIERT
- **Teilfreistellung** for private investors (§ 20 InvStG): Aktienfonds 30 %, mixed funds 15 %, real estate funds 60 %, foreign real estate funds 80 %; bond, money market and commodity funds 0 %. Applies to distributions, Vorabpauschale and capital gains on disposal. VERIFIZIERT
- **Accumulating vs. distributing:** same taxation system; the difference lies only in the timing (accumulation defers the tax to the sale, to the extent that the return exceeds 70 % of the base rate). VERIFIZIERT
- **Withholding tax at fund level** (e.g. US withholding tax of an Irish fund) is not creditable for the investor; it is compensated on a flat-rate basis via the Teilfreistellung. Withholding tax on the distribution of the fund itself is creditable (cap based on the income after Teilfreistellung). VERIFIZIERT (system and BMF example)

### A8.5 Vorabpauschale (§ 18 InvStG)

- Basic return = redemption price (NAV, not the exchange price) at the beginning of the year × calculation rate, calculation rate = 0.7 × base rate with at least 3 decimal places (BMF Tz. 18.4); for share classes with a NAV in a foreign currency, conversion at the respective ECB rate (Tz. 18.6)
- Basic return capped at: increase in value (price at year end − price at year start) + distributions of the year
- **Vorabpauschale = max(0; capped basic return − distributions)**
- In the year of acquisition: reduction by 1/12 for each full month before the month of acquisition
- Deemed received on the **first working day of the following year** and thus income of the following year; banks book it on the first bank working day (for 2026: 20270104)
- Only for units held at the end of 31 December (BMF Tz. 18.4). VERIFIZIERT
- Rounding: basic return per unit with at least 4 decimal places, commercial rounding to 2 places only after multiplication by the number of units (BMF Tz. 18.4). VERIFIZIERT
- **Base rate:** 2023 2.55 %; 2024 2.29 %; 2025 2.53 %; **2026 3.20 %** (BMF-Schreiben of 20260113); 2027 not yet published. VERIFIZIERT (2025, 2026 from BMF PDF; 2023, 2024 via verbatim quotation)
- **Liquidity note:** for accumulating funds and a German depot (brokerage account), the bank debits the tax on the Vorabpauschale from the settlement account at the beginning of January; the app sends a reminder in December if the exemption order (Freistellungsauftrag) is not sufficient

### A8.6 Sale of fund units

- Gain = proceeds − selling costs − acquisition costs including incidental acquisition costs (FIFO per depot or sub-depot, § 20 Abs. 4 S. 1 and S. 7 EStG; BMF 20250514 Rn. 97–98) − **all Vorabpauschalen recognised during the holding period** (in full, before Teilfreistellung; § 19 Abs. 1 InvStG); Teilfreistellung thereafter. Can produce a loss. VERIFIZIERT
- In the case of foreign custody, earlier Vorabpauschalen are only deducted if they were declared or if the income in those years was within the Sparer-Pauschbetrag (BMF Tz. 19.9). VERIFIZIERT → The app keeps a **Vorabpauschale register** per tranche

### A8.7 Gold

- **Physically backed gold ETCs with an exclusive claim to delivery of, or to the proceeds from, the deposited gold** (Xetra-Gold type): private disposal transactions (private Veräußerungsgeschäfte) under § 23 Abs. 1 S. 1 Nr. 2 EStG, **tax-free after more than one year** of holding; delivery is not a disposal (BFH VIII R 35/14 and VIII R 4/15 of 20150512; IX R 33/17 of 20180206; VIII R 7/17 of 20200616; BMF 20250514 Rn. 57). VERIFIZIERT
- EUWAX Gold II: same classification likely, but no BFH decision of its own found. UNVERIFIZIERT
- Gold certificates that are not deliverable or not backed: capital income under § 20 (Abgeltungsteuer); gold funds: capital income (BFH VIII R 15/18). VERIFIZIERT
- Gains under § 23 remain tax-free if their total in the year is **less than 1,000 €** (exemption threshold, § 23 Abs. 3 S. 5; from assessment period 2024, previously less than 600 €); at 1,000 € or more, the entire gain is taxable. Losses can only be offset against § 23 gains. VERIFIZIERT
- Holding period based on the trade date (Schlusstag) of purchase and sale; calculation of the period according to §§ 187 Abs. 1, 188 Abs. 2 BGB (purchase 20260310 → tax-free from a sale on 20270311). VERIFIZIERT (by the review)
- Tranche order: the law expressly prescribes FIFO for § 23 only for foreign currencies; the app keeps gold tranches individually and uses FIFO as a prudent assumption. UNVERIFIZIERT (administrative view)
- The app shows for each tranche the date from which a sale is tax-free

### A8.8 Direct equities (satellite)

- Dividends from the USA: 15 % withholding tax under the double taxation treaty (DBA) (Art. 10 Abs. 2 lit. b), provided that the W-8BEN form is on file with the broker (otherwise 30 %), creditable up to at most 25 % and up to the German tax on this income; **within the Sparer-Pauschbetrag, the credit is lost** (§ 32d Abs. 5 EStG). VERIFIZIERT
- Losses from share sales can only be offset against gains from share sales (§ 20 Abs. 6 S. 4 EStG; referral to the Federal Constitutional Court 2 BvL 3/21, no decision found as of 20260925). ETF losses go into the general Verlusttopf (loss pot). VERIFIZIERT (rule), UNVERIFIZIERT (status of the proceedings)

### A8.9 German vs. foreign custodian bank

- German bank: tax withholding, Teilfreistellung, exemption order, Verlusttöpfe, loss certificate (Verlustbescheinigung) can be requested until 15 December (§ 43a Abs. 3 EStG). VERIFIZIERT
- Foreign broker (e.g. IBKR): no withholding tax; all income including self-calculated Vorabpauschalen must be declared (§ 32d Abs. 3 EStG; mandatory tax assessment). The app generates an **annual summary for Anlage KAP / KAP-INV**. VERIFIZIERT (rule), UNVERIFIZIERT (behaviour of IBKR)
- **Recommendation for the core portfolio:** German custodian bank, because of automatic tax processing and the exemption order; IBKR optional for trading modules. ENTSCHEIDUNG

### A8.10 Tax-optimised sale order

For each recommended sale, the app calculates per tranche (FIFO per depot or sub-depot is prescribed by law; the choice of product, sub-depot and timing is free):
1. Amount remaining after tax for each sale variant
2. Use of losses and Sparer-Pauschbetrag
3. For gold: postponement if a tranche reaches the one-year period within 60 days and the overlay/rebalancing allows it
4. Proposal of the product or sub-depot whose sale triggers the least tax, provided it corrects the same weight deviation
5. Spreading of non-urgent sales across several tax years in order to use the Sparer-Pauschbetrag and, where applicable, the basic personal allowance in each

### A8.11 After-tax gate for overlays and product switches

- **Overlays (A7):** the backtest is recalculated with realised gains and the tax engine of this section in the user's situation (Sparer-Pauschbetrag, Günstigerprüfung, church tax). The gate uses **the same metric** as before tax (Calmar ratio against the static mix with the same investment ratio, strategy catalogue G7 item 8) and must be passed before **and** after tax
- **Satellite S-Taktik:** as for overlays, with the metric of the respective strategy
- **Product switch:** terminal wealth after tax (A5.6)
- ENTSCHEIDUNG

---

## A9 Projection

### A9.1 Data and method

- **Source:** Jordà-Schularick-Taylor Macrohistory Database (annual data, 18 countries from 1870, total returns on equities and bonds, short-term interest rates, consumer prices, exchange rates; free for non-commercial use, CC BY-NC-SA; last data year UNVERIFIZIERT)
- **Base case: world portfolio.** For each year, a **GDP-weighted world portfolio** for equities, bonds and short-term interest rates is formed from the 18 countries, converted into USD (JST exchange rates) and expressed in real terms using US inflation. This corresponds better to a broadly diversified world index than drawing individual countries, and prevents hyperinflation years of individual countries from shaping the safety building block. Approximation: the perspective is USD-real, not EUR-real; EUR/USD exchange rate effects are not modelled (ENTSCHEIDUNG, explained)
- **Method:** stationary block bootstrap (Politis & Romano, 1994) over the years of the world portfolio, **mean block length 10 years**, circular within the series. Equities, bonds, short-term interest rates and inflation of a given year are drawn **jointly** so that correlations and inflation phases are preserved
- **Stress case "bad country":** block bootstrap within **individual** countries (blocks do not cross country boundaries), including war and hyperinflation years; the 5th percentile is reported
- **Never** a normal distribution alone or US history only: the US sample is flattered by survivorship bias (probability of a real 30-year loss 1.2 % compared with 12 % in 39 countries; Anarkulova et al., 2022). VERIFIZIERT

### A9.2 Centring on conservative assumptions

The real log returns of the world portfolio are shifted per asset class: r'_t = r_t − mean(r) + ln(1 + g), where the mean is taken over the **source sample** (all years of the world portfolio). As a result, g corresponds to the **median geometric real growth rate** (the typical, middle path), not to the arithmetic expected value. At a volatility of around 20 %, the arithmetic expected value is about 2 percentage points higher, and the mean of terminal wealth lies well above the median. **The app therefore labels g everywhere as "median real growth rate"** and does not show a mean of terminal wealth as the headline figure.

| Asset class (real, before costs, geometric) | Pessimistic | Base | Optimistic |
|---|---|---|---|
| World equities | 2 % | 4 % | 6 % |
| Bonds / short-term interest rates | 0 % | 0.5 % | 1.5 % |

- Anchor: world equities real 5.2 % p.a. geometric 1900–2024, bonds 1.7 %, money market 0.5 % (Dimson, Marsh & Staunton, Yearbook 2025); forward-looking estimates of the **risk premium** (arithmetic, over safe assets) are well below the historical one (Fama & French, 2002: 2.55–4.32 % compared with 7.43 % realised; Dimson, Marsh & Staunton, 2003: world 3.5 %). The table is a cautious synthesis: ENTSCHEIDUNG
- Inflation is not shifted (historical distribution), but in A9.3 it serves only for the nominal calculation

### A9.3 Costs and taxes (calculated in nominal terms, then deflated)

- From the real return and the jointly drawn inflation, a **nominal** return is produced for each path: (1 + r_nom) = (1 + r_real) × (1 + π)
- Ongoing costs = TD of the selected product (A5.3), otherwise TER
- **Taxes on the nominal path** using A8: Vorabpauschale annually (cap = nominal increase in value; base rate as a marked assumption: last published value, variant 2 %), Sparer-Pauschbetrag, Teilfreistellung, tax on sale at the end of the target period
- Then conversion back into **today's euros** using the inflation of the path
- Presentation optionally before and after the tax on the sale at the end

### A9.4 Outputs

- **Fan chart** in today's euros: percentiles 5, 10, 25, 50, 75, 90
- Probability of having less than the sum of contributions (real) at the end of the target period
- Largest decline in euros in year 10, 20 and 30 (sequence risk: late declines hit large amounts)
- Probability of reaching a target amount (P8) by the target date
- **Stress scenarios:** "Japan 1990" (20 years at 0 % real, deterministic), "−50 % in year N, then 15 years of recovery" (deterministic), "bad country" (A9.1, 5th percentile)
- Label: "This is how it could turn out, not a forecast"

### A9.5 Reproducibility

10,000 paths, fixed stored seed, data and assumptions version in the result.

---

## A10 Monthly recommendation

On the first day of each month (and on events), the app generates a page with exactly these parts:

1. **Key message in one sentence**, e.g. "Savings plan continues as before, no rebalancing needed."
2. **Concrete actions** (if needed) as a list: product (name, ISIN), amount in €, buy/sell, reason; for sales, the expected tax
3. **Status of the preconditions:** debts, reserve (e.g. "Reserve 2.4 of 3 months")
4. **Portfolio vs. target:** actual and target weights per pot, deviation
5. **Overlay status** (if activated): invested / partly cash, with reason
6. **Tax year:** Sparer-Pauschbetrag used, expected Vorabpauschale in January
7. **Projection in brief:** median and 10th percentile at the target date per pot, change from the previous month
8. **"What has changed"** compared with the previous month
9. **"Why?"** link to rules, evidence and IPS

**Events that trigger a special recommendation:** announcement of the closure or merger of a held product; satellite exceeds its cap by more than 25 %; new base rate; profile change; lump sum; withdrawal request. Weight deviations outside the review date are only displayed (A6.2).

The recommendation is stored with all inputs and is immutable (append-only).

---

## A11 Investment policy statement (IPS)

Elements according to CFA Institute (2010), VERIFIZIERT: purpose and scope; responsibilities and review; return and risk objectives including benchmark; risk tolerance (rational and emotional); constraints (horizon, liquidity, taxes, special considerations such as sustainability); risk management (measurement, rebalancing rules, triggers).

**App additions:** accepted loss in euros; reserve target; monthly savings amount and increase rule; permitted satellites with caps; the commitment "What I do at −50 %" in your own words; annual review date; custodian bank.

- Is created after the profile and confirmed by you (date)
- Changes only with a waiting period (A12)
- Exportable as a Markdown file into the vault

---

## A12 Behavioural guardrails

| Guardrail | Rule | Evidence |
|---|---|---|
| View | Depot value shown quarterly or annually by default instead of daily | Frequent evaluation amplifies myopic loss aversion and leads to less risky investment decisions (Gneezy & Potters, 1997; Thaler et al., 1997; not re-checked) |
| Selling in a drawdown | Selling core positions during a decline of > 20 % from the peak first shows your own IPS commitment and the recovery times from A3.1 | Disposition effect, overreaction (Odean, 1998; Guiso et al., 2018) |
| Waiting period | Deviation from the IPS (lowering the share, selling the core) can only be confirmed after 72 hours | No direct evidence found; ENTSCHEIDUNG |
| Frequency | Warning at more than 4 manual transactions per month in the core portfolio (savings plan executions do not count) | Overtrading is costly (Barber & Odean, 2000: most active fifth 11.4 % net compared with 17.9 % market return) |
| Performance chasing | Notice when a satellite is to be topped up after a strong preceding period | Return gap caused by entries and exits (Dichev, 2007) |
| Review | Annual review: what would "doing nothing" have produced? | ENTSCHEIDUNG |

---

## A13 Retirement provision notes (informative)

- **Altersvorsorgedepot** (retirement provision depot) (Altersvorsorgereformgesetz, passed by the Bundestag on 20260327, Bundesrat 20260508; products from **20270101**): subsidised depot without a guarantee requirement; allowance of 50 % on contributions up to 360 € and 25 % on contributions from 360.01 to 1,800 € (basic allowance at most 540 €); **one-off career starter bonus of 200 € for contracts concluded before the 25th birthday**; cost cap for the standard product 1.0 %; no taxation of fund income within the contract (§ 16 Abs. 2 InvStG), but taxation of the payouts instead. VERIFIZIERT (official summaries; statutory text, eligibility of students and details UNVERIFIZIERT)
- Once available, the app shows a comparison: subsidised Altersvorsorgedepot vs. free depot for the pot "retirement provision" (allowance, costs, after tax at payout, restricted availability)
- **Occupational pension via salary conversion (Entgeltumwandlung)** for working students: with income below the basic personal allowance hardly any tax saving, later taxation of the payout; usually unattractive. The app shows the calculation but recommends nothing without review. VERIFIZIERT (limits § 1a BetrAVG, § 3 Nr. 63 EStG), social security status UNVERIFIZIERT
- **Frühstart-Rente** (early-start pension): only a cabinet draft, concerns children aged 6 to 18, not relevant for you

---

## A14 Tests

| No. | Test | Inputs | Expected |
|---|---|---|---|
| TA1 | Total tax rate | k = 0 / 0.08 / 0.09 | 26.3750 % / 27.8186 % / 27.9951 % |
| TA2 | Vorabpauschale, basic case | 10,000 → 11,000, no distribution, base rate 3.20 %, purchase in January | 224.00 €; taxable after Teilfreistellung 156.80 €; without Sparer-Pauschbetrag 39.20 € + SolZ 2.15 € = 41.35 €; with Sparer-Pauschbetrag 0 € |
| TA3 | Cap | 10,000 → 10,100 | 100.00 € |
| TA4 | Loss year | 10,000 → 9,000 | 0 € |
| TA5 | Distributing fund | 10,000 → 10,800, distribution 150 € | 74.00 € |
| TA6 | Acquisition in March | as TA2, purchase 15 March | 186.67 € |
| TA7 | BMF example | base rate 1 %, price 100 → 100.50, distribution 0.10; purchase 10 July | 0.50 per unit for a full year; 0.25 with the purchase on 10 July |
| TA8 | Sale after Vorabpauschale | TA2, sale 20270630 at 12,000, without transaction costs | Gain 1,776.00 €; after Teilfreistellung 1,243.20 €; total capital income 2027 1,400.00 € (= 70 % × 2,000); **tax assessment** without Sparer-Pauschbetrag: 350.00 € + SolZ 19.25 € = 369.25 €; **bank withholding in two transactions** (Vorabpauschale, sale): SolZ 2.15 € + 17.09 € = 19.24 €; with Sparer-Pauschbetrag (tax assessment) 100.00 € + 5.50 € = 105.50 € |
| TA9 | Tax scale 2026 | zvE 12,348 / 15,000 / 20,000 / 30,000 | 0 / 435 / 1,570 / 4,217 € |
| TA10 | Günstigerprüfung | Marginal tax rate at 20,774 € | ≈ 25 % |
| TA11 | Gold holding period and exemption threshold | Purchase 20260310, sale 20270310 or 20270311; annual § 23 gain of 999.99 € or 1,000.00 € | taxable or tax-free respectively; 999.99 € tax-free, 1,000.00 € fully taxable |
| TA12 | Equity share | Horizon 20 yrs, stable income, L€ sufficient | 100 %; with fluctuating income 70 %; horizon 7 yrs: q_Horizont = 60 + (7 − 5)/5 × 20 = 68 % → rounded down 60 % |
| TA12b | Tolerance across two pots | Pots A (h 20 yrs, B5 10,000 €) and B (h 2 yrs, B5 10,000 €), L€ 5,000 €, D_Stress 0.5 | q_Tol,A = min(1; 5,000/5,000) = 100 %, remaining budget 0; q_Tol,B = 0 % (horizon limit at 2 yrs is 15 % anyway) |
| TA12c | Tolerance without a depot | Σ B5 < 1,000 € | Tolerance limit does not apply, notice appears |
| TA13 | Cash-flow rebalancing | w = (0.8; 0.2), V = (9,000; 1,000), C = 500 | T = (8,400; 2,100), F = (0; 1,100), x = (0; 500) |
| TA14 | Cash flow with a small shortfall | w = (0.8; 0.2), V = (8,000; 1,950), C = 500 | T = (8,360; 2,090), F = (360; 140), Σ F = 500, x = (360; 140) |
| TA14b | Minimum amount | as TA14, minimum amount 150 € | Month 1: x = (500; 0), open entitlement of building block 2: 140 €; payout as soon as entitlement + x ≥ 150 € |
| TA14c | No contribution | C = 0, portfolio exactly on target | x = (0; 0), no division by zero |
| TA15 | Preconditions | Overdraft (Dispo) 12 %; reserve 1.5 of 3 months | V1 applies; after repayment V3: 50/50 |
| TA16 | ETF scoring | Synthetic candidates with known metrics | Ranking and point scores exactly as calculated by hand; hard filters exclude funds that are too small and too young |
| TA17 | Projection | Fixed seed | Identical percentiles on repetition; mean of the centred log returns **of the source sample** = ln(1.04) ± 10⁻¹²; median of real terminal wealth of a lump-sum investment over 30 years without costs and taxes close to 1.04³⁰ (tolerance from Monte Carlo error) |
| TA18 | After-tax gate | Overlay with a pre-tax advantage of 0.3 % p.a., but annual realisation of gains | Gate fails if the after-tax advantage ≤ 0 |
| TA19 | Look-ahead | Truncation and perturbation test for ETF metrics (as-of date), base rate (publication), projection inputs | No change up to t |
| TA20 | ETF scales | TD −0.10 / −0.11 / +0.20 pp | After rounding to 0.05: −0.10 / −0.10 / +0.20 → 25 / 25 / 100 points |
| TA21 | Product switch | Old fund TD −0.30, new TD 0.00, gain realisable tax-free within the Sparer-Pauschbetrag | Switch recommended; the same case with a taxable gain and 3 years of remaining horizon: no switch |
| TA22 | Glide path shortly before the target | Pot with target date 20290930, q_p = 30 % on 20260930, depot 10,000 €, monthly savings amount 100 € | Step to 20 % due as soon as q_Horizont < 30 % (from 20261001); quarterly review 20261231 recommends a sale of around 1,000 € (savings amounts of 300 € are not sufficient); q_p = 0 implemented by 20280930 at the latest; the annual profile hysteresis does not delay any of these steps |
| TA23 | Hurdle rate, base case | r = 6 %, Teilfreistellung 30 %, k = 0 | 4.8923 % (Decimal, A8 rounding); a loan at 4.5 % is below the hurdle, a loan at 5.5 % above it |
| TA24 | Hurdle rate reacts to the tax parameters | as TA23, but k = 9 % and separately Teilfreistellung 0 % | Hurdle changes in both cases and is read from the tax engine, not from a constant: k = 9 % lowers it, Teilfreistellung 0 % lowers it further |
| TA25 | Fixed-rate property loan inside the fixed-rate period | P18 set, fixed rate, Sondertilgung allowance 0 | V5: overpayment not available, A2.6 not applied; the monthly amount follows V3/V4 |
| TA26 | Variable-rate property loan | P18 set, variable rate, Sollzinssatz 7 % | § 500 Abs. 2 Satz 1: overpayment available; above the hurdle → repayment before investing |
| TA27 | § 489 date after renegotiation | Full receipt 20180301, rate renegotiated 20230601 | Earliest termination date computed from 20230601, not from 20180301; notice period six months |

All tax tests with `Decimal`; values TA1–TA10 were recalculated twice independently.

---

## A15 Open points

| Point | When to clarify |
|---|---|
| Confirm the unit of k in § 32d Abs. 1 S. 4 EStG in the statutory text | Before A8 |
| Usage rights for the Grable-Lytton scale | Before A1 |
| Licence terms for delayed price data from Deutsche Börse; terms of use of DWS, Amundi, SPDR, OpenFIGI | Phase 1 |
| JST database: last data year, licence for private use | Phase 1 |
| Withholding tax of German and Luxembourg funds on US dividends | Before A5 |
| Classification of EUWAX Gold II under § 23 | Before recommending S-Gold |
| Altersvorsorgedepot: statutory text, eligibility of students | Before 2027 |
| Status of BVerfG 2 BvL 3/21 (Aktienverlusttopf) | Annually |
| Limits of family insurance (§ 10 SGB V) and BAföG asset allowance | Before A6.3 |
| Calibration of D_Stress from the JST world portfolio (placeholder 0.60) | Phase 1 |
| Tranche order under § 23 (administrative view) | Before recommending S-Gold |
| Review overlay variants OV-L2, OV-L4 (registered in strategy catalogue v1.2) | Phase 3 |
| Whether a "berechtigtes Interesse" under § 500 Abs. 2 Satz 2 BGB covers a sale of the property, and what the app may say about it without giving legal advice (A2.7) | Before A2.7 |
| Base rate 2027 | January 2027 |
| Rate for a fund size whose as-of date has no ECB reference rate: **closed in v1.6** — carry forward only across actual TARGET closing days; any missing business day is a data gap and is reported as an error (A5.1) | — |
| Fund size of the fund or of the share class (A5.2 no. 3) | Before A5 |
| Aliases per A5.5 building block, read from the KID or factsheet of each real candidate: the exact index name, its return variant, and for global bonds the hedging tag | Before filter 2 can return fulfilled for any building block; until then its candidates stay open (A5.2 on 2, status) |
| KID precedence (A5.1) against documents other than the factsheet: **closed in v1.6** — replaced by a precedence over eight document classes, STATUTE before KID before ANNUAL_REPORT before PROSPECTUS before FACTSHEET before ISSUER before EXCHANGE before SECONDARY | — |
| Whether a VERIFIED value should beat an UNVERIFIED one **within the same document class**. Deliberately not done in v1.6: it would make dependent checks pass more often rather than less (A5.1) | Before the candidate list is filled with real data |

---

## Changelog

**v1.7 (20260925)** Filter 2 made data-driven, and two errors in A5.5 corrected by pulling the real documents. **Matching** (A5.2 on 2): the exact comparison against the A5.5 spelling was a false-rejection machine — the real spellings `MSCI ACWI Index (Net)` and `ESTR Compounded` came out as *violated*, which also affected K1 and K2 money market, the two building blocks considered implemented. The name is now normalised (case, `€STR`/`ESTR`, trailing `Index`, return-variant and currency/hedging suffixes) and matched against a canonical name plus aliases registered per building block; the return variant and the hedging tag are extracted into their own fields instead of being dropped, because they are separate checks. Everything that changes the constituent set — `Sector Neutral`, `ESG`, `Screened`, maturity bands, region qualifiers — is never normalised away, so a differently-composed index still fails. An unknown name stays **open** with the normalised form in the reason, never a guessed match. **S-Factor corrected** (A5.5): v1.4 named *MSCI World Quality* (MSCI 702787), but the real products track *MSCI World Sector Neutral Quality* (MSCI 705169) — a different index, applying the same three criteria within each GICS sector. The v1.4 selection criteria match the sector-neutral variant, so only the name was wrong; the products are named "Quality Factor" while their benchmark is not, which is the likely source. **€STR clarified** (A5.5): €STR is the ECB's overnight rate, not an investable index; funds track a derived compounded or swap series, which matches only as a registered alias. Aliases are data, not code: each is recorded with its document class and as-of date, so until a building block has an alias read from a real document, its candidates stay open rather than violated. The leads gathered so far are UNVERIFIZIERT in `20260925_filter2-datenbedarf.md`. Not yet independently reviewed

**v1.6 (20260925)** Two open points closed and implemented in the same version. **Precedence by document class** (A5.1): the v1.4 rule "KID before everything" put an audited annual report behind a possibly stale KID, so precedence now runs over eight classes — STATUTE, KID, ANNUAL_REPORT, PROSPECTUS, FACTSHEET, ISSUER, EXCHANGE, SECONDARY — with as-of date, retrieval and write order deciding only within a class. STATUTE ranks above KID so that no document describing the law can override the statutory text itself. The order is defined once in the code and the SQL is generated from it, so an unclassified source type fails the tests instead of silently sorting last. Deliberately *not* done: letting a VERIFIED value beat an UNVERIFIED one, which would make checks pass more often rather than less; this is now a separate open point. **TARGET calendar** (A5.1, A5.2 on 3): the v1.5 carry-forward rule could not tell a holiday from a data gap and would convert at a rate weeks too old. Carry-forward is now allowed only across actual TARGET closing days — Saturdays, Sundays and six days, New Year's Day, Good Friday, Easter Monday, 1 May, 25 and 26 December — with Easter computed rather than tabulated, so the calendar does not expire. Ascension Day, Whit Monday, Corpus Christi, Day of German Unity, All Saints' Day, 24 and 31 December are ECB staff holidays but **not** TARGET closings; rates are published on those days. Any missing TARGET business day is reported as a data gap naming the length; the hard filter then stays open with that reason. Status corrections: the currency conversion (v1.4) and the age measure were marked "not yet implemented" although they had been; filter 2 for the four v1.4 starting indices remains genuinely unimplemented and is blocked on the index spellings, not on code. Not yet independently reviewed

**v1.5 (20260925)** Financing guide and small financing adviser as an extension of A2, not as a new module. New: A2.5 (why the order of finances is what it is, explanatory, no computation), A2.6 (the hurdle rate — repayment is compared against the **after-tax** expected return 4.8923 %, recomputed from the tax engine, which is where V1's 5 % threshold now comes from instead of being a bare number), A2.7 (property loans behind toggle P18, off by default). Two statutory rules: V5 § 500 Abs. 2 BGB (a fixed-rate Immobiliar-Verbraucherdarlehen generally cannot be overpaid during the fixed-rate period), V6 § 489 Abs. 1 Nr. 2 BGB (penalty-free termination ten years after full receipt with six months' notice; a renegotiation restarts the ten years, so the anchor date is stored as its own field). Both read from the statutory text. New profile field P18, tests TA23–TA27. BAföG is explicitly excluded as a product to advise on; the § 18 Abs. 10 Satz 2 BAföG discount is out of scope. Decided: a missing ECB rate carries the last published rate forward, as in strategy catalogue G4. New open point on "berechtigtes Interesse". Nothing of this is implemented yet. Not yet independently reviewed

**v1.4 (20260925)** The English text becomes binding; the German original of v1.3 moves to `archive/20260925_anlage-spezifikation.md` and is no longer binding. German tax and legal terms (Vorabpauschale, Teilfreistellung, Günstigerprüfung, NV-Bescheinigung, Abgeltungsteuer, Sparer-Pauschbetrag, Verlusttöpfe, Aktienfonds, all § references) stay as proper nouns. Strings shown to the user are English. Vocabulary matches the code: S-Factor; hard-filter verdicts fulfilled / violated / open; eligible; label "new"; per-value status VERIFIED / UNVERIFIED. Decisions: starting indices for K2 EUR government bonds, K2 global bonds, S-Gold and S-Factor (A5.5, A5.2 on 2); history score in full calendar years (A5.3); fund size converted at the ECB reference rate of the value's own as-of date (A5.1, A5.2 on 3); KID before factsheet (A5.1). Implementation status: the currency conversion, the KID precedence and filter 2 for the new starting indices are not yet in the code. Editorial: TA7 states which value belongs to which case; "open entitlement" used throughout. Not yet independently reviewed

**v1.3 (20260925)** Instrument master data layer: A5.1 extended by time axes, precedence and verification status per value; A5.2 extended by the three-valued evaluation (fulfilled / violated / open) and clarifications on filters 1, 2, 4, 5, 6 and 7. Not yet independently reviewed

**v1.2 (20260925)** Self-review on filing: the annual hysteresis (A3.3 item 6) applied, according to its wording, to q_p as a whole and would have delayed the glide path reduction in the final years before the target by up to one year → now applies only to tolerance and capacity; q_Horizont monthly; new glide path rule for the last 36 months (A6.2) with test TA22; justification in A3.1 adjusted to the 10-percentage-point rounding; test table sorted

**v1.1 (20260925)** after independent review (2 critical, 10 major, 11 minor findings; all test values TA1–TA14 and the 2026 tax scale including z = (x − 17,799)/10,000 confirmed):
- Critical: tolerance limit was circular and undefined for new investors → B5 deterministic at q = 100 %, lower limit 1,000 €, loss budget across all pots (longest horizon first), annual recalculation with hysteresis
- Critical: projection incorrectly specified → g is the median geometric rate (median), labelled as such; taxes on nominal paths with jointly drawn inflation; world portfolio instead of individual countries in the base case, individual countries only in the stress case; annual data, block length 10 years; test related to the source sample
- Major: FIFO per depot or sub-depot, one sub-depot per pot; gain realisation with BFH basis, basic personal allowance headroom, discounting, side effects on BAföG and family insurance; overlays as separately registered variants only on K1 (L3, S1 as satellite); linear glide path; product switch based on terminal wealth after tax; fixed scoring scales with materiality threshold, comparison only within one index, own index choice; D_Stress placeholder 0.60; cash-flow algorithm cleaned up (zero case, minimum amount with open entitlement, standing order); rebalancing only on the review date with band min(5 pp; 25 %); satellite limit uniformly relative to q
- Minor: unit of k derived; gold exemption threshold "less than 1,000 €" from 2024, holding period under the BGB confirmed, wording of the delivery claim; Vorabpauschale with NAV, calculation rate, reference date 31 December verified; selling costs; bank withholding vs. tax assessment for the SolZ; reserve target ≥ starter reserve; classification of the loss probabilities and of the Japan example; realistic equity share at the start; transaction warning excluding savings plans; evidence on viewing frequency; W-8BEN; citations corrected (Bessembinder 57 %, Barber & Odean, Grable-Lytton retrospective, Anarkulova versions)

---

## Sources

**Statutes and administration**
- Einkommensteuergesetz (EStG), §§ 9a, 10c, 20, 23, 32a, 32d, 43a, 44a, 52. https://www.gesetze-im-internet.de/estg/
- Investmentsteuergesetz 2018 (InvStG), §§ 2, 16, 18, 19, 20. https://www.gesetze-im-internet.de/invstg_2018/
- Solidaritätszuschlaggesetz (SolZG), §§ 3, 4.
- Bundesministerium der Finanzen. (20250514). *Einzelfragen zur Abgeltungsteuer* (IV C 1 - S 2252/00075/016/070).
- Bundesministerium der Finanzen. (20190521, last amended 20251124). *Anwendungsfragen zum Investmentsteuergesetz*.
- Bundesministerium der Finanzen. (20250110; 20260113). *Basiszins zur Berechnung der Vorabpauschale gemäß § 18 Absatz 4 InvStG*.
- Bundesfinanzhof: VIII R 35/14 and VIII R 4/15 (20150512); IX R 33/17 (20180206); VIII R 7/17 (20200616); VIII R 15/18 (20210412); IX R 60/07 (20090825).
- ESMA. (2023). *Guidelines on certain aspects of the MiFID II suitability requirements* (ESMA35-43-3172).
- Directive 2009/65/EC (UCITS), Art. 52.
- Bundesregierung. (20260601). *Reform der privaten Altersvorsorge*. https://www.bundesregierung.de/breg-de/aktuelles/reform-private-altersvorsorge-2400072

**Literature**
- Anarkulova, A., Cederburg, S., & O'Doherty, M. S. (2022). Stocks for the long run? Evidence from a broad sample of developed markets. *Journal of Financial Economics, 143*(1), 409–433.
- Anarkulova, A., Cederburg, S., & O'Doherty, M. S. (2023, revised 20260903). *Beyond the status quo: A critical assessment of lifecycle investment advice* [Working paper]. SSRN 4590406.
- Barber, B. M., & Odean, T. (2000). Trading is hazardous to your wealth. *Journal of Finance, 55*(2), 773–806.
- Benartzi, S., & Thaler, R. H. (2004). Save More Tomorrow. *Journal of Political Economy, 112*(S1), S164–S187.
- Bessembinder, H. (2018). Do stocks outperform Treasury bills? *Journal of Financial Economics, 129*(3), 440–457.
- CFA Institute. (2010). *Elements of an investment policy statement for individual investors*.
- Cocco, J. F., Gomes, F. J., & Maenhout, P. J. (2005). Consumption and portfolio choice over the life cycle. *Review of Financial Studies, 18*(2), 491–533.
- Constantinides, G. M. (1979). A note on the suboptimality of dollar-cost averaging as an investment policy. *Journal of Financial and Quantitative Analysis, 14*(2), 443–450.
- Dichev, I. D. (2007). What are stock investors' actual historical returns? *American Economic Review, 97*(1), 386–401.
- Dimson, E., Marsh, P., & Staunton, M. (2003). Global evidence on the equity risk premium. *Journal of Applied Corporate Finance, 15*(4), 27–38.
- Dimson, E., Marsh, P., & Staunton, M. (2025). *UBS Global Investment Returns Yearbook 2025* [summary].
- Erb, C. B., & Harvey, C. R. (2013). The golden dilemma. *Financial Analysts Journal, 69*(4), 10–42.
- Fama, E. F., & French, K. R. (2002). The equity premium. *Journal of Finance, 57*(2), 637–659.
- French, K. R., & Poterba, J. M. (1991). Investor diversification and international equity markets. *American Economic Review, 81*(2), 222–226.
- Gneezy, U., & Potters, J. (1997). An experiment on risk taking and evaluation periods. *Quarterly Journal of Economics, 112*(2), 631–645. (Not re-checked.)
- Grable, J. E., & Lytton, R. H. (1999). Financial risk tolerance revisited: The development of a risk assessment instrument. *Financial Services Review, 8*(3), 163–181.
- Kuzniak, S., Rabbani, A., Heo, W., Ruiz-Menjivar, J., & Grable, J. E. (2015). The Grable and Lytton risk-tolerance scale: A 15-year retrospective. *Financial Services Review, 24*(2), 177–192. (Author list not re-checked.)
- Guiso, L., Sapienza, P., & Zingales, L. (2018). Time varying risk aversion. *Journal of Financial Economics, 128*(3), 403–421.
- Hou, K., Xue, C., & Zhang, L. (2020). Replicating anomalies. *Review of Financial Studies, 33*(5), 2019–2133.
- Huang, S., Song, Y., & Xiang, H. The smart beta mirage. *Journal of Financial and Quantitative Analysis.* (Year and volume to be checked.)
- Klement, J. (2015). Investor risk profiling: An overview. *CFA Institute Research Foundation Briefs, 1*(1).
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Novy-Marx, R. (2013). The other side of value: The gross profitability premium. *Journal of Financial Economics, 108*(1), 1–28.
- Odean, T. (1998). Are investors reluctant to realize their losses? *Journal of Finance, 53*(5), 1775–1798.
- Thaler, R. H., Tversky, A., Kahneman, D., & Schwartz, A. (1997). The effect of myopia and loss aversion on risk taking: An experimental test. *Quarterly Journal of Economics, 112*(2), 647–661. (Not re-checked.)
- Politis, D. N., & Romano, J. P. (1994). The stationary bootstrap. *Journal of the American Statistical Association, 89*(428), 1303–1313.

**Industry and data sources (not peer-reviewed evidence, flagged as such)**
- Jaconetti, C. M., Kinniry, F. M., & Zilbering, Y. (2010). *Best practices for portfolio rebalancing*. Vanguard.
- Shtekhman, A., Tasopoulos, C., & Wimmer, B. (2012). *Dollar-cost averaging just means taking risk later*. Vanguard.
- Vanguard. (2021). *Global equity investing: The benefits of diversification and sizing your allocation*.
- Vanguard. (2022). *Rational rebalancing*.
- Vanguard. (2026). *Currency hedging whitepaper*.
- Morningstar. (20240110). *ETF tracking difference and tracking error*.
- MSCI, FTSE Russell: index factsheets, as of 20260831. iShares Core MSCI World: factsheet, as of 20260831.
- justETF: general terms and conditions (as of 20250618).
- Deutsche Börse: Xetra Liquidity Measure; MiFIR publications of delayed data.
- Jordà-Schularick-Taylor Macrohistory Database. https://www.macrohistory.net/
- Index and reference-rate providers named in A5.1 and A5.5 by the v1.4 decisions; their methodology documents have not been read for this specification: FTSE Russell (FTSE EMU Government Bond Index), Bloomberg (Bloomberg Global Aggregate), ICE Benchmark Administration and LBMA (LBMA Gold Price PM), MSCI (MSCI World Sector Neutral Quality), European Central Bank (euro foreign exchange reference rates and €STR). Exception (v1.7): the EGBI factsheet of FTSE Russell was read for the maturity-band names, and the MSCI index pages for the S-Factor correction; both are recorded as UNVERIFIZIERT leads in `20260925_filter2-datenbedarf.md`, not as verified values

