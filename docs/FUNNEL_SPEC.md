# The Quality Dislocation Funnel

**Vantage · Funnel Spec v0.8 · 29 Aug 2026**

Find durably excellent companies, wait for one of them to be temporarily
marked down, and check that the markdown is sentiment rather than damage.
Three stages, every calculation stated in full.

> **This document is the single source of truth for Vantage.** Anything
> that disagrees with it — code comment, README, chat history — is wrong
> until this file is changed. See [CONTRIBUTING.md](../CONTRIBUTING.md)
> for what may and may not enter this repository.

## What this version is

Stage 1 is built and running against live SEC EDGAR filings, with a
17-company regression test that currently passes. Stages 2 and 3 are
specified here but not yet implemented. Nothing is deployed.

Corrections forced by real data: the original returns bar excluded Amazon
and Costco; the margin test was unrunnable on 13 of the 20 largest
companies; the solvency test had data for only 27% of the index;
Berkshire failed on a mark-to-market accounting artefact; Mastercard was
about to be scored on 2013 figures; and Exxon's entire history was
invisible because a 2025 reorganisation moved it to a different filer ID.
Each is documented below with the measurement that caught it.

### Version history

| Version | Date | What changed |
|---|---|---|
| **v0.8** | 29 Aug 2026 | Shock-year rule tightened: a company counts only if it was **profitable the year before**, so a loss must be specific to that year. Stops chronic loss-makers standing in as evidence of an industry-wide event, which had made Industrials 2020 fire spuriously. Only Energy 2020 fires. |
| v0.7 | 29 Aug 2026 | Health insurers routed to the financials track. Financials' Gate 1 falls back to net income where no operating-income series is filed. Unassessable companies 36 → 29; eligible 238 of 500 (48%). **Ported into the Vantage repository as its source of truth; section 6 reduced to UI principles only — the detailed interface spec is now a separate document, written after Stage 3.** |
| v0.6 | 29 Aug 2026 | Capital-intensive track (telecom/cable/media, ROE 10%) and the sector shock-year rule. Energy 5→10 and Comm Services 4→10 eligible. Full-500: 230 of 500 (46%) eligible. |
| v0.5 | 29 Aug 2026 | Utilities track added (ROE 8%, operating cash flow replaces FCF, coverage 2.5×) — utilities went from 1/31 to 17/31 eligible. Canonical per-track gate table added. Full-500: 219 of 500 (44%). |
| v0.4 | 29 Aug 2026 | Four-way grading (pass / near-pass / near-fail / fail) with a 15% proportional band. Watchlist tiers and the exceptions mechanism. First full-500 run: 203 eligible. |
| v0.3 | 28 Aug 2026 | Gates rebuilt after live validation: ROIC → return on assets with an improvement clause, gross → operating margin, coverage-first solvency. Financials track (ROE). Golden set established. |
| v0.2 | 28 Aug 2026 | Scoped to S&P 500. Tag-coverage audit across all 500. Institutional ownership tested and rejected; volume and short interest adopted. |
| v0.1 | 28 Aug 2026 | Initial three-stage funnel concept, thresholds proposed from sampled distributions. |

Versions stay below 1.0 until Stages 2 and 3 are implemented.

---

## 1. The thesis

The goal is not to rank 500 stocks by an upside number. It is to maintain
a small, slow-changing watchlist of companies worth owning, and to be
told when one of them goes on sale for a reason that isn't deterioration.

Quality is not a factor to be traded off against cheapness. It is a
precondition. A mediocre company that has fallen a long way must never
outrank an excellent one that has fallen a little.

```
STAGE 1 — QUALITY GATE          hard pass/fail
500 S&P constituents  ->  238 that clear every bar
Recomputed quarterly, on filings.
        |
        v
STAGE 2 — DISLOCATION           0-100 score
How far below its own normal trading range is each one today?
Recomputed daily, on prices.
        |
        v
STAGE 3 — CHEAP OR BROKEN       verdict + score
For the dislocated ones only: does the evidence say sentiment, or damage?
Daily.
```

Stage 1 answers *"would I ever own this?"* Stage 2 answers *"is it on
sale?"* Stage 3 answers *"is the sale real?"* Only a company passing all
three is worth attention, and the interface must say so in that order.

This is buy-and-hold accumulation, not dip trading.

---

## 2. Universe and data sources

**Universe: the S&P 500.** Chosen because index membership is itself a
quality screen that cannot be reproduced from filings — inclusion
requires positive GAAP earnings in the most recent quarter and across the
trailing four quarters, plus liquidity, float and size minimums, with a
committee actively removing companies that deteriorate. Turnover is
~20–25 names a year, which is the stability a low-churn watchlist needs.

Deliberately **not** the full 10,391-entity EDGAR ticker map: sampling it
returns OTC shells, warrants, foreign ADRs and pink-sheet miners. It is
every SEC filer, not an investable universe. The universe must remain a
swappable input, never hard-coded.

### Deferred, not dismissed — screening every US filer is feasible

EDGAR's `frames` endpoint returns one financial concept for *every* filer
in a single call — net income for CY2024 came back as 6,051 companies in
0.9 MB in 0.3 seconds. Stage 1 across all US filers would cost roughly 40
API calls, less work than a single 500-ticker price scan. A live test of
Gate 1 alone cut 6,051 filers to 1,386 — a 77% reduction before any other
gate.

So the constraint is not Stage 1. It is that Stage 3's strongest signal —
analyst conviction trend — thins out below large caps, where a company
may have two analysts or none. Starting with the S&P 500 keeps every
stage fully powered while the funnel is proven. Widening later is a
configuration change plus a liquidity gate and an "insufficient coverage"
state in Stage 3, not a rewrite.

### Sources

| Source | Used for | Cost | Why this one |
|---|---|---|---|
| SEC EDGAR XBRL API | Stage 1 fundamentals; Stage 3 trend checks | Free, no key | Audited, as-filed, multi-year. The primary source every aggregator derives from. Verified: returns 6+ years of annual figures per concept. |
| yfinance | Prices, 52-week range, analyst targets and ratings | Free | Fine for prices; not trusted for fundamentals where EDGAR exists. |
| Finnhub | Stage 3: estimate revisions | Free, 60/min | Only if EDGAR plus analyst trend prove insufficient. Transcripts are paid — out of scope for v1. |

Rate limits matter: FMP's 250/day and Alpha Vantage's 25/day cannot cover
500 tickers. EDGAR and Finnhub can.

SEC requires a contact address on every request. It comes from the
`SEC_USER_AGENT` environment variable and is **never** hard-coded.

---

## 3. Stage 1 — the quality gate

Six tests. A company must clear all of them — no scoring, no
compensating: weak margins are not offset by a clean balance sheet.

### 3.1 The exact tests, by track

Canonical reference. Implemented in [`funnel/stage1.py`](../funnel/stage1.py);
read the code, not a summary of it.

| Gate | Standard · ~336 | Financials · 82 | Utilities · 31 | Capital-intensive · 21 (telecom, cable, media) |
|---|---|---|---|---|
| **1 · Sustained profit** | Operating income positive in every one of the last 5 years, **and** net income positive in at least 4 of 5 | Same, but one negative operating year allowed; falls back to net income where no operating-income series is filed | Same as standard | Same as standard |
| **2 · Return on capital** | Median 5y return on **assets** ≥ 8% | Median 5y return on **equity** ≥ 10% | Median 5y return on **equity** ≥ 8% | Median 5y return on **equity** ≥ 10% |
| | …or latest ≥ (bar − 1 point) **and** above its own median — the improvement clause, universal to all tracks. This is what admits Amazon. | | | |
| **3 · Cash generation** | Sum of (operating cash flow − capex) over 5 years > 0 | Same as standard | Operating cash flow positive every year — capex excluded entirely | Same as standard |
| **4 · Debt serviceable** | Coverage ≥ 4×, fallback equity/assets ≥ 10% | Coverage ≥ 4×, fallback ≥ 8% | Coverage ≥ 2.5×, fallback ≥ 10% | Same as standard |
| **5 · Margin durable** | Latest operating margin ≥ 70% of its trailing 3-year average | Same | Same | Same |
| **6 · Liquidity** | Median daily dollar volume ≥ $25M | Same | Same | Same |

Sector-wide shock years are excluded from Gate 1 on **every** track.

Four sector-specific values in total, across three gates. Everything else
is universal.

```
return on assets  = operating income x 0.79 / total assets
return on equity  = net income / stockholders' equity
operating margin  = operating income / revenue
```

Two points that are easy to misread. The "or improving" clause in Gate 2
applies to **all** tracks, not just the standard one — it is what admits
Amazon (median 5.5% return on assets, latest 8.7% and rising). And the
one-loss-year allowance in Gate 1 is **financials only**: utilities get
the strict version, which is why AES and PG&E are still rejected.

### 3.2 The rule for when a sector may have its own track

> **Adjusting the *metric* to fit a business model is legitimate.
> Adjusting the *bar* to fit a sector's average quality is not.**

A bank's assets are its business, so return on assets misreads it — that
is mechanical, and earns a track. "Companies in this sector score lower"
does not. The alternative, ranking within sector, can never conclude that
a sector isn't worth owning — which is precisely what an absolute-quality
screen exists to be able to say.

### 3.3 Sector-wide shock years

Where at least half of a sector's ten largest companies are **knocked
into** an operating loss in the same year — having been profitable the
year before — that year is excluded from Gate 1 for every company in that
sector.

```
Energy — share of the largest names with negative operating income:
  2019  12%
  2020  71%   <-- sector-wide shock, year excluded
  2021   0%    2022  0%    2023  0%    2024  0%
```

A single-year spike with zero either side is the signature of an
exogenous event, not deterioration. This is mechanical — it identifies
that a *year* was industry-wide — rather than a lowered bar, and it is
self-limiting: nine energy names still fail on their own record even with
2020 excused.

**Why the prior-year condition is load-bearing.** An earlier version
counted *any* loss in the year, and that let chronically unprofitable
companies stand in as evidence of an industry-wide event — exactly
backwards, since a company that loses money every year says nothing about
whether one particular year was exceptional. Measured:

```
share of the ten largest posting an operating loss
                     2019    2020    2021
Energy                10%     77%      0%    <- spike
Industrials           20%     50%     30%    <- plateau
```

Industrials 2020 tripped the old rule at exactly the 50% threshold,
carried there by Boeing and DuPont, which were losing money either side
of 2020 as well. Requiring a profitable prior year drops Industrials 2020
to 30% (does not fire) while Energy 2020 holds at 67% (still fires). Only
Energy 2020 fires across the index.

A company is counted only where figures exist for **both** the year and
the year before, so one with a gap is left out of the numerator and the
denominator alike rather than silently diluting the share.

Sector size is ranked on **total assets**, which Stage 1 already loads
from EDGAR, rather than market capitalisation. That avoids a second data
source for one ranking, and balance-sheet size is the more appropriate
measure of "one of this sector's big names" anyway.

The shock window is the same five years the gates judge on. An earlier
draft used six, which meant the rule could excuse a year the gates never
looked at — an inconsistency with no justification.

### 3.4 How a result is graded

Each gate returns a **margin**, not a boolean. A company clearing a bar by
a hair is materially different from one clearing it by triple, and one
missing by a hair is different from one missing by half. Boolean logic
reports those pairs identically and throws away the only interesting part.

```
slack = (value - bar) / |bar|      # proportional, so it means the
                                   # same at an 8% bar or a 4x bar

slack >= +15%   -> pass
    0 .. +15%   -> near-pass       # cleared, but at risk
  -15% .. 0     -> near-fail       # borderline
slack <  -15%   -> fail
```

**Why grading exists — it holds the thresholds still.** Without it, the
only way to admit one company you believe in is to lower a bar, which
silently changes the answer for all 500 and overfits the thresholds to
whichever names happen to be in the test set. That happened repeatedly
while building this: the returns bar moved from 12% to 8% chasing Costco
and Amazon; the solvency bar moved from 20% to 15% to 10% chasing Apple
and Oracle. Grading breaks the loop — a near-miss is recorded as a
near-miss instead of prompting anyone to move the bar. **The thresholds
are now fixed.**

### 3.5 The watchlist tiers

| Tier | Meaning | Goes to Stage 2/3? |
|---|---|---|
| **PASS** | Every gate cleared. A near-pass counts as a pass. | yes |
| **BORDERLINE** | Exactly one near-fail, nothing worse. | yes |
| **EXCEPTION** | A near-fail deliberately overridden — named, reasoned, dated. | yes |
| **REJECTED** | Any outright fail, or two or more near-fails. | no |
| **CANNOT ASSESS** | Fewer than 4 of the 5 substantive gates evaluable. | no |

The tier travels with the company rather than being collapsed away, so
the interface can always show whether a name is on the list cleanly,
barely, or by override — and Stages 2 and 3 still get the definite list
they need to run on.

#### Exceptions

A deliberate, auditable override for a single company. Two hard rules
stop it becoming a backdoor:

1. An exception can only rescue a **near-fail**, never an outright fail.
   Miss a bar badly and no override applies.
2. It must name the **specific gate**. A blanket "let this company in" is
   not permitted.

Each carries a written reason and a review date, and the company is shown
as "on watchlist by exception" — never as a clean pass. An exception
changes the answer for one company; lowering a threshold changes it
silently for five hundred.

`EXCEPTIONS` is currently empty, and that is the intended default.

#### CANNOT ASSESS exists because of a real near-miss

An early version let a company pass by *failing nothing* — which meant
Exxon passed having been evaluated on zero substantive gates, because
none of its data was reachable. That is the worst failure mode
available: it silently admits exactly the companies you know least about.
Eligibility now requires being measurable on at least 4 of the 5
substantive gates.

It currently holds 29 companies, and the composition matters: almost all
are recent spinoffs and IPOs with genuinely less than four years of
standalone filing history — GE Vernova, Solventum, Veralto, Kenvue,
Sandisk, Reddit, Paramount Skydance. **The interface must show these as
"not enough history yet", never merged into REJECTED.** A company with no
record is not the same as a company with a bad one, and conflating them
would quietly bury every recent spinoff.

An earlier count of 36 included eight established financials —
BlackRock, Aflac, Allstate, KKR, Apollo, BNY, Regions, Raymond James —
unassessable purely because Gate 1 demanded an operating-income series
they do not file. Allstate tags none at all; Aflac's stops in 2021. Gate
1 now falls back to net income on the financials track, which is the
profit measure that matters there and the one Gate 2 already uses.

### 3.6 The trap this design exists to avoid

Naive fundamental gates silently delete whole sectors. Measured on real
data: 70 financials report no meaningful free cash flow or debt-to-equity
(deposits aren't debt); 30 REITs are judged on funds from operations and
must pay out ~90% of income; and every negative-free-cash-flow name in a
60-ticker sample was a utility or capex-heavy industrial (AEP, AWK, ATO,
LNT, AEE, AES, APD) — companies that borrow to build infrastructure by
design. That is 100+ companies wrongly excluded by rules that look
perfectly reasonable.

### 3.7 Validation run — the 20 largest, live EDGAR data

The v1 gates were tested against AAPL, MSFT, NVDA, AMZN, META, GOOG,
AVGO, TSLA, BRK-B, JPM, LLY, V, XOM, UNH, MA, COST, HD, PG, JNJ, ORCL.

| What broke | Evidence | Verdict |
|---|---|---|
| Test 1 rejected two great companies | AMZN FAIL, BRK-B FAIL | Amazon posted a 2022 net loss (Rivian markdown, investment cycle). Berkshire's 2022 "loss" was mark-to-market on its equity book under ASU 2016-01 — an accounting rule change, not a business event. Both are false failures. |
| Test 2 produced impossible numbers | HD 223%, AAPL 161%, ORCL 120% | Sustained buybacks shrink book equity toward zero, so ROE explodes. It stops measuring returns and starts measuring buyback intensity. |
| Test 5 had no data | 13 of 20 "no GP tag" | Amazon, Google, Meta, Visa, UNH, Mastercard, Costco, P&G and Oracle simply do not tag `GrossProfit` in XBRL. The test was unrunnable on two thirds of megacaps. |

Also surfaced: `InterestExpense` is untagged for BRK-B, JPM and XOM, and
`PaymentsToAcquirePropertyPlantAndEquipment` is untagged for JPM and LLY.
**Tag availability, not company quality, was the dominant failure mode.**
Every gate now specifies fallback tags and an explicit "not assessable"
outcome.

### 3.8 Tag coverage audit — measured across all 500

Because tag availability was the dominant failure mode, every candidate
tag was measured against the full index before any gate was finalised.
Coverage is what a gate is allowed to depend on.

| Concept | Single tag | With fallback chain | Usable? |
|---|---|---|---|
| Assets | 99.4% | — | yes |
| Operating cash flow | 97.8% | — | yes |
| Revenue | 47.2% | 97.4% | yes, chained |
| Operating income | 77.4% | 95.6% | yes, chained |
| Net income | 94.0% | — | yes |
| Stockholders' equity | 93.8% | — | yes |
| Capital expenditure | 66.6% | 89.2% | acceptable |
| Gross profit | 37.0% | — | **no — gate dropped** |
| Interest expense | 27.2% | 54.4% | **no — demoted to fallback** |
| Long-term debt | 50.8% | — | **no — ROIC abandoned** |

Measured live via EDGAR's `frames` endpoint against all 500 index CIKs.
Balance-sheet items use the instant frame (`CY2024Q4I`); flow items use
the annual frame.

> **Rule adopted: a gate may only depend on concepts reaching ≥ 85%
> coverage after fallback chaining.** Anything below that is either
> demoted to a fallback or dropped.

This is why gross margin became operating margin, why interest coverage
stopped being the sole solvency test, and why ROIC became return on
assets.

### 3.9 Gate 1 — Sustained profitability

Operating income positive in every one of the last 5 years (financials:
one negative year allowed), and net income positive in at least 4 of 5.

```python
neg_allowed = 1 if financials else 0
PASS if count(operating_income[-5:] <= 0) <= neg_allowed
   and count(net_income[-5:] > 0) >= 4
```

**Why operating income leads.** Net income absorbs mark-to-market swings,
one-off writedowns and tax items that say nothing about the business.
Allowing one bad net-income year tolerates a genuine one-off — Amazon's
2022 Rivian markdown — while still failing a company that loses money
repeatedly.

**Why financials get an extra allowance.** Insurers must mark their
investment portfolio to market, so Berkshire's 2022 pre-tax figure was
−$30.5B purely from unrealised equity revaluation while its operating
businesses were fine. Penalising that is measuring the stock market, not
the company.

### 3.10 Gate 2 — Returns on capital *(sector rule)*

```python
standard    ROA = OperatingIncomeLoss * (1 - 0.21) / Assets
financials  ROE = NetIncomeLoss / StockholdersEquity

PASS if median(v[-5:]) >= bar
    or (v[-1] >= bar - 1 and v[-1] > median(v[-5:]))   # improving
```

**Why assets, not invested capital.** ROIC needs debt and cash tags —
`LongTermDebtNoncurrent` covers only 51% of the index. Assets covers
99.4%. A slightly cruder ratio that runs on every company beats a purer
one that runs on half.

**The only sector rule the evidence forced.** Banks and insurers hold
enormous balance sheets against thin spreads, so return on assets is
structurally ~1–1.5% for a perfectly healthy bank. Measured: JPMorgan
earns 12.9–17.0% ROE while running just 1.0–1.5% ROA. An 8% ROA bar is
not strict for a bank — it is arithmetically impossible. Financials are
therefore judged on return on equity, the yardstick the industry itself
uses.

Everything else that looked like it needed sector logic — JPMorgan,
Berkshire, Lilly and J&J all failing together — turned out to be a
tagging problem with one shared fix, not four sector problems.

**Why the "or improving" clause exists — measured.** Live 5-year
return-on-assets paths:

```
AMZN   5.6 -> 4.7 -> 2.1 -> 5.5 -> 8.7%    median 5.5%   RISING
COST   7.7 -> 8.9 -> 9.6 -> 9.3 -> 10.5%   median 9.3%   RISING
MSFT  13.9 ->16.5 ->18.1 ->17.0 ->16.4%    median 16.7%  stable
INTC  12.2 -> 9.1 -> 1.0 -> 0.0 ->-4.7%    median 1.0%   COLLAPSING
```

The original 12% bar excluded both Amazon and Costco — two obviously
high-quality businesses — while the trajectory rule admits both and still
rejects Intel decisively. The bar was simply set wrong, and only running
it on real data revealed that.

### 3.11 Gate 3 — Cash generation, measured across a cycle

Cumulative free cash flow over 5 years > 0. Not single-year.

```python
FCF_year = NetCashProvidedByUsedInOperatingActivities
         - PaymentsToAcquirePropertyPlantAndEquipment
PASS if sum(FCF[-5:]) > 0
```

**Why five years and not one.** Oracle's trailing free cash flow is
−$24.5B — it is building AI datacentres. Its operating cash flow over the
same period ran $9.5B → $15.9B → $17.2B → $18.7B → $20.8B → $32.0B. A
single-year rule rejects one of the highest-quality names in the index
for the crime of investing. The cumulative rule keeps it and still
excludes companies that never generate cash.

Utilities are the exception: their free cash flow is negative by design,
so the test becomes operating cash flow positive every year.

### 3.12 Gate 4 — Debt serviceable

```python
if InterestExpense present:
    PASS if OperatingIncomeLoss / |InterestExpense| >= 4     # 2.5 utilities
else:
    PASS if StockholdersEquity / Assets >= 0.10              # 0.08 financials
```

**Why coverage leads.** It asks the question that matters — can earnings
pay the interest? — rather than merely how much is owed. Equity-to-assets
alone failed Apple (15.6%) and GE (16.2%) for buybacks and restructuring,
not for any quality problem. Leverage is not a defect if earnings
comfortably service it.

**Why the fallback is deliberately loose.** It is a crude proxy used only
when the real test is unavailable, so it should catch the obviously
over-levered without second-guessing companies it cannot properly
measure. At a 15% bar Apple cleared by 0.6 points, which is luck rather
than judgement.

### 3.13 Gate 5 — Durable pricing power

```python
operating_margin = OperatingIncomeLoss / Revenues
ref = mean(op_margin[-4:-1])            # trailing 3 years
PASS if op_margin[-1] >= ref * 0.70
```

**Why gross margin was abandoned.** It is the better concept — it isolates
pricing power from cost discipline — but 13 of the 20 largest S&P 500
companies do not tag `GrossProfit` at all. A test that cannot run on
Amazon, Google, Meta, Visa or Costco is not a test.

**Why the band is relative, not absolute.** An absolute band cannot serve
both ends of the margin range: 6 percentage points is a rounding error to
a 40%-margin semiconductor firm and a catastrophe to a 5%-margin
retailer. Measured — Dollar General's operating margin roughly halved
(8.2% → 4.2%) and still passed a 6pp band. The 70% rule fails DG at 51%
of its average while passing Texas Instruments at 74%.

### 3.14 Gate 6 — Liquidity

```python
PASS if median(close * volume, 63 trading days) >= 25_000_000
```

**Why this exists.** Accumulating a position means buying without moving
the price against yourself. This gate is about executability, not
quality — it is listed separately for that reason. Every S&P 500 name
clears $25M comfortably, so it does nothing today; it is here so the
universe can widen later without silently surfacing names you cannot
actually buy.

*Requires price data, so it is the one gate not computed from EDGAR. It
runs with Stage 2.*

### 3.15 Sector handling

| Track | Count | Treatment |
|---|---|---|
| Standard | 336 | All six tests as written. |
| Financials | 75 + 7 | Gate 2 uses return on equity; Gate 4's fallback bar is 8%; Gate 1 allows one negative year and falls back to net income where no operating-income series is filed. The 7 are health insurers (UNH, ELV, CI, HUM, CNC, MOH, CVS) that the index files under Health Care but which are insurance companies — premiums in, claims out, large investment float. Named explicitly: matching on company name wrongly swept in hospital chains, a drug distributor and a device maker. |
| Capital-intensive | 21 | Telecom, cable, media. Asset-heavy so return on assets misreads them, but they generate strong free cash flow — so Gate 2 alone changes, to ROE ≥ 10%. |
| Utilities | 31 | Gate 2 → ROE ≥ 8% (regulator-allowed ROE runs 9–10.5%); Gate 3 → operating cash flow, since utility free cash flow is negative by design; Gate 4 → coverage ≥ 2.5×. |
| REITs | 30 | Not assessed by these gates — see below. |

**REITs become a second watchlist, not an exclusion.** Rather than
dropping 30 companies, REITs get their own funds-from-operations-based
Stage 1 (FFO growth, debt/EBITDA, occupancy trend) and their own
watchlist. Until that track is built they are labelled "REITs — not yet
assessed" rather than quietly vanishing. This makes the gap visible and
addressable instead of invisible.

> **Honesty requirement:** the interface must state how many companies
> were excluded for lack of a valid test, separately from those that
> failed one. Those are different facts and must not be merged.

### 3.16 Data plumbing — four bugs that would have silently corrupted results

None of these are visible from reading a spec. All were found by running
the gates against real filings, and each would have produced confident,
wrong answers.

| Problem | What it did | Fix |
|---|---|---|
| **No operating-income line** | JPMorgan, Berkshire, Lilly and J&J all went unassessable at once — four sectors, one cause. Banks and insurers have no meaningful "revenue minus operating costs" subtotal, because interest *is* the business; much of pharma goes straight to pre-tax income. | Fall back to pre-tax income. Imperfect (it includes non-operating items) but far better than not assessing them. |
| **Figures split across tags** | J&J reports pre-tax income as Domestic and Foreign — 13 years each — and never files a usable combined figure. | Sum the component tags when the total is missing (`SUM_PARTS`). |
| **Stale series** | Mastercard's `NetIncomeLoss` stops at 2013; modern years use another tag. The code was about to score it on decade-old figures and call the answer current. | A chain entry only qualifies if it is long enough **and** reaches the present (`min_recent_year`). |
| **Orphaned history** | A 2025 reorganisation moved Exxon to a new filer ID with 94 tags and zero annual history; its real 19-year record sits under the predecessor CIK. The successor's record lists no former names, so nothing links them. | An explicit predecessor map (`PREDECESSOR_CIK`). Named rather than fuzzy-matched, so it can never attach the wrong company's accounts. |

### 3.17 The regression test

Seventeen companies where the right answer is known independently of this
code. It runs on every threshold change and fails loudly if any anchor
moves — the defence against tuning the gates until they merely flatter
the test set.

| Must pass (13) | Must fail (4) |
|---|---|
| AMZN · META · AAPL · NVDA · NFLX · GOOG · BRK-B · COST · WMT · MA · V · ISRG · MSFT | INTC · BA · F · MMM |

**Status: passing, 17 of 17.** Positives are the high-conviction
compounders plus names the S&P 500 Quality Index independently selects.
Negatives are recognised deterioration cases — Intel fails 4 gates,
Boeing 5.

Genuinely debatable names are deliberately excluded from the set: TXN,
CSCO, GE, ORCL, CVS, DG, EL. **A golden set may only contain cases we are
certain about, or it stops being a reliable alarm.**

### 3.18 Full-index result

Measured across all 500 from this repository, 29 Aug 2026:

| Tier | Count | Share |
|---|---|---|
| PASS | 210 | 42.0% |
| BORDERLINE | 29 | 5.8% |
| REJECTED | 202 | 40.4% |
| CANNOT ASSESS | 29 | 5.8% |
| REIT (not assessed) | 30 | 6.0% |
| **Eligible for Stages 2/3** | **239** | **48%** |

Which gate does the rejecting:

| Gate | Outright fails | Near-fails |
|---|---|---|
| 1 · Sustained profit | 68 | 0 |
| 2 · Return on capital | 129 | 26 |
| 3 · Cumulative 5y FCF | 29 | 0 |
| 4 · Debt serviceable | 57 | 13 |
| 5 · Op margin durable | 76 | 14 |

By sector:

| Sector | Eligible | of | Pass | Borderline | Rejected | Cannot assess |
|---|---|---|---|---|---|---|
| Industrials | 47 | 83 | 44 | 3 | 30 | 6 |
| Financials | 47 | 76 | 42 | 5 | 28 | 1 |
| Information Technology | 36 | 73 | 32 | 4 | 34 | 3 |
| Health Care | 26 | 59 | 21 | 5 | 30 | 3 |
| Consumer Discretionary | 23 | 47 | 21 | 2 | 21 | 3 |
| Consumer Staples | 15 | 34 | 11 | 4 | 16 | 3 |
| Utilities | 17 | 31 | 13 | 4 | 12 | 2 |
| Materials | 8 | 25 | 7 | 1 | 14 | 3 |
| Energy | 10 | 21 | 9 | 1 | 9 | 2 |
| Communication Services | 10 | 21 | 10 | 0 | 8 | 3 |
| Real Estate | — | 30 | — | — | — | — |

Tightening the shock rule moved Gate 1's outright fails from 66 to 68 —
two Industrials companies no longer have 2020 excused — but changed no
tier, because both were already rejected on other gates. The eligible
count is unaffected by the fix.

An earlier measurement gave 238 eligible (208 PASS / 30 BORDERLINE / 203
REJECTED). That difference is **not** the shock rule: it is the
constituent list. This repository fetches the index live rather than
reading a static ticker file, so membership drifts with the real index
(~20–25 names a year). Comparisons across runs are only meaningful when
the universe is pinned.

---

## 4. Stage 2 — the dislocation score

*Specified, not yet built.*

Applies to every Stage 1 PASS, BORDERLINE and EXCEPTION — the tier
carries through so the interface can show it, but all three are scored.
Answers: **how far below its own normal is this today?**

### The calculation

```python
# 1. Three raw measures of "below its own normal", in %
d_ma   = (SMA200 - price) / SMA200      # below long-run trend
d_high = (high52 - price) / high52      # below yearly peak
d_tgt  = (target - price) / price       # below analyst consensus

# 2. Standardise each ACROSS THE WATCHLIST so weights mean what they say
z(x) = (x - median(x)) / IQR(x)         # robust to outliers

# 3. Weight and combine
raw = 0.50*z(d_ma) + 0.30*z(d_high) + 0.20*z(d_tgt)

# 4. Map to 0-100 for display (percentile within the watchlist)
DislocationScore = percentile_rank(raw) * 100
```

**Standardisation is not cosmetic — it is the fix for a measured bug.** A
component only moves a ranking to the extent it *varies* across the
names being ranked. In the predecessor's blend, three components with
stated weights 50/25/25 had spreads of 11.3, 27.4 and 13.3 points, so the
*effective* weights were ≈36/43/21 — the 52-week high dominated despite
being nominally quarter-weighted, and removing it changed 6 of the top 20
names. Standardising each component before weighting is what makes the
stated weights true.

**Why 50/30/20.** The moving average is the closest thing to "its own
normal" and gets the most weight. The 52-week high is a single day, so it
is a supporting signal, not a lead one. The analyst target is a forecast
carrying documented optimism bias, so it is weighted least.

**Why median/IQR rather than mean/standard deviation.** A single crashed
stock would drag a mean and inflate a standard deviation, compressing
everyone else. Median and interquartile range are unaffected by extremes.

**Why percentile for display.** A raw z-score is meaningless to a reader.
"87" communicates "more dislocated than 87% of your watchlist", which is
exactly the question being asked.

---

## 5. Stage 3 — cheap, or broken?

*Specified, not yet built.*

The decisive stage. A quality company that has fallen sharply is either
mispriced or genuinely impaired, and price alone cannot tell you which.

Six independent checks, each scored −1, 0 or +1, then summed to a
−6…+6 **Corroboration score**.

| Signal | Source | +1 (cheap) | −1 (broken) |
|---|---|---|---|
| **Analyst conviction trend** | recommendation breakdown, 4 months | Buy/strong-buy share flat or rising | Downgrades accumulating as price falls |
| **Fundamental trajectory** | EDGAR, last 4 quarters | Revenue and margin holding or improving | Both deteriorating sequentially |
| **Idiosyncratic or sector-wide** | computed from peers in the scan | Sector is flat/up — the fall is company-specific and possibly overdone | Falling much harder than a falling sector |
| **Distance from failing Stage 1** | Stage 1 outputs | Comfortably clears every gate | Within 10% of failing any gate |
| **Volume character** | 10-day vs average volume | Ratio ≤ 1.0 — the fall happened on ordinary volume: drift, not stampede | Ratio ≥ 1.5 — heavy volume on the way down: institutions distributing |
| **Short interest** | short % of float | Below ~3% — no organised bear thesis | Above ~6% — informed money positioned for further decline |

**The fourth signal is the one that matters most and is unique to this
design:** it asks whether the company is on the verge of ceasing to be
quality. A stock that still passes Stage 1 but is one bad quarter from
failing it is precisely the falling knife the funnel exists to avoid.

**Why the two market-behaviour signals earn a place.** Live check across
eight names: volume ratios clustered at 0.57–0.85× for quiet stocks,
while NKE — the most dislocated name — showed 1.24×. Short interest was
sharper still: 0.8–2.8% for the calm names versus 7.2% for NKE. Both
independently flagged the one stock whose fall looks contested rather
than incidental, which is exactly the discrimination Stage 3 exists to
make.

### Rejected after testing — institutional ownership %

The intuition is sound: wouldn't BlackRock and Vanguard want to own
quality? It was tested as a floor across 70 index members:

```
min 42.5%   p5 58.0%   p10 69.7%   median 89.9%   max 113.2%
```

Two findings kill it. First, the eight names below a 70% floor are AMZN,
CTAS, KO, BEN, KKR, LVS, OXY, TSLA — that list contains Coca-Cola (68.4%)
and Amazon (68.7%). Any floor strict enough to flag anything flags
Coca-Cola. Second, a maximum of 113.2% — ownership above 100% of float —
shows the underlying data is itself unreliable, inflated by share lending
and stale float figures.

The mechanism explains why: Vanguard and BlackRock hold every S&P 500
constituent mechanically, in index proportion, with no opinion whatsoever.
Within this universe the figure measures index membership, not conviction.

Worth revisiting only if the universe ever widens beyond the S&P 500,
where passive ownership isn't automatic.

### Verdict mapping

```
score >= +3   -> ACT     "Dislocated, evidence intact"
score  0..+2  -> WATCH   "Mixed evidence"
score <= -1   -> AVOID   "Deterioration signs"
```

**ACT / WATCH / AVOID** is the vocabulary carried through every surface,
so the same three words mean the same three things everywhere.

Three verdicts, not a percentage. A number implies a precision this
evidence does not have — six coarse signals cannot justify "73%
confident". A verdict says what it knows, and the underlying six checks
are always shown so the reader can disagree.

---

## 6. Interface principles

**The detailed UI specification is a separate document, written after
Stage 3 is built and validated.** This section records only the
principles that constrain it, so that the interface is designed around
real numbers rather than a guess.

1. **The page reads as the funnel, top to bottom.** It opens with an
   answer, not with filters. Filters are adjustment, not the product.
2. **Most days the answer is "nothing is on sale."** That is a useful and
   honest answer, and the design must make it tolerable rather than
   treating it as an empty state to apologise for.
3. **The most dislocated name is not automatically the recommendation.**
   If its Stage 3 evidence is mixed, it ranks below a less-dislocated
   name whose evidence is intact. That inversion is the entire point of
   Stage 3 and the interface must show it.
4. **Nothing is a black box.** Every threshold shows the company's actual
   value beside the bar it had to clear, so a rejection is a fact the
   reader can disagree with.
5. **"Closest to its limit" is shown per company** — which gate to watch.
   That is what turns a screen into a monitoring tool.
6. **CANNOT ASSESS is never merged into REJECTED.** No record and a bad
   record are different facts.
7. **A ticker inspector is required.** Type any ticker, see exactly where
   it stands in the funnel and why — including, and especially, the
   rejected ones. This is what makes weeks of "nothing on sale"
   tolerable: the screen may be silent, but the tool never is.
8. **The tier is always visible.** A BORDERLINE name is never shown as a
   clean pass, and an EXCEPTION never as either.

---

## 7. Build order

Agreed and not to be reordered:

1. **Stage 1 as a research script — done.** Built, running against live
   EDGAR, 17-company regression test passing.
2. **Run all 500 through Stage 1 — done.** 238 of 500 eligible.
3. **Stage 2** — the dislocation score.
4. **Stage 3** — starting with the analyst-trend signal.
5. **Write the UI specification and mockups.**
6. **Build the interface last**, once all three stages produce real
   numbers.

**Why the full run comes before any UI.** Every layout decision assumes a
watchlist size. If the real number is 40, the watchlist is a single list
and sector filters are pointless. If it's 300, the gate isn't gating.
Designing the page first means designing around a guess — which is
exactly what went wrong in the predecessor project.

---

## 8. Open questions

### Settled

- **REITs** — a second watchlist with their own FFO-based gate, not an
  exclusion.
- **Stale watchlist between filings** — the concern was misplaced. If a
  company deteriorates, Stage 3 catches it before Stage 1 needs to:
  falling analyst conviction, worsening quarterly trajectory, heavy
  down-volume and rising short interest all fire within days. Stage 1
  sets who is *eligible*; Stage 3 is the recency layer.
- **Weeks with nothing on sale** — correct behaviour, made tolerable by
  the ticker inspector.
- **ACT / WATCH / AVOID** — adopted as the shared vocabulary.
- **Institutional ownership %** — tested and rejected.
- **A news-recency signal** — left out of v1. The market signals already
  *are* the recency layer and are more reliable than headlines: volume,
  short interest, analyst revisions and quarterly trajectory all encode
  what the news means without needing to interpret prose. Revisit if the
  six signals prove insufficient.

### Still open

- **Q1 · Are these the right six gates?** They test profitability,
  returns on capital, cash generation, solvency, margin durability and
  executability. Deliberately absent: *growth* (a great business can be
  flat, and growth screens chase momentum) and *valuation* (cheapness is
  Stage 2's job — a P/E limit here would fight the funnel by rejecting
  the very dislocations you are hunting).
- **Q2 · Does the "or improving" clause let too much through?** Gate 2
  passes a company on trajectory alone. That is what admits Amazon, and
  it correctly rejects Intel. But it will also admit a turnaround after
  one good year. The alternative is requiring two consecutive improving
  years: stricter, but slower to recognise a real inflection.
- **Q3 · Is 15% the right borderline band?** It currently makes J&J
  borderline rather than rejected, and keeps Dollar General rejected.
  Worth revisiting now that the full-500 run shows the tier distribution.
- **Q4 · Should J&J and Broadcom get exceptions?** Both land BORDERLINE.
  They already flow to Stages 2 and 3 labelled as such, which may be
  sufficient. Recommendation: neither, for now. Exceptions should be
  reserved for cases where the gate is measuring the wrong thing, not
  merely producing an answer we dislike.

---

## Credits

- **SEC EDGAR XBRL API** — U.S. Securities and Exchange Commission.
  Public-domain filing data. `https://data.sec.gov`
- **S&P 500 constituent list and GICS sector labels** — Wikipedia,
  *List of S&P 500 companies*, CC BY-SA.
- **S&P 500 Quality Index** — S&P Dow Jones Indices. Used only as an
  independent cross-check when assembling the golden set; no index
  methodology or data is reproduced here.
- **ASU 2016-01** (equity securities measured at fair value through net
  income) — Financial Accounting Standards Board. The accounting change
  that explains Berkshire's 2022 reported loss.
- No external code was copied into this project.
