# The Quality and Price Funnel

**Vantage · Funnel Spec v2.21 · 30 Aug 2026**

Find durably excellent companies, then watch for one of them to trade
well below where it usually trades. Two stages, every calculation stated
in full — and then you go and read about the company yourself.

> **This document is the single source of truth for Vantage.** Anything
> that disagrees with it — code comment, README, chat history — is wrong
> until this file is changed. See [CONTRIBUTING.md](../CONTRIBUTING.md)
> for what may and may not enter this repository.

## Tenets

Five rules that govern every stage. A design either violates one or it
doesn't. Full text and the evidence behind each is in
[TENETS.md](../TENETS.md) — the only copy that should be edited.

1. **No reconstruction of time periods.** Figures exactly as filed; never derive a period the filer didn't report.
2. **Don't display what isn't used.** Drivers and audit trail only. Decoration is cut.
3. **Measure before deciding.** Every threshold comes from real data, never intuition.
4. **A check must change outcomes, or be cut.** If removing it changes nothing, it stays removed.
5. **Thresholds never move to admit a company.** A named exception, or it stays out.

## What this version is

All three stages are built and running — Stage 1 against live SEC EDGAR
filings with a 17-company regression test, a data-recency assertion and a
unit test that a quarter can never pass as a year; Stage 2 against daily
prices with a 13-check validation suite; Stage 3 against quarterly
filings, annotating the ranking without reordering it. §5.1 keeps the
record of why Stage 3 was cancelled in v1.0 and §5.2 why that decision
was reopened.

The result is published as **two pages over one scan**, regenerated from
each run:

- **[/vantage/](https://smunka42-gh.github.io/vantage/)** — the detailed
  table, every company a row.
- **[/vantage/simple/](https://smunka42-gh.github.io/vantage/simple/)** —
  one readable sentence per company, for a reader without a trading
  background (§6 principle 9).

Neither withholds anything from the other: the expanded panel is one
implementation inlined into both.

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
| **v2.21** | 30 Aug 2026 | **"What this version is" was two versions stale and said so in the present tense** — *"Both stages are built"* and *"There is no Stage 3"*, thirteen versions after Stage 3 shipped in v2.8. It also pointed only at the detailed page. Rewritten, and both pages are now named here and in the README. The doc-currency test did not catch it: it checks counts, gate numbers and placeholders, not prose about which stages exist. Worth knowing about the guard's shape — it catches numbers that drift, not sentences that were true once. Also teaches the pre-commit risk map about `site/detail.js`, `site/detail.css` and `site/template_simple.html`, added earlier today: the panel is inlined into BOTH pages, so a change there is the most warning-worthy kind, and it was triggering nothing. |
| **v2.20** | 30 Aug 2026 | **A page that has quietly stopped updating now fails something.** Measured 30 Aug: GitHub fires the schedule but unreliably — one firing in ~22 opportunities, 4h 18m late. A single miss is harmless (16.5h of slack before the next open, and the state gate keeps a late run correct), but consecutive silent days would leave the page stale behind a green tick, because a run that never happens cannot fail. Two guards, both keyed on `scan.json`'s `generated_utc`: the doc-currency test fails locally, and an **ungated** final workflow step fails on any firing — including one that skipped the scan, which is the state this failure actually produces. **Five days, not three**: the workflow commits only when the page changes, so a market holiday produces no commit, and Thu→Tue closures make 5 the longest real gap. Three would fire every ordinary weekend, which is how a check earns being ignored. Verified at 3, 5, 6 and 9 days. **What neither catches**: a period where the workflow never fires at all — nothing inside GitHub can, and that needs an external check. |
| **v2.19** | 30 Aug 2026 | **Every gate detail is now written for a reader**, on both pages — the wording lives in the shared `site/detail.js`. Measured before: **628 of them reached the reader as backend strings**; after: none. Gate 6 had no `plain()` case and no `GATE_LABEL` entry at all, so ~470 companies showed *"revenue grew 10.6% a year over 5y (2021-2025)"* raw. Four more shapes fell through their regexes: **negative** cumulative cash flow (`$-1.1B`, which assumed a `+`), **negative** operating margin (EchoStar's −118.1%), four-year windows, and `operating cash (no capex tag)`. **Labels no longer assert over a check that never ran**: where the filings contain nothing to measure, the label drops to a neutral topic — *Profit record*, *Debt*, *Sales growth* — instead of *"Profitable every year"* above *"insufficient history"*. §3.5 already said CANNOT ASSESS is not REJECTED; the wording now says it too. **The REIT note is deleted as dead code** — REITs are excluded from the page entirely (§6 principle 7), so no row could ever reach it. The build stamp now says why staleness matters rather than printing a bare timestamp. |
| **v2.18** | 30 Aug 2026 | **`/simple/` carries the same six filters as the detailed page**, laid out side by side in a three-column grid rather than stacked. It shipped with three of them removed on the argument that a fourteen-row list states each one on the face of every card; laid out horizontally the whole set costs 211px, so the argument for dropping them was really an argument about vertical space. Sorting sits below a rule, separated from the filters, because it changes the ORDER and never the membership. **`passes()` is now identical on both pages** and reads the same stored fields — `r.z`, `r.sh`, `r.s3.l`. The simple page had been deriving size from market cap itself, which would have drifted the moment a boundary moved. |
| **v2.17** | 30 Aug 2026 | **A second page at `/simple/`** (§6 principle 9, §6.1), for a reader with savings and no trading background. The detailed table at `/` is untouched. One company per readable sentence, a funnel read downward, and colour only where the funnel already reaches a verdict — never on a price move. **Nothing is withheld**: the expanded card opens the same panel the table does, five-year record included. The panel was extracted to `site/detail.js` and `site/detail.css` and is inlined into both pages by `build_site.py`, so the two cannot drift; the extraction was verified to leave `docs/index.html` byte-identical. The daily workflow now renders and publishes both from one scan. Found while building: `detail.js` emits `<div class="card">` for each stage box, so the new page's own `.card` captured 126 of them — the company card is `.co-card`. |
| **v2.16** | 30 Aug 2026 | **Stage 3 had never run in CI** (§3.17). Its workflow step was missing the `SEC_USER_AGENT` block Stage 1 has, so it died on its first EDGAR request in every scheduled and dispatched run since the stage shipped, while `continue-on-error` painted the step green. The defect was masked by local rebuilds: the results files are gitignored, so every published page carrying Stage 3 data had been built by hand rather than by the pipeline. The first CI-built page after Stage 3 existed published with the cheapness column empty for all 470 rows. Fixed, and the publish guard extended to check Stage 3's output rather than its exit code — it had validated only Stages 1 and 2. Re-run clean: 500 gated, 259 eligible, 468 priced, 253 read for cheapness. |
| **v2.15** | 30 Aug 2026 | **Stage 3 gate 1's four-year minimum documented as structural** (§5.3). It had read as an arbitrary constant, which is how it became an open item. At three years the 3y and 5y windows are the same list, so the medians are identical and *"priced about as usual"* — 52 of 450 companies today — becomes unreachable; four years is where the two windows first differ. A (3y, 4y) pairing was considered and changes nothing, being equally identical at three years. **The six eligible companies without gate 1 are closed as unfixable**, with the cause corrected: it is three companies whose data the API does not carry (V, BRK-B, ERIE file EPS per share-class, behind a dimension `companyfacts` omits) and three with genuinely three years (GDDY — which does file the tag, contrary to the earlier note — plus TKO and VLTO). Verified against EDGAR. Also corrects v2.14's predicted outcome to the measured one: five tiers moved, not three. |
| **v2.14** | 30 Aug 2026 | **Gate 4's coverage discount is earned, not assigned** (§3.12). The 2.5x bar was given to utilities as a sector — bar-fitting, which §3.2 forbids, and v0.5's changelog records the pass-rate origin ("utilities went from 1/31 to 17/31 eligible"). It now goes to any company whose **operating income has not fallen more than 10% year-on-year** across the window, on any track. The justification was always real and simply misattached: measured, the median utility's worst year is **−0.3%** against **−15.2%** for standard companies, and 16% have ever fallen >25% against 36%. Utilities still qualify most often (66% vs 34%) but through the property. **Measured on the live scan, five tiers moved**, not the three predicted: FISV and GEN BORDERLINE → PASS and OKE REJECTED → BORDERLINE as expected, and **D (Dominion) and ED (Con Edison) BORDERLINE → REJECTED** — both had genuine double-digit operating-income falls (Dominion's margin 17.1% → 9.9% in 2022, Con Edison's 22.1% → 17.3% in 2024), so neither qualifies as stable and both moved to the 4.0x bar. NRG also loses the discount it held purely by label. Eligible utilities **20 → 18**; eligible overall 260 → 259, and Utilities is the only sector to fall. The −10% line is not a new constant: Stage 3 gate 2 already uses it for this quantity across 11,536 quarter pairs. Measured annually over four comparisons, which is thin and said so; the quarterly alternative is rejected because Stage 1 rests on audited filings and quarterlies are reviewed. The sector-value count drops from four across three gates to **three across two**. The 4.0x base bar's own lack of derivation is left open rather than fixed here. |
| **v2.13** | 30 Aug 2026 | **No minimum years of history — decided and recorded** (§3.5). TKO Group passes on a four-year series whose coverage ran 3.9x, 1.6x, 0.1x, 4.1x, which raised the question of a minimum record length. Measured, both candidate instruments fail: a minimum-years rule would reject **Honeywell, Ross Stores and CRH**, whose short *series* is a tag-chain artifact rather than youth (Honeywell's own gates read `net income positive 5/5`), and a volatility rule would flag **PNC, USB, BAC and JPM** at 14-24x coverage swings, where coverage is a rate-cycle artifact. TKO is already graded near-pass on gate 4 and carries an `at_risk` flag naming it; 48 PASS companies rest on at least one near-pass. Recorded rather than left as a decision taken in conversation — the failure mode §3.12's utility bar is still an open item for. Also fixes the tier table, which said "4 of the 5 gates evaluable" and has read 4 of **6** since gate 6 landed in v2.8. |
| **v2.12** | 30 Aug 2026 | **`partial_years()` removed, replaced by `tests/test_whole_years.py`** (§3.17). The guard against a quarter posing as a fiscal year inferred the defect from a REVENUE COLLAPSE — any year under 30% of the one before. That was a guess about values standing in for a fact about periods, and the corridor it worked in was narrower than it looked: measured across all 1,766 consecutive-year revenue pairs in the index, Accenture's quarter posing as its year was 0.22 of the prior year while Western Digital's entirely real FY2023 collapse was 0.34, leaving four points between a threshold and a false alarm — and a seasonally concentrated quarter above 30% of its year would have passed unnoticed, which is the case the guard existed for. The structural rule (350-380 days, in `_pick`) is unchanged and was always the real fix; it is now pinned by a unit test replaying the exact Accenture filing rather than by a heuristic re-run over 500 companies on every scan. The test was verified to fail — reproducing the original 2.24B-beats-10.23B result — with the rule removed. |
| **v2.11** | 30 Aug 2026 | **The `?resize=1` drag tool removed.** It existed to let the column widths be chosen against real data; once they were frozen in v2.10 it was ~115 lines of CSS and JS shipped to every visitor for no remaining purpose, so it is deleted rather than left gated behind a flag. Recoverable from `feb1f97`. The `localStorage` override went with it, so the stylesheet is now the only thing that can set a column width. |
| **v2.10** | 30 Aug 2026 | **Column widths frozen** (§6 principle 9, §6.1). Computing them failed three ways in succession — fixed layout with guessed widths clipped values, auto layout re-sized the table on every filter click because it measures only the rows on screen, and measuring across all 470 at load became redundant once the widths were chosen deliberately. They are now set by hand through a build-time `?resize=1` drag mode and read off into the stylesheet, with `table-layout: fixed` honouring them literally; every value in all 470 rows was checked to fit first. **Long headings wrap, values do not**: a nowrap heading sets a floor wider than its own data, and `% below usual` was holding 123px for values needing 67. The one value exception is Stage 3's read, where *no earnings history* and *profit falling* appear together and, kept on one line, set a floor no width could get under. **A `No.` column** gives each row its position in the list as currently sorted and filtered. Removed: a stray duplicate `col.c-exp` rule later in the stylesheet that had been silently overriding the width above it. |
| **v2.9** | 30 Aug 2026 | **The page becomes one filterable table.** Every company Stage 1 assessed (470) is now a row; the quality gate and the 10% bar became filter DEFAULTS rather than a hard cut, so the default view is unchanged in spirit (14 rows) while nothing is hidden. **§6 principle 1 is REVERSED** — it required the page to open with an answer rather than filters — and §6 principle 7's dedicated ticker inspector is replaced by search, redundant once every ticker is a row. Both revisions are recorded in place rather than quietly dropped. Quality is shown as **high / medium / low / uncertain**; "uncertain" is CANNOT ASSESS, which is unmeasured rather than bad. Trend and pricing filters deliberately have NO defaults: a default is a claim, and defaulting those would assert "still falling is bad" and "not cheap is uninteresting", which §4.2 and principle 3 refuse. **REITs are absent from stages 2 and 3** as well as 1 — whatever Stage 1 did not run on, nothing downstream runs on either. **The headline is gone**: it was a claim that could not survive filters changing what is on screen. Plain-language column headings throughout (`% below usual`, `Price trend`, `Cheaper or pricier?`, `Size`, `Research`); the two moving-average columns merge. A per-row `+` replaces "click a row to see the working" and adds the `aria-expanded` the rows never had. Footer carries a GENERATED build stamp — v2.6 removed a hardcoded spec version for going stale, so this is the date and commit the page was actually built from. |
| **v2.8** | 30 Aug 2026 | **Gate 6 added — revenue durability** (§3.14). Gates 1-5 test whether a business is sound; none tested whether it is shrinking, and 41 of 262 eligible (16%) were flat or shrinking while passing all five. It is not redundant (r = +0.14, +0.17, +0.06 against gates 2, 5, 4). Conditional on purpose: neither the 5-year CAGR nor the vs-3-year-average view works alone, and requiring both to be negative excludes every cyclical in the index while catching Nike, which CAGR misses entirely at −0.2%. Bar **1.00**, the company's own 3-year average; at 0.95 the gate rejected nobody, CHRW missing the fail line by four thousandths. Rejects CHRW, HPQ, TGT; marks nine more. **Borderline band stays at 15%** — 10% was measured across all 470 assessed companies and costs 9 eligible (CMS, D, DTE, GNRC, HUM, KEY, L, NOC, SO), concentrated in the regulated and leveraged sectors the tracks already accommodate, and would re-reject D and SO which the v2.7 part-year fix had just rescued. PASS is unchanged at 224 either way: the band's upper half has no tier consequence at all, so tightening it is a one-directional change to the rejection rule, not a symmetric one. **Stage 3 specified and reopened** (§5) — the spec's own revisit condition ("a lagging signal replaced by a current one") was met: quarterly filings are a median 60 days old against annual filings at 2-12 months, covering 260 of 262. Two checks — cheapness in earnings-yield POINTS, and operating income against the year-ago quarter. The v1.0 circularity objection to P/E is answered by measurement rather than waived. §4's stale "specified, not yet built" removed. |
| **v2.7** | 29 Aug 2026 | **Part-year figures rejected.** A 10-K carries the quarters inside it as well as the year, and some filers tag those `fp=FY` too. `_pick` grouped facts by the year in their end-date and kept the newest-*filed* entry, so where a quarter and the year were filed the same day the tie broke on JSON ordering and the **quarter could win** — Accenture's return on assets read 2.7% instead of 12.4%, one quarter's profit over a full year's balance sheet. Duration facts must now span **350-380 days**. The error was one-directional (a part-year profit against a full-year balance sheet always understates), so it could only wrongly reject: D, SO, TKO and URI move up, none move down, eligible 258 to 262. The golden set could not guard this — not one of its seventeen anchors was affected — so `partial_years()` asserts on the data across the whole index (§3.17). **Interest as % of profit removed** from the five-year record: it was coverage inverted (share = 1/coverage), the only row where lower was better, and it carried no bar; the record's `bar` column now reads **`at least`**, which states the direction for every remaining row without per-row markers (§6.1). **Gate 4's label now follows the test that ran** — "Can cover its interest" where coverage was used, "Not overloaded with debt" where the equity/assets fallback was (§3.12). |
| **v2.6** | 29 Aug 2026 | **REIT exclusion stated plainly.** The page said "all 500 constituents are tested", which was untrue — the gates never run on the 30 REITs, so the scan covers **470**. Both the page and §3.16 now say so, and a looked-up REIT explains why it was skipped. The spec had also described REITs as "a second watchlist, not an exclusion", which described an intention rather than the code; that track does not exist. Page footer trimmed of a hardcoded spec version that had already gone stale, plus gate and stage counts that mean nothing to a reader. |
| v2.5 | 29 Aug 2026 | **All open questions settled.** Five gates confirmed; the improvement clause left as written; the borderline band stays at 15% (no evidence favours a change, and moving a threshold without evidence is what tenet 3 forbids); exceptions removed entirely in v2.3. §8 now records what would settle a future question rather than listing opinions. |
| v2.4 | 29 Aug 2026 | **52-week scale added to the expanded row** — low, today, high, with today's distance from each end. Shown, never scored: distance above the low correlates −0.77 with the below-normal figure, so it would cancel itself out as an input, but the residual separates names the score rates identically. §6.1 records the collision and wording decisions. Also clears two passages that still assumed EXCEPTION existed. |
| v2.3 | 29 Aug 2026 | **Exceptions removed.** The mechanism could only relabel a named near-fail as EXCEPTION instead of BORDERLINE — and nothing else, since both tiers were already eligible and treated identically everywhere downstream. It changed no outcome (tenet 4), and never covered the case that actually creates pressure to move a bar: a company you believe in that is REJECTED. An exception could only rescue a *near*-fail, and a single near-fail already yields BORDERLINE, which already passes through. Tenet 5 is now absolute: the company clears the bar or it does not. |
| v2.2 | 29 Aug 2026 | **Published.** The page is generated from the scan by `scripts/build_site.py` and served by GitHub Pages from `docs/`, static by design so there is no process to sleep or wedge. A scheduled workflow rescans the full index through both stages each trading day an hour after the close, gating on **state rather than the clock** because GitHub delays scheduled runs — and refusing to publish a scan whose shape looks wrong. Adds §6 interface decisions taken during the build. |
| v2.1 | 29 Aug 2026 | **"On sale" dropped as a phrase.** It claims a fall is a bargain, which this figure cannot know — the same objection that ruled out "discount". The flag now reads *more than 10% below its own normal*, and `ON_SALE` becomes `BELOW_NORMAL_BAR`. |
| v2.0 | 29 Aug 2026 | **Stage 3 removed before being built.** Every candidate signal was either circular (analyst target, P/E vs own range), near-constant (volume character awarded +1 to 89% of the index), or lagged behind the event it was meant to judge (short interest 2-3 weeks, fundamentals up to 3 months). The decisive argument: Stages 1 and 2 already reduce 500 to ~16 **ranked** names, so the ranking is the triage and a third stage changes no outcome — [tenet 4](../TENETS.md) applied to a whole stage. Replaced by links out plus the two things external sites cannot provide: which gate a company is closest to failing, and how stale the filed data is. **"Dislocation" renamed "below normal"** — it measures price against its own price history, not against value, and "discount" would claim more than the number earns. **Market cap added as a sortable column**, deliberately not a grouping. Shape labels reworded to plain language. |
| v1.0 | 29 Aug 2026 | **Tenets adopted** ([TENETS.md](../TENETS.md)) and applied. **Frame-filter defect fixed:** `_pick` was discarding EDGAR entries carrying a `frame` label, which for the newest fiscal year is often the only entry present — 99% of the index was scored on filings a full year older than available. **Gate 6 (liquidity) removed** (tenet 4: zero rejections across 500) and not demoted to a displayed fact (tenet 2). **52-week high removed entirely** rather than kept as displayed context (tenet 2). **TTM and 10-Q data rejected for Stage 1** (tenet 1: no reconstructed periods). A data-recency assertion added to the golden set, since an outcome test cannot detect a freshness defect. |
| v0.9 | 29 Aug 2026 | **Stage 2 rebuilt from measurement.** Score is now two moving-average components blended as real percentages — `0.60*d_ma200 + 0.40*d_ma50` — with an absolute 10% "on sale" bar replacing the percentile rank. The 52-week high is dropped from the score (0.74 correlated with the 200-day, and contaminated by spikiness) and kept as displayed context; the analyst target moves to Stage 3, where its question actually belongs. Standardisation removed as unnecessary once the components are commensurate, with the residual ≈68/32 effective split disclosed rather than engineered away. Adds the fresh/stabilising/recovering shape label, the data-quality gates and the Stage 2 validation plan. |
| v0.8 | 29 Aug 2026 | Shock-year rule tightened: a company counts only if it was **profitable the year before**, so a loss must be specific to that year. Stops chronic loss-makers standing in as evidence of an industry-wide event, which had made Industrials 2020 fire spuriously. Only Energy 2020 fires. |
| v0.7 | 29 Aug 2026 | Health insurers routed to the financials track. Financials' Gate 1 falls back to net income where no operating-income series is filed. Unassessable companies 36 → 29; eligible 238 of 500 (48%). **Ported into the Vantage repository as its source of truth; section 6 reduced to UI principles only — the detailed interface spec is now a separate document, written after Stage 3.** |
| v0.6 | 29 Aug 2026 | Capital-intensive track (telecom/cable/media, ROE 10%) and the sector shock-year rule. Energy 5→10 and Comm Services 4→10 eligible. Full-500: 230 of 500 (46%) eligible. |
| v0.5 | 29 Aug 2026 | Utilities track added (ROE 8%, operating cash flow replaces FCF, coverage 2.5×) — utilities went from 1/31 to 17/31 eligible. Canonical per-track gate table added. Full-500: 219 of 500 (44%). |
| v0.4 | 29 Aug 2026 | Four-way grading (pass / near-pass / near-fail / fail) with a 15% proportional band. Watchlist tiers and the exceptions mechanism. First full-500 run: 203 eligible. |
| v0.3 | 28 Aug 2026 | Gates rebuilt after live validation: ROIC → return on assets with an improvement clause, gross → operating margin, coverage-first solvency. Financials track (ROE). Golden set established. |
| v0.2 | 28 Aug 2026 | Scoped to S&P 500. Tag-coverage audit across all 500. Institutional ownership tested and rejected; volume and short interest adopted. |
| v0.1 | 28 Aug 2026 | Initial three-stage funnel concept, thresholds proposed from sampled distributions. |

The funnel is complete at two stages. There is no Stage 3 and none is
planned — see section 5 for why.

---

## 1. The thesis

The goal is not to rank 500 stocks by an upside number. It is to maintain
a small, slow-changing watchlist of companies worth owning, and to be
told when one of them moves a long way from where it usually trades.

Quality is not a factor to be traded off against cheapness. It is a
precondition. A mediocre company that has fallen a long way must never
outrank an excellent one that has fallen a little.

```
STAGE 1 — QUALITY GATE          hard pass/fail
500 S&P constituents  ->  258 that clear every bar
Recomputed quarterly, on audited filings.
        |
        v
STAGE 2 — BELOW NORMAL          % below where it usually trades
Of those, which are trading well below their own normal today?
Recomputed daily, on prices.       ->  ~16, ranked
        |
        v
YOU                              read the company
Links out to the sites that do news, earnings and filings properly.
```

Stage 1 answers *"would I ever own this?"* Stage 2 answers *"has it moved
far from where it usually trades?"* Neither answers *"should I buy it"* —
that is a judgement made by a person reading about the business, and the
funnel's job is to get them to the right sixteen companies.

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

So the constraint is not Stage 1. It is that the S&P 500's membership
rules do quality work that filings alone cannot reproduce, and that a
wider universe would surface names too illiquid to accumulate. Widening
later is a configuration change plus a liquidity gate, not a rewrite.

### Sources

| Source | Used for | Cost | Why this one |
|---|---|---|---|
| SEC EDGAR XBRL API | Stage 1 fundamentals | Free, no key | Audited, as-filed, multi-year. The primary source every aggregator derives from. Verified: returns 6+ years of annual figures per concept. |
| yfinance | Prices, market cap | Free | Fine for prices; not trusted for fundamentals where EDGAR exists. |

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
| **4 · Debt serviceable** | Coverage ≥ 4×, or **≥ 2.5× where operating income has not fallen more than 10% in a year**; fallback equity/assets ≥ 10% | Same, fallback ≥ 8% | Same as standard | Same as standard |
| **5 · Margin durable** | Latest operating margin ≥ 70% of its trailing 3-year average | Same | Same | Same |
| **6 · Revenue durability** | Passes outright if 5y revenue CAGR ≥ 0; otherwise latest revenue ≥ its own trailing 3-year average | Same | Same | Same |

Sector-wide shock years are excluded from Gate 1 on **every** track.

Three sector-specific values in total, across two gates. Everything else
is universal. Each of the three changes **what is measured** to fit how a
business works, which §3.2 permits. A fourth — the utility coverage bar —
was removed in v2.14 because it changed the **pass line** instead; the
discount it granted is now earned by measured stability, on any track.

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

| Tier | Meaning | Goes to Stage 2? |
|---|---|---|
| **PASS** | Every gate cleared. A near-pass counts as a pass. | yes |
| **BORDERLINE** | Exactly one near-fail, nothing worse. | yes |
| **REJECTED** | Any outright fail, or two or more near-fails. | no |
| **CANNOT ASSESS** | Fewer than 4 of the 6 gates evaluable. | no |

The tier travels with the company rather than being collapsed away, so
the interface can always show whether a name is on the list cleanly,
barely, or by override — and Stage 2 still gets the definite list it
needs to run on.

#### There is no minimum number of YEARS

The floor counts gates, not years of filings. Considered on 30 Aug 2026
and deliberately left alone.

The case for a minimum was TKO Group: PASS on a four-year series whose
interest coverage ran 3.9x, 1.6x, **0.1x**, 4.1x, with return on equity
negative in that same third year. A company clearing on the strength of
its newest year is exactly what a durability screen should be suspicious
of.

Both instruments that would catch it catch better companies first.

**Years of filings is not company age.** Eleven companies carry a
four-year series; five of them PASS, and three are Honeywell, Ross Stores
and CRH. Honeywell is not a young company — its *series* is short because
of which tag chain its coverage figures come from, while its own gates
read `net income positive 5/5` and `revenue grew 2.1% a year over 5y`. A
minimum-years rule measures **tag coverage, not history**, and rejects
Honeywell and Ross Stores for a filing quirk.

**Volatility catches the banks.** TKO's coverage does swing hardest, a
41x range. Immediately behind it sit PNC, USB, BAC and JPM at 14-24x —
where interest coverage is a rate-cycle artifact and close to meaningless,
which is why §3.16 puts them on the financial track in the first place.

**What already catches TKO.** Gate 4 grades it **near-pass**, not a clean
pass — 4.1x against a 4.0x bar — and it carries `at_risk` naming that
gate, so the page shows it flagged with the gate to watch. Resting on one
near-pass is not itself unusual: 48 PASS companies do.

Revisit if the screen ever admits a company whose short record is *not*
already marked near-pass or at-risk on the gate that its newest year
carries. That would be the case this reasoning does not cover.

#### There is no exceptions mechanism

One existed until v2.3 and was removed. It could relabel a named
near-fail as EXCEPTION instead of BORDERLINE, and did nothing else —
both tiers were already eligible and treated identically everywhere
downstream — so it changed no outcome, which
[tenet 4](../TENETS.md) does not allow.

It also never covered the case that creates pressure to move a bar: a
company you believe in that is **REJECTED**. An exception could only
rescue a *near*-fail, and a single near-fail already yields BORDERLINE,
which already passes through. The mechanism was solving a problem
BORDERLINE had solved already.

So the rule is now absolute: **a company clears the bar or it does not.**
The verdict does not depend on which company it is — `decide()` returns
the same tier whatever ticker it is handed.

#### CANNOT ASSESS exists because of a real near-miss

An early version let a company pass by *failing nothing* — which meant
Exxon passed having been evaluated on zero gates, because
none of its data was reachable. That is the worst failure mode
available: it silently admits exactly the companies you know least about.
Eligibility now requires being measurable on at least 4 of the 5
gates.

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
stable = operating income never fell more than 10% year-on-year
         across the window (needs 4+ years, every one positive)

if InterestExpense present:
    PASS if OperatingIncomeLoss / |InterestExpense| >= (2.5 if stable else 4)
else:
    PASS if StockholdersEquity / Assets >= 0.10              # 0.08 financials
```

**The discount is earned, not assigned.** Until v2.14 the lower bar was
given to utilities as a sector. That was **bar-fitting**, which §3.2
forbids, and its origin says so plainly: v0.5 lowered the bar from 4.0x
to 2.5x when 30 of 31 utilities were failing. Measured on the figure the
gate actually uses — the latest year — 4.0x sits at the 90th percentile
of utilities against the 20th of standard companies.

The lower bar has a real justification; it was simply attached to the
wrong thing. Earnings that do not fall need less headroom to service
debt, and that is a claim about a business model, which §3.2 permits.
Measured across the index:

| Track | median swing (CoV) | median worst 1-year fall | ever fell >25% |
|---|---|---|---|
| capital-intensive | 32.0% | −11.2% | 38% |
| financial | 20.0% | −13.6% | 38% |
| standard | 22.8% | −15.2% | 36% |
| **utility** | **16.5%** | **−0.3%** | **16%** |

The median utility has effectively never had a down year — so utilities
still take the discount, but **through the property rather than instead
of it**: 66% of them qualify against 34% of standard companies. NRG,
whose operating income fell 80% in 2023, no longer gets one for its
label; FISV, GEN, OKE and IQV now can.

Of 392 companies filing an interest tag, 34 sit in the 2.5–4.0x band
where the rule decides anything, and 12 of those take the discount.

**The −10% threshold is not new.** Stage 3 gate 2 already uses it for
this exact quantity, measured across 11,536 year-on-year quarter pairs
(§5.3). It is anchored between the two populations above: the standard
track's median worst year is −15.2%, the utility track's −0.3%. It is
still a judgement, and the data has no natural break — companies newly
passing gate 4 climb 3 → 4 → 5 → 7 → 9 as the line loosens from −5% to
−25%. Recorded so the next reader can see what the choice bought.

**Measured annually, over the gate window — four comparisons.** That is
thin, and stated rather than hidden. Stage 1 reads 10-Ks only: a
quarterly version would give ~16 observations and be far more current,
but quarterlies are reviewed rather than audited, and a Stage 1 verdict
says what the **audited** record shows. Revisit if four comparisons prove
too few to separate steady earnings from lucky ones.

**It fails safe.** Fewer than four years, a missing series, or any loss
year means not stable, so the strict 4.0x applies. The discount is never
granted on absent evidence.

**Why the other gates do not already cover this.** Operating income is
read by three of the six gates and none of them sees a fall. Gate 1 tests its
**sign** — NRG's collapse to $0.40bn stayed positive and passed. Gate 5
tests the **latest year's margin** against a 3-year average, so income
and revenue falling together leaves it flat, and a collapse in the middle
of the window that has since recovered is invisible. Gate 4 tests a
**single year's** ability to pay interest. Gate 5 asks *is profitability
holding up now*; this asks *did earnings ever fall hard*. Same input,
different questions.

**The 4.0x base bar itself has no recorded derivation.** It appears in
v0.3 as "coverage-first solvency" with no measurement behind it in this
document, the build log, or the code. It means interest consumes at most
25% of operating income, which is defensible, but it was inherited rather
than chosen. Raising it to hit a target percentile would be the same
error this section just removed — a bar fitted to a population rather
than to what is safe. Open question, tracked separately.

**Why coverage leads.** It asks the question that matters — can earnings
pay the interest? — rather than merely how much is owed. Equity-to-assets
alone failed Apple (15.6%) and GE (16.2%) for buybacks and restructuring,
not for any quality problem. Leverage is not a defect if earnings
comfortably service it.

**The displayed label follows whichever test ran.** Because gate 4 is
two different tests, one name cannot honestly describe both: the page
says *"Can cover its interest"* where coverage was used and *"Not
overloaded with debt"* where the equity/assets fallback was. The earlier
single label, *"Debt under control"*, claimed a leverage check for
companies whose debt levels were never examined.

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

### 3.14 Gate 6 — Revenue durability *(conditional)*

```python
if 5-year revenue CAGR >= 0:
    PASS                                    # growing over the window
else:
    PASS if latest revenue / its own 3-year average >= 1.00
```

**Why the funnel needed this.** Gates 1-5 test whether a business is
SOUND. None of them tests whether it is SHRINKING. Measured across the
262 eligible on 29 Aug 2026, **41 (16%) were flat or shrinking and passed
every gate** — Blackstone's revenue had fallen 10.6% a year for four
years and read PASS, because falling revenue with intact margins,
returns, cash flow and coverage clears all five.

It is not a restatement of an existing gate. Rank correlation of the
revenue measure against what the others actually compute:

| against | r |
|---|---|
| Gate 2 · return on capital | +0.14 |
| Gate 5 · operating margin | +0.17 |
| Gate 4 · interest coverage | +0.06 |

**Why the CAGR condition, and why it is not optional.** Neither view
works alone; their AGREEMENT is the signal. Three formulations were
measured — 5-year CAGR, latest-vs-own-3-year-average, and worst single
year — and each alone conflates decay with the cycle:

| | cagr | vs 3y avg | worst yr | what it is |
|---|---|---|---|---|
| EXPD | −9.5% | 0.90 | −45.5% | genuine decay |
| CHRW | −8.4% | 0.81 | −28.7% | genuine decay |
| NKE | −0.2% | 0.93 | −9.8% | real deterioration — **CAGR misses it entirely** |
| BX | −10.6% | **1.46** | −62.3% | lumpy fees, currently 46% ABOVE its own average |
| CVX | **+4.3%** | 0.88 | — | cyclical trough |

Requiring both to be negative excludes every cyclical in the index
automatically — Chevron, Exxon, Marathon, EOG, Paccar, Old Dominion,
NXP, CF all grew over five years and are merely below their own
three-year average today. Worst-single-year was measured and discarded:
it flags 33 names dominated by exactly those energy cyclicals, so it
measures the cycle rather than decay.

**Why the bar is 1.00 and not 0.95.** 1.00 is the company's own
three-year average — a natural reference point, not a number reverse-
engineered from which companies it catches. At 0.95 the gate rejected
nobody: the ±15% band put the fail line at 0.807 and the worst name in
the index (CHRW at 0.8114) missed it by four thousandths, making the
gate purely cosmetic. At 1.00 it rejects CHRW, HPQ and TGT and marks
nine more, including Nike, whose five-year record independently shows
return on assets collapsing 13.9% → 8.0%.

**Known false positive.** Divestitures read as decline — Kimberly-Clark
at 0.91 sold businesses rather than lost them. No formulation separates
a sale from a fall without reading the filings, and this is recorded
rather than engineered around.

**The evaluability floor stays at 4**, not 5. It is an absolute minimum
of substantive evidence, not a proportion of the gates that happen to
exist; raising it alongside a new gate would silently reject companies
for a reason unrelated to their quality.

### 3.15 The removed liquidity gate

A sixth gate required median daily dollar volume ≥ $25M. It was **removed**.

Measured across the full index, it rejected **zero of 500 companies**. It
was retained only "so the universe can widen later without surfacing
names you cannot actually buy" — a check earning its place from a future
that has not arrived. [Tenet 4](../TENETS.md) requires a check to change
outcomes or be cut, and [tenet 2](../TENETS.md) rules out the fallback of
keeping it as a displayed fact.

Rebuild it if and when the universe widens beyond the S&P 500, where
every constituent clears the bar comfortably by construction.

### 3.16 Sector handling

| Track | Count | Treatment |
|---|---|---|
| Standard | 336 | All six tests as written. |
| Financials | 75 + 7 | Gate 2 uses return on equity; Gate 4's fallback bar is 8%; Gate 1 allows one negative year and falls back to net income where no operating-income series is filed. The 7 are health insurers (UNH, ELV, CI, HUM, CNC, MOH, CVS) that the index files under Health Care but which are insurance companies — premiums in, claims out, large investment float. Named explicitly: matching on company name wrongly swept in hospital chains, a drug distributor and a device maker. |
| Capital-intensive | 21 | Telecom, cable, media. Asset-heavy so return on assets misreads them, but they generate strong free cash flow — so Gate 2 alone changes, to ROE ≥ 10%. |
| Utilities | 31 | Gate 2 → ROE ≥ 8% (regulator-allowed ROE runs 9–10.5%); Gate 3 → operating cash flow, since utility free cash flow is negative by design; Gate 4 → coverage ≥ 2.5×. |
| REITs | 30 | Not assessed by these gates — see below. |

**REITs are excluded, and the page says so.** The gates never run on
them: a REIT is judged on funds from operations and must pay out roughly
90% of its income, so the cash-generation and margin tests misread it
structurally. **The scan therefore covers 470 companies, not 500** — a
sentence the page states outright, because "all 500 are tested" was on it
for a while and was untrue.

The intended fix is a second, FFO-based track (FFO growth, debt/EBITDA,
occupancy trend) with its own watchlist. **It has not been built**, and
until it is, "excluded" is the honest word. Earlier versions of this
document called it "a second watchlist, not an exclusion" — which
described an intention rather than the code.

> **Honesty requirement:** the interface must state how many companies
> were excluded for lack of a valid test, separately from those that
> failed one. Those are different facts and must not be merged.

### 3.17 Data plumbing — six bugs that would have silently corrupted results

None of these are visible from reading a spec. All were found by running
the gates against real filings, and each would have produced confident,
wrong answers.

| Problem | What it did | Fix |
|---|---|---|
| **No operating-income line** | JPMorgan, Berkshire, Lilly and J&J all went unassessable at once — four sectors, one cause. Banks and insurers have no meaningful "revenue minus operating costs" subtotal, because interest *is* the business; much of pharma goes straight to pre-tax income. | Fall back to pre-tax income. Imperfect (it includes non-operating items) but far better than not assessing them. |
| **Figures split across tags** | J&J reports pre-tax income as Domestic and Foreign — 13 years each — and never files a usable combined figure. | Sum the component tags when the total is missing (`SUM_PARTS`). |
| **Stale series** | Mastercard's `NetIncomeLoss` stops at 2013; modern years use another tag. The code was about to score it on decade-old figures and call the answer current. | A chain entry only qualifies if it is long enough **and** reaches the present (`min_recent_year`). |
| **A whole stage that never ran** | Stage 3's workflow step carried no `env:` block, so `SEC_USER_AGENT` was unset and `run_stage3.py` died on its first EDGAR request in **every CI run since the stage shipped**. `continue-on-error: true` reported the step green. It stayed invisible for nine days because `scripts/*_results.json` are gitignored and the page was being rebuilt locally, where the variable is set — so every published page carrying Stage 3 data had been built by hand, and CI had never produced any. The first CI-built page after Stage 3 shipped went out with the cheapness column blank for all 470 companies. | The step gets the secret, as Stage 1 always had. More importantly the publish guard now checks Stage 3's OUTPUT: it validated Stage 1 and Stage 2 only, so an entirely absent stage passed a check named *refuse to publish a bad scan*. It now floors on readings among eligible companies at 80%, leaving room for the six that legitimately have none (§5.3). Verified both ways before shipping — 0 of 260 blocks, 254 of 260 publishes. **A step allowed to fail softly must be judged on its output, never its exit code.** |
| **A quarter posing as a year** | A 10-K carries the quarters inside it as well as the year, and some filers tag those `fp=FY`. Accenture's fiscal-2025 filing holds both `2024-09-01..2025-08-31` ($10.23B, 364 days) and `2024-12-01..2025-02-28` ($2.24B, 89 days), filed the same day — the tie broke on JSON ordering and the quarter won. Its return on assets read 2.7% instead of 12.4%. | Duration facts must span **350-380 days**, wide enough for 52- and 53-week fiscal calendars. Instant facts carry no start date and are exempt. The rule is pinned by `tests/test_whole_years.py`, which replays this exact filing — the 89-day quarter listed first, both filed the same day — and fails if the quarter ever wins again. The golden set cannot do this job: none of its seventeen anchors was affected, so all seventeen passed both before and after the fix. |
| **Orphaned history** | A 2025 reorganisation moved Exxon to a new filer ID with 94 tags and zero annual history; its real 19-year record sits under the predecessor CIK. The successor's record lists no former names, so nothing links them. | An explicit predecessor map (`PREDECESSOR_CIK`). Named rather than fuzzy-matched, so it can never attach the wrong company's accounts. |

### 3.18 The regression test

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

### 3.19 Full-index result

Measured across all 500 from this repository on 30 Aug 2026, with gate 6
active and the frame-filter, freshest-tag and part-year defects fixed:

| Tier | Count | Share |
|---|---|---|
| PASS | 209 | 41.8% |
| BORDERLINE | 51 | 10.2% |
| REJECTED | 194 | 38.8% |
| CANNOT ASSESS | 16 | 3.2% |
| REIT (not assessed) | 30 | 6.0% |
| **Eligible for Stage 2** | **259** | **52%** |

Which gate does the rejecting:

| Gate | Outright fails | Near-fails |
|---|---|---|
| 1 · Sustained profit | 70 | 0 |
| 2 · Return on capital | 126 | 23 |
| 3 · Cumulative 5y FCF | 24 | 0 |
| 4 · Debt serviceable | 68 | 27 |
| 5 · Op margin durable | 68 | 13 |
| 6 · Revenue durability | 12 | 36 |

By sector:

| Sector | Eligible | of | Pass | Borderline | Rejected | Cannot assess |
|---|---|---|---|---|---|---|
| Financials | 52 | 76 | 43 | 9 | 23 | 1 |
| Industrials | 51 | 83 | 42 | 9 | 28 | 4 |
| Information Technology | 34 | 73 | 31 | 3 | 37 | 2 |
| Health Care | 31 | 59 | 26 | 5 | 27 | 1 |
| Consumer Discretionary | 26 | 47 | 23 | 3 | 19 | 2 |
| Utilities | 20 | 31 | 10 | 10 | 11 | 0 |
| Consumer Staples | 14 | 34 | 9 | 5 | 18 | 2 |
| Energy | 11 | 21 | 5 | 6 | 9 | 1 |
| Communication Services | 11 | 21 | 11 | 0 | 8 | 2 |
| Materials | 10 | 25 | 9 | 1 | 14 | 1 |
| Real Estate | — | 30 | — | — | — | — |

**What gate 6 moved.** Eligible 262 to 260. CHRW, HPQ and TGT are
rejected; fifteen more drop from PASS to BORDERLINE. EIX becomes
*eligible* — a sixth evaluable gate lifts companies over the
four-gate floor, so adding a gate made two companies assessable rather
than fewer, and CANNOT ASSESS fell 18 to 16.

**What the earlier data fixes moved.** The frame-filter and freshest-tag fixes
took eligible from 239 to 258 and CANNOT ASSESS from 29 to 19, because
the gates finally read the newest filed year. The part-year fix then
moved four more: D and SO to BORDERLINE, TKO and URI to PASS, for 262
eligible and 18 unassessable. That last correction could only ever run
one way — a part-year profit measured against a full-year balance sheet
always understates — so no company lost its place.

None of this is uniformly generous. Gate 4 fails went 57 to 73 before
settling at 68, and Gate 1 fails 68 to 71 and back to 70: the data is
not kinder, it is simply *current* and whole.

Comparisons against runs made before v1.0 are not meaningful: those
scored a different five-year window.

---

## 4. Stage 2 — how far below its own normal

Applies to every Stage 1 PASS and BORDERLINE — the tier carries through
so the interface can show it, but both are scored.
Answers: **how far below its own normal is this today?**

"Its own normal" means the company's own trading history, not a
valuation multiple and not a comparison to other companies. A P/E screen
here would fight the funnel by rejecting the very below-normal figures it exists
to find.

### 4.1 The calculation

```python
d_ma200 = (SMA200 - price) / SMA200     # below its long-run normal
d_ma50  = (SMA50  - price) / SMA50      # below its recent normal

BelowNormal = 0.60 * d_ma200 + 0.40 * d_ma50        # a real percentage
Flagged     = BelowNormal >= 0.10                    # absolute, cohort-free
```

Two components, both measured the same way, both reported as real
percentages. A company at `BelowNormal = 0.187` is *18.7% below its own
normal* — a figure that means the same thing today, next quarter, and
against any watchlist.

Names are ordered by `BelowNormal`. There is no percentile and no
standardisation; §4.3 explains why both were removed.

### 4.2 Why these two, and not the 52-week high or the analyst target

Four candidate components were measured across all 500 constituents on
29 Aug 2026. Rank correlation, measured on the then-eligible 239 (the
list is 258 after the v1.0 data fixes; the correlations were not
re-measured, and the design conclusion does not turn on the difference):

| | d_ma200 | d_ma50 | d_high | d_tgt |
|---|---|---|---|---|
| **d_ma200** | 1.00 | 0.53 | **0.74** | 0.43 |
| **d_ma50** | 0.53 | 1.00 | 0.43 | 0.57 |
| **d_high** | 0.74 | 0.43 | 1.00 | 0.46 |
| **d_tgt** | 0.43 | 0.57 | 0.46 | 1.00 |

**The two moving averages are kept because they are not redundant.** At
0.53 they carry substantially different information — a prediction that
they would correlate above 0.8 was made before measuring and was wrong.

**The 52-week high is removed entirely.** It is the most redundant
component in the set (0.74 with the 200-day), and its distinctive part is
contaminated: distance from a 52-week high is heavily determined by
whether the stock had a *spike* in the last year. A company that popped
on a takeover rumour ten months ago and drifted back reads as "40% below
its 52-week high" while trading exactly at its own normal. That is a
volatile stock, not one trading below its normal.

v0.9 dropped it from the score but kept it as displayed context. v1.0
removes it altogether, under [tenet 2](../TENETS.md): showing "44% below
its 52-week high" beside "18.7% below its own normal" invites a reader to
weight it themselves, inconsistently, and to reach for the larger figure.
"Keep it as context" was a way of avoiding the decision.

It survives in exactly one place — the Stage 2 validation suite uses it
as an *independent* sanity anchor ("a company at its 52-week high must
not read as below normal"), which is what catches a sign inversion. Tenet 2
governs what reaches the reader, not internal values a test relies on.

**The analyst target is dropped entirely.** It is not a measure of
"cheap versus its own normal" at all; it is an outside opinion on whether
a fall is justified. v0.9 moved it to Stage 3; v2.0 removed it with that
stage, on the grounds that it is **circular** — targets lag price, so a
fall mechanically widens the gap, and the fall itself creates the
evidence that the fall was an overreaction. It also correlates most
strongly with the 50-day (0.57), consistent with being a slow echo of a
move already captured.

Measured, both excluded components are one-directional:

| | |
|---|---|
| Analyst target above current price | 450 of 496 (**90.7%**), median premium **+13.0%** |
| Price below its 52-week high | 486 of 498 (**97.6%**), median **10.3%** below |

Under a percentile design this would be harmless — subtracting a median
removes the level. **Under the absolute threshold adopted in §4.1 it is
decisive:** at the original 30% and 20% weights, those two floors would
have handed every company roughly **5.7 points of score for free**, before
it had fallen at all, and a "10% below normal" bar would be cleared by
stocks trading *above* their moving averages.

### 4.3 Why there is no standardisation and no percentile

The predecessor blended three components at a stated 50/25/25 whose real
influence was ≈36/43/21, because **a component only moves a ranking to
the extent it varies** across the names being ranked. Standardisation —
subtracting the median and dividing by the interquartile range — was the
fix, and it was the right fix *for that blend*, because the components
were measured in incommensurate units.

Removing those components removes the need. `d_ma200` and `d_ma50` are
both "percent below a moving average": same units, comparable spread. A
raw blend is close to honest, and it keeps the score in real percentage
terms.

**The stated weights are still not exactly the effective ones, and this
is disclosed rather than engineered away.** Measured across the 239
eligible, `d_ma200` has an IQR of 15.6 points against `d_ma50`'s 11.0 —
a 1.41× ratio. So:

| stated | effective (200d : 50d) |
|---|---|
| 50/50 | 59 / 41 |
| **60/40** | **68 / 32** |
| 70/30 | 77 / 23 |

**60/40 is adopted, and its real influence is ≈68/32** — measured at
69/31 on the 258-company list after the v1.0 data fixes. The trade is
explicit: standardising would make the weights exact but would destroy
the real-percentage units, and those units are what allow an absolute
threshold — which is what allows the page to say *nothing is more than
10% below normal today*. Honest units were judged worth more than exact weights, and the
gap is stated here rather than hidden.

For calibration: ranking on the 200-day alone changes only 2 of the top
20 names. The weighting is not a sensitive parameter and should not be
tuned further.

### 4.4 Why an absolute threshold, not a percentile rank

A percentile always has a 99th percentile. A percentile-ranked score
would nominate a most-below normal company every single day, including days
when all 239 sit at their highs — manufacturing a daily recommendation
out of nothing. That directly contradicts §6 principle 2.

An absolute bar can return zero. Measured across the eligible list on
29 Aug 2026 — a period when the median eligible company was trading
**4.4% above** its own normal:

| Bar | Companies of 258 |
|---|---|
| **≥ 10%** | **16 (6.2%)** |

Distribution across the eligible list: median −4.4%, p75 +1.6%,
p90 +6.6%, p95 +12.2%, max +40.5%.

The sixteen that clear it, with the shape of each decline:

| | Below own normal | 200d | 50d | Shape |
|---|---|---|---|---|
| MNST | 40.5% | 40.6% | 40.3% | still falling |
| TTD | 37.4% | 48.2% | 21.2% | stabilising |
| ROL | 23.3% | 31.6% | 11.0% | stabilising |
| PODD | 22.9% | 33.5% | 6.9% | stabilising |
| LII | 21.1% | 21.6% | 20.4% | still falling |
| PNR | 20.7% | 28.2% | 9.4% | stabilising |
| NKE | 18.7% | 25.6% | 8.5% | stabilising |
| ZTS | 16.7% | 27.4% | 0.6% | recovering |
| LULU | 16.2% | 25.5% | 2.2% | recovering |
| ISRG | 14.9% | 21.8% | 4.6% | stabilising |
| DECK | 14.8% | 15.7% | 13.3% | still falling |
| TJX | 12.7% | 13.0% | 12.4% | still falling |
| CHRW | 12.2% | 12.2% | 12.3% | still falling |
| TPR | 11.8% | 10.2% | 14.2% | still falling |
| WMT | 11.2% | 13.0% | 8.4% | stabilising |
| CRH | 10.8% | 14.0% | 5.9% | stabilising |

Eight stabilising, six still falling, two recovering. Two companies
(FDXF, HONA — recent spinoffs) are reported as **insufficient history**
rather than scored.

**10% is adopted.** Sixteen names is a short enough list to read
properly, and the list is ranked, so a reader works down from the top and
stops when they choose. The bar's job is not to pick winners — it is the
point below which you are content not to look.

### 4.5 The shape of the decline

The two averages together carry information neither has alone: **when the
fall happened**. The 50-day average catches up to a new price level in
about two months; the 200-day takes a year. A stock that drops from $100
to $60 and holds:

| | SMA50 | SMA200 | d_ma50 | d_ma200 |
|---|---|---|---|---|
| Day 1 | $100 | $100 | 40% | 40% |
| Day 25 | $80 | $95 | 25% | 37% |
| Day 50 | $60 | $90 | **0%** | 33% |

So both large means the fall is recent or ongoing; a large 200-day with a
small 50-day means it happened months ago and price has settled.

```python
shape_ratio = d_ma50 / d_ma200          # only when d_ma200 > 0
```

| ratio | label | meaning |
|---|---|---|
| ≥ 0.70 | **falling now** | as far below its short average as its long one — the drop is recent or ongoing |
| 0.20 – 0.70 | **fell, now flat** | fell some time ago, price has settled |
| < 0.20 | **fell, now rising** | back at or above its 50-day, climbing |

The labels describe **price behaviour only** and deliberately imply no
judgement. Wording like "high confidence dip" was rejected: Stage 2 has
no idea whether a fall is justified, and a card reading *"high confidence
dip / not worth buying"* would contradict itself.

Their real function is telling you **how much of the story the evidence
has caught up with**. A company that fell three weeks ago has filings,
analyst views and short-interest figures that all predate the fall. One
that fell six months ago does not. That is why the label survives
[tenet 4](../TENETS.md) — it changes what a reader trusts.

This is a **label, not a score adjustment** — it annotates the ranking
without altering it. It matters because the thesis is temporary shocks:
"still falling" is a shock in progress with an unknown bottom,
"stabilising" is one that can now be assessed, and "recovering" means the
opportunity has largely passed.

Observed on the sixteen names clearing the bar: MNST at ratio 0.99 is
falling right now; NKE at 0.33 fell and has steadied; ZTS at 0.02 has
been flat for months. A single number cannot distinguish those.

A ratio above 1.0 (the 50-day gap exceeding the 200-day gap) means the
decline is accelerating, and falls inside "still falling".

### 4.6 What is shown alongside the score

| Field | Why it is there |
|---|---|
| **Below normal %** | The ranking variable |
| **Shape label** | Whether the evidence has caught up with the fall |
| **Market cap** | Plays no part in gating or ranking, but changes what a reader would do, so [tenet 2](../TENETS.md) makes it a driver. A **sortable column, never a grouping** — grouping by size would systematically bury the unfamiliar names the screen exists to surface. Measured on the current sixteen: $6.4B to $820B, median $25B. |
| **Yahoo and Google Finance links** | Where the actual research happens. The funnel's job ends at getting you to the right sixteen companies. |

### 4.7 Liquidity — removed

Stage 2 previously enforced Gate 6, being the one Stage 1 gate that
needed prices rather than filings. That gate is gone (§3.15), and median
dollar volume is no longer computed or displayed.

### 4.8 Data source and its known weaknesses

Prices come from Yahoo Finance via the unofficial `yfinance` library. It
is free and adequate for prices, and it is **not** trusted for
fundamentals, which come from EDGAR. It can rate-limit and can return
empty frames.

**Prices must be split- and dividend-adjusted.** This is a correctness
requirement, not a preference. On raw prices a 2-for-1 stock split makes
a company appear to have fallen 50% overnight, and every ex-dividend date
produces a small false below-normal figure. Both would be scored as opportunities.
Averages are computed from adjusted closing prices throughout, and the
52-week high likewise, so that a price and its own history are always on
the same basis.

**Definitions, stated so they cannot drift:** `SMA200` is the simple mean
of the last 200 adjusted closes, `SMA50` the last 50; `high52` is the
highest adjusted close in the last 252 trading days. Trading days, not
calendar days.

The predecessor once published a near-empty scan and blanked its own
page. Stage 2 therefore **validates before it writes**, and refuses to
publish rather than publish something wrong:

| Check | Bar |
|---|---|
| Tickers returning data | ≥ 95% |
| Trading days per ticker | ≥ 200 (else "insufficient history", never scored as flat) |
| Prices | no zero or negative values |
| Most recent bar | within 5 calendar days |

Any failure aborts the run and leaves the previous results in place.

Companies with under 200 trading days of history are marked
**insufficient history** and are never scored as though they were
trading flat — the same distinction Stage 1 draws between CANNOT ASSESS
and REJECTED.

### 4.9 Scope of computation

Components are computed for **all 500 constituents**, not just the 239
eligible, because the ticker inspector (§6.7) must be able to answer for
a rejected company too. Only the eligible list is ranked and only it can
be flagged as more than 10% below normal.

### 4.10 How Stage 2 is validated

Stage 2 has no golden set — there is no independently known right answer
for "how below normal is this". Validation is therefore mechanical:

1. **Arithmetic check.** Recompute one company's 200-day average by hand
   from raw closes and confirm it matches to the cent.
2. **Sanity anchors.** A stock at its 52-week high must score at or below
   zero; one trading far under both averages must score near the top. A
   violation means a sign is inverted.
3. **Effective-weight check.** Measure the realised influence split and
   confirm it matches the ≈68/32 stated in §4.3 (69/31 on the current
   list). This is the direct test
   for the bug that broke the predecessor.
4. **Shape-label check.** Confirm the three labels partition the flagged
   list and that each example behaves as §4.5 describes.
5. **Second-source spot check.** Verify three companies' prices against a
   source other than yfinance, so the data is known to be *right*, not
   merely *present*.

---

## 5. Stage 3 — is this fall an opportunity or a warning?

*Specified 30 Aug 2026. Annotates Stage 2's ranking; never reorders,
filters or scores it.*

### 5.1 The design that was cancelled, and why it stays on record

A third stage was specified through v1.0: six signals — analyst
conviction, fundamental trajectory, sector context, distance from failing
a gate, volume character, short interest — each scored −1/0/+1 and summed
to a −6…+6 corroboration score mapped to ACT / WATCH / AVOID.

**It was removed before being built.** The record matters more than the
design, because every signal failed a test:

| Signal | What measurement showed |
|---|---|
| Volume character | Awarded +1 to **89%** of the index and −1 to nobody. The thresholds came from an eight-name sample. |
| Analyst price target | **Circular.** Targets lag price, so a fall mechanically widens the gap — the fall creates the evidence that the fall was an overreaction. |
| P/E versus its own range | **Circular in the same way.** New price over old earnings always looks cheap immediately after a fall. |
| Sector context | Real but not decisive; the sign was arguable in both directions. |
| Short interest | Real, but reported twice monthly with a 2–3 week lag and contaminated by arbitrage positioning. |
| Fundamental trajectory | Real, but quarterly filings lag by up to three months. |

Two survived, and both **lag the event they are meant to judge**. That is
the fatal problem: a reader on a finance site looking at yesterday's news
has strictly better information than any lagged proxy we could compute.

The decisive argument was simpler still. **Stages 1 and 2 already reduce
500 companies to roughly 16, ranked.** A reader deep-dives the top few
and ignores the rest — so the ranking is the triage, and a third stage
changes no outcome. [Tenet 4](../TENETS.md) applies to an entire stage as
readily as to a single check.

What replaced it: **links out** to the sites that do news, earnings and
filings properly, plus the one thing they cannot provide — which Stage 1
gate a company is closest to failing, and how stale the filed data behind
that verdict is.

**When to revisit.** If the flagged list routinely runs long enough that
ranking stops being sufficient triage, or if a lagging signal can be
replaced by a current one. Not before — building for a future that has
not arrived is what removed the liquidity gate.

### 5.2 Why it was reopened

**The second revisit condition was met.** The fatal objection to the
cancelled design was that every surviving signal LAGGED the event it
judged. Stage 1 reads annual 10-Ks that are 2-12 months old; Stage 2
reads today's price; nothing looked at the months between. Measured
across the 262 eligible, the most recent QUARTER a company has filed is
a median of **60 days old** (p90 151 days), with **260 of 262 covered**.
That is a current signal replacing a lagging one, which is the condition
this spec set for itself.

**The triage argument does not apply.** Stage 3 was cancelled partly
because ranking 500 companies down to ~16 is already sufficient triage.
That remains true, and Stage 3 does not add triage — it does not
reorder, filter, score or rank anything. It annotates rows the ranking
already chose. A reader still reads the top few.

**The circularity objection, answered with measurement.** §5.1 rejected
"P/E versus its own range" as circular: new price over old earnings
always looks cheap immediately after a fall. That objection is correct
and it is why the cheapness check is not used alone. It is also
testable, and it fails as a general claim: if the measure were purely
mechanical, EVERY name that had fallen would read cheap. Measured on the
17 flagged names, **6 do not** — Walmart is 10.7% below its own normal
price and still trades at a 2.65% earnings yield against its own 3.33%
median, i.e. more expensive than usual despite having fallen. A purely
circular measure cannot produce that.

The residual circularity is real and is precisely what check 2 exists to
catch: Lululemon reads as the CHEAPEST name on the list at +8.51 points,
because its yield is computed on stale annual earnings while its most
recent quarter shows operating income down 37%. That is a value trap,
and the two checks together identify it where either alone would not.

### 5.3 The two gates

Called GATES, matching Stage 1's vocabulary. Both read filed figures
only; nothing is reconstructed.

**Gate 1 — is it cheaper than its own normal?**

```python
yield_now = latest annual EPS / today's price
yield_3y  = median of (EPS / price at that fiscal year end), last 3 years
yield_5y  = same, last 5 years
                                     # PERCENTAGE POINTS, never a ratio
above BOTH medians   -> "cheaper than usual"
below BOTH medians   -> "pricier than usual"
between them         -> "priced about as usual"
```

The threshold is **zero**, which is structural rather than chosen: a
company's own median is the definition of its normal.

**Four years of history is also structural, not a chosen minimum.** With
only three, `history[-3:]` and `history[-5:]` are the SAME LIST, so the
two medians are identical, the windows can never disagree, and *"priced
about as usual"* becomes unreachable — a state that describes 52 of 450
companies today. Four years is the first point at which the two windows
differ and the gate does what it claims. Widening the pairing to (3y, 4y)
changes nothing: at three years those two windows are identical as well.

**The six eligible companies without gate 1**, and why none is fixable:

| | | |
|---|---|---|
| **V**, **BRK-B**, **ERIE** | data absent from the API | All three run multi-class share structures and file EPS **per class**, behind a dimension that the `companyfacts` endpoint omits. Visa files no diluted-EPS or weighted-average-share tag at all; Berkshire's EPS stops at 2013 and its share count at 2014; Erie returns neither. No tag-chain widening reaches figures the endpoint does not carry. |
| **GDDY**, **TKO**, **VLTO** | genuinely three years | GoDaddy does file `EarningsPerShareDiluted`, but exactly three annual facts (2023-2025), carried as comparatives in one filing. TKO and VLTO are recent. |

All six still receive gate 2's profit reading, so the page states *"no
earnings history"* beside what **is** known rather than showing a blank.
Checked against EDGAR on 30 Aug 2026 and closed: the constraint is the
filings, not the reader.

**Points, not a ratio.** A ratio explodes as historical earnings approach
zero — Insulet's own-normal P/E computes to 595x and The Trade Desk reads
"+1093% cheaper", both arithmetic rather than information. Inverting P/E
to a yield does NOT fix this; it moves the explosion into the ratio.
Differencing two yields is bounded: across 249 companies the spread runs
-28.4pt to +15.2pt, median -0.5pt.

**Both windows, and they must agree.** Measured, 3 and 5 years disagree
for only 8% of the index — but for **4 of the 16 published names**
(TJX, WMT, CRH, TPR), all four flipping from "not cheaper" to "cheaper".
A quarter of what the reader sees would be decided by a window choice
with no principled reason to prefer either.

Disagreement is not indecision, and "between the two medians" is the same
statement as "the two windows disagree" — if today's yield is above one
median and below the other it lies between them by definition. So the
three labels answer one question: *where does today sit relative to the
band its own history spans?*

| | 3y median | today | 5y median | |
|---|---|---|---|---|
| NKE | 4.13% | **5.30%** | 3.69% | above both -> cheaper than usual |
| GNRC | 2.53% | **1.46%** | 2.53% | below both -> pricier than usual |
| WMT | 2.49% | **2.65%** | 3.09% | between -> priced about as usual |
| TPR | 4.98% | **5.79%** | 8.48% | between, on a very wide band |

Requiring agreement also removes false precision at the boundary: TJX at
-0.05pt against a single median is a coin flip reported as a verdict.

**Gate 2 — is the business still intact?**

```python
quarterly operating income vs the SAME quarter one year earlier
FIRES when TWO CONSECUTIVE quarters are below -10%
```

**Why two consecutive, and not one at a bigger number.** Measured across
**11,536 year-on-year quarter pairs**, a single quarter is never rare:

| fall of at least | share of quarters | companies that have ever had one |
|---|---|---|
| -10% | 19.7% | — |
| -20% | 12.5% | **92%** |
| -30% | 8.6% | 84% |

An earlier draft of this spec set a single-quarter bar at -20% and called
it "material by any reading". **That was wrong** — 92% of companies that
clear six quality gates have had one, roughly every two years. There is
no single-quarter threshold at which the event becomes rare.

Two in a row is 2.3x rarer at EVERY threshold, and it is the difference
between Lululemon (-11.2% then -36.9%) and The Trade Desk (**+22.4%**
then -13.0% — one soft quarter after a strong one). Persistence is what
"deteriorating" means, and no single-quarter rule can express it.

**Three things this gate deliberately does NOT do:**

| Rejected | Why |
|---|---|
| Exclude swings into an operating loss (worse than -100%) | Redundant under a two-quarter rule: it only bites when BOTH quarters breach, and in both such cases (MRK, WAT) the company posted two consecutive operating LOSSES — worth reporting whatever the cause. The panel shows the figures, so a sign-flip reads as one. |
| An annual fallback when the newest period is a fiscal year | 10-Ks do not tag Q4 as a quarter, so for a company just past year end the newest QUARTER is ~6 months old while the newest YEAR is ~3 months. Measured, the annual view detects **nothing** the quarterly rule misses and **loses Nike**, whose full year was flat while its last two quarters fell 29% and 23%. The Q4 gap makes evidence older, not missing. |
| A staleness cutoff | The cases it would exclude (BNY resolving to 2016, ACGL to 2021) are a TAG-SELECTION BUG, not a staleness policy. A cutoff would hide the bug. Show the age instead. |

**Only one judged number exists in Stage 3: -10%.** Zero is structural,
two-consecutive is structural, agreement between windows is structural.

### 5.4 Output — a label, never a verdict

Gate 1's state, with `, profit falling` appended when gate 2 fires:

```
cheaper than usual · priced about as usual · pricier than usual
   +/- ", profit falling"
```

Where one gate is unavailable the label reports only what WAS
established — 14 of 260 have no usable earnings-yield history, 3 have no
usable quarter pair, 2 have neither.

**No confidence figure.** There is no backtest, so any percentage beside
these would be invented. What is shown instead is the evidence and its
AGE — "quarter to 28 Feb 2026, filed 182 days ago" — which degrades
visibly for an old filing. §6 forbids "WARNING" as a word: the funnel
refuses to say whether a fall is good or bad, and a label that judges
would put that judgement back in.

**Stage 3 ANNOTATES Stage 2's ranking.** It never reorders, filters,
scores, or contributes a number to it. If it ever starts influencing the
order it has become Stage 2 and must be resisted. The 52-week high was
removed (§4.2) precisely because a second figure beside the first invites
the reader to weight them inconsistently and reach for the larger.

### 5.5 What it changes today

Two of the sixteen published names:

| | gate 1 | gate 2 | label |
|---|---|---|---|
| LULU | +8.51pt, the cheapest name on the list | -11.2% then -36.9% | cheaper than usual, profit falling |
| NKE | +1.76pt | -29.4% then -23.0% | cheaper than usual, profit falling |

Lululemon reads as the cheapest name on the list *because* its earnings
are collapsing: the yield uses annual earnings while its most recent
quarter is down 37%. That is a value trap neither Stage 1 nor Stage 2 can
see — Stage 1 reads annual filings 2-12 months old, Stage 2 reads only
price.

**Why this design survived when others did not.** Four Stage 1 proposals
were measured and dropped in the same session (gate 6 option B, the
utility coverage bar, a gate 2 deterioration clause, a gate 4 coverage
median). Three died on one finding: **a 3-year window today begins at the
2022-23 inflation peak, so it reads cycle position as decline.** Gate 1
is immune because it REQUIRES the two windows to agree and treats
disagreement as its own answer; gate 2 is immune because a year-on-year
quarter comparison does not depend on where a window starts.

## 6. Interface principles

**The detailed UI specification is a separate document, written after
both stages are built and validated.** This section records only the
principles that constrain it, so that the interface is designed around
real numbers rather than a guess.

1. **The page is one filterable table, and its DEFAULTS carry the
   thesis.** *(Revised v2.9. Through v2.8 this principle read: "It opens
   with an answer, not with filters. Filters are adjustment, not the
   product." The page now opens with filters, and that reversal is
   deliberate — recorded rather than quietly dropped.)*

   Every company Stage 1 assessed is on the page; the quality gate and
   the below-normal bar became filter DEFAULTS rather than a hard cut.
   Nothing is hidden, and the separate ticker inspector is no longer
   needed because every ticker is already present.

   What keeps this from becoming a generic screener is that **a default
   is a claim**. Two defaults are on: quality first, and only show what
   has actually moved. Trend and pricing get filters but NO defaults,
   because defaulting them would claim "still falling is bad" and "not
   cheap is uninteresting" — judgements principle 3 and §4.2 refuse.
   Measured: a trend default drops MNST, the biggest faller on the page;
   a pricing default drops WMT, the fell-but-not-cheap case Stage 3
   exists to surface.
2. **Most days the answer is "nothing is far below normal."** That is a
   useful and honest answer, and the design must make it tolerable rather
   than treating it as an empty state to apologise for.
   The wording matters: **never "on sale"**, which claims the fall is a
   bargain. The figure has no idea whether it is — same reason it is not
   called a discount. Say what is measured: *more than 10% below its own
   normal*.
3. **The name furthest below normal is not automatically the best one.**
   The list is ranked by how far a price has moved, which is not the same
   as how good an opportunity is. The shape label and the at-risk gate
   say so on the card; the rest of that judgement happens off this page,
   which is what the links are for.
4. **Nothing is a black box.** Every threshold shows the company's actual
   value beside the bar it had to clear, so a rejection is a fact the
   reader can disagree with.
   **This means showing inputs and outputs, not internal arithmetic.** A
   company view shows *18.7% below its own normal*, and beneath it the two
   figures it came from — *25.6% below its 200-day, 8.5% below its 50-day*.
   A reader who cares can check the arithmetic; a reader who doesn't is
   not made to read a formula. The weights and the effective-influence
   note in §4.3 belong on a methodology page, one level down — accurate
   and available, never the headline.
   **The weights are never user-adjustable.** A slider invites tuning
   until the answer flatters a prior, which is the exact failure the
   Stage 1 grading design exists to prevent. The predecessor shipped a
   weights slider *and* a methodology page describing the opposite of what
   the weights did; both halves of that were mistakes.
5. **"Closest to failing" is shown per company** — which gate to watch,
   read straight off the grade Stage 1 already assigned. No new
   computation. It is the one fact a finance site cannot provide, because
   it depends on our own bars. Alongside it, **how stale the filed data
   is**: a verdict resting on a year ending in December is blind to
   everything since, and a reader needs to know where our knowledge stops
   and theirs starts.
6. **CANNOT ASSESS is never merged into REJECTED.** No record and a bad
   record are different facts.
7. **Any ticker must be answerable.** Every company Stage 1 assessed is
   a row, so search filters the table rather than a separate inspector
   answering one name at a time. Rejected companies are included, and
   especially so. This is what makes weeks of "nothing far below normal"
   tolerable: the screen may be silent, but the tool never is.

   *(Revised v2.9. Until then this was a dedicated lookup row, which
   became redundant once the table held all 470.)* Whatever Stage 1 did
   not run on, nothing downstream runs on either — so REITs are absent
   entirely rather than appearing with a price and no verdict.
8. **The tier is always visible.** A BORDERLINE name is never shown as a
   clean pass.
9. **There are two pages over one funnel, and neither is a reduced
   version of the other.** `/` is the detailed table; `/simple/` states
   one company per readable sentence for a reader with savings and no
   trading background. They are rendered by the same build from the same
   scan, so they cannot disagree about what the funnel found.

   **Nothing is withheld from the simple page.** Every gate, the
   five-year record and the 52-week scale are one click away, from the
   same `site/detail.js` the detailed page inlines. What differs is the
   way in, not the depth: the simple page asks for no finance vocabulary
   before the reader has seen a company, and puts the detail behind a
   collapsed card instead of in front of them.

   The simple page also carries **colour where the funnel already reaches
   a verdict** — checks passed, direction, cheaper-than-usual, falling
   profit — and never on a price move, because §6.1 refuses to say
   whether a fall is good or bad and a coloured price would say it in
   CSS.
9. **Column widths are set by hand, then frozen.** They are a design
   decision, not an outcome of whichever rows a filter happens to show.
   Left to the browser the table re-sized itself on every click, because
   auto layout measures only the rows currently on screen. The widths in
   the stylesheet were chosen by dragging the real table over the real
   data and reading the numbers off; `table-layout: fixed` then honours
   them literally.

---

### 6.1 Decisions taken while building the page

| Decision | Why |
|---|---|
| **No red or green anywhere** | The funnel deliberately refuses to say whether a fall is good or bad. A screener that colours a 40% fall red has made that judgement in CSS. The shape labels use a filled / hollow / outlined dot — a difference in form, not in moral weight. |
| **A sorted table, not a chart** | At ~16 rows a treemap is a decorated list. A sector treemap was rejected outright: the sixteen span 6 of 11 sectors with two singletons, so most of it would be empty, and *area* — a treemap's dominant visual — would encode market cap, the one variable playing no part in the funnel. |
| **Market cap sortable, never grouping** | It changes what a reader does, so [tenet 2](../TENETS.md) makes it a driver. But grouping by size would bury the unfamiliar names the screen exists to surface. Measured on one day's list: $6.4B to $820B, median $25B — and the name a reader was least likely to recognise was the 4th largest. |
| **Plain English, numbers unchanged** | Gate results are re-worded for a reader without finance vocabulary, carrying every figure through untouched. Where a string does not match its expected shape the raw version is shown rather than a guess, so the page can never invent or mislabel a number. |
| **The empty state replaces the table** | It is behaviour, not an illustration. Showing both at once contradicts the headline. |
| **A 52-week scale, shown not scored** | Three points — low, today, high — at the top of each expanded row, with today's distance from each end. Measured across the 258 eligible, distance above the 52-week low correlates **−0.77** with the below-normal figure and −0.80 with the 200-day component, so as a scoring input it would largely cancel itself out (tenet 4). The residual is real though: TJX and NKE sit *at* their 52-week low while CHRW and TPR have already bounced 23–26% off theirs, on near-identical scores — and the shape label misses it, since both of the latter are *falling now*. Shape dates the current move; distance from the low says how much has already been recovered. Netting the two into one number would lose both. |
| **Endpoint labels below the track, today's price above** | Not decoration. Measured on one day's list, three of sixteen sat *exactly* at their 52-week low, so the price marker lands on the endpoint marker regularly. Same-side labels would collide constantly. The floating price label re-anchors at the extremes so it cannot overflow the track. |
| **Not "upside"** | The gap to the 52-week high is never called upside. The high is the highest price in a year, not a target, and that word would claim it is one — the same objection that removed *discount* and *on sale*. Each distance is measured against the endpoint it names, so the pair is built consistently. |
| **Single theme** | Paper: off-white ground, ink text, hairline rules. A research document, not a trading terminal. |
| **The panel is one implementation, inlined twice** | `site/detail.js` and `site/detail.css` hold the expanded panel — gates, five-year record, 52-week scale — and `build_site.py` inlines both into each page. Copying the panel into a second template would have guaranteed drift: the two pages would agree on the day they shipped and disagree by the second change. Each page stays a single self-contained document, which is what GitHub Pages serves. |
| **The simple page states, the detailed page tabulates** | One sentence per company, generated from the same figures the table shows — *"Monster Beverage passes all six quality checks, is priced 39.9% below its own recent average, and is cheaper than its earnings have historically cost."* No clause asserts anything the detailed page does not evidence. |
| **Frozen column widths, not computed ones** | Three attempts to compute them all failed differently. `table-layout: fixed` with guessed percentages clipped *falling now* mid-word while Research sat twice as wide as two letter badges need. Auto layout fixed the clipping but sized every column to the ~14 rows a filter left on screen, so the whole table shifted on every click. Measuring across all 470 rows at load fixed *that*, and was then redundant the moment the widths were chosen deliberately. The stylesheet is now the single source, and every value in all 470 rows was verified to fit before `fixed` was switched back on. |
| **Long headings wrap; values do not** | A heading that cannot wrap sets a floor wider than any number beneath it, so the column ends up sized by its own label. `% below usual` was holding 123px for values needing 67. The two headings that wrap gave that width back. Values stay on one line wherever they fit — the pair of moving averages was briefly wrapped and did not need to be. |
| **The Stage 3 read may stack** | Its one exception. Three companies show two labels at once (*no earnings history* + *profit falling*), and while the cell was nowrap end to end that pair set a floor no width could get under. Each label still holds together; only the pair breaks. |
| **A `No.` column** | The row's position in the list as currently sorted and filtered — so it renumbers when either changes. Styled muted, because it is a place in a list, not a fact about the company. |
| **The drag tool was removed once it had done its job** | A `?resize=1` mode with drag handles and a read-out panel is how the widths above were arrived at — chosen against the real data rather than argued about in the abstract. It was then deleted rather than left in gated: the widths are settled, so shipping the machinery to every visitor bought nothing. It is in git history at `feb1f97` if a column ever needs re-tuning. |

## 7. Build order

Agreed and not to be reordered:

1. **Stage 1 as a research script — done.** Built, running against live
   EDGAR, 17-company regression test passing.
2. **Run all 500 through Stage 1 — done.** 238 of 500 eligible.
3. **Stage 2** — the below-normal figure.
4. **Stage 3 — cancelled**, see §5.
5. **Write the UI specification and mockups.**
6. **Build the interface last**, once all three stages produce real
   numbers.

**Why the full runs come before any UI.** Every layout decision assumes a
watchlist size. If the real number is 40, the watchlist is a single list
and sector filters are pointless. If it's 300, the gate isn't gating.
Designing the page first means designing around a guess — which is
exactly what went wrong in the predecessor project.

Measured: **258 eligible, of which ~16 are below normal on a given day.**
At that size a sorted table beats any chart. A sector treemap was
considered and rejected: the sixteen span 6 of 11 sectors with two
singletons, so most of it would be empty, and area — a treemap's dominant
visual variable — would encode market cap, the one thing that plays no
part in the funnel.

---

## 8. Open questions

### Settled

- **REITs** — a second watchlist with their own FFO-based gate, not an
  exclusion.
- **Stale watchlist between filings** — real, and now surfaced rather
  than solved. Stage 1 reads annual 10-Ks, so a verdict is 2–12 months
  old depending on the fiscal calendar. Every result therefore states
  which filing it rests on and how many months of business the gates have
  not seen. The recency layer is the reader, on the linked sites.
- **Weeks with nothing flagged** — correct behaviour, made tolerable by
  the ticker inspector.
- **ACT / WATCH / AVOID** — adopted as the shared vocabulary.
- **Institutional ownership %** — tested and rejected.
- **A news-recency signal** — left out of v1. The market signals already
  *are* the recency layer and are more reliable than headlines: volume,
  short interest, analyst revisions and quarterly trajectory all encode
  what the news means without needing to interpret prose. Revisit if the
  six signals prove insufficient.
- **Stage 2's components** — settled by measurement in v0.9. Two moving
  averages; the 52-week high removed entirely; the analyst target
  dropped as circular. See §4.2.
- **Ordering versus triggering** — settled. One absolute number does both
  jobs. A percentile rank was specified through v0.8 and removed because
  it can never return "nothing is far below normal". See §4.4.
- **Standardisation** — settled. Necessary for incommensurate components,
  unnecessary once every component is a percentage below a moving
  average. The residual gap between stated and effective weights is
  disclosed instead. See §4.3.

### Also settled, 29 Aug 2026

All four questions that stood open through v2.2 have been answered.

- **The six gates are right.** They test profitability, returns on
  capital, cash generation, solvency, margin durability and revenue
  durability. *(Revised v2.9. Through v2.8 this read "the five gates" and
  listed growth and valuation as DELIBERATELY ABSENT — "a great business
  can be flat", and "cheapness is Stage 2's job". Both since changed:
  gate 6 added revenue durability in v2.8 after measurement showed 41 of
  262 eligible companies were flat or shrinking while clearing every
  gate, and Stage 3 added valuation in v2.9 — against a company's OWN
  history, never an absolute P/E limit, which is what the original
  objection was actually about.)* A liquidity gate was removed in v1.0
  for rejecting nobody.
- **The "or improving" clause stays as written.** It passes a company on
  trajectory alone, which is what admits Amazon while still rejecting
  Intel decisively. Requiring two consecutive improving years would be
  stricter but slower to recognise a real inflection, and there is no
  evidence the current form lets anything through it shouldn't.
- **The borderline band stays at 15%.** No evidence favours 10% or 20%,
  and moving a threshold without evidence is precisely what
  [tenet 3](../TENETS.md) forbids — it is how the returns bar drifted
  12% → 8% before the grading system existed. If it is ever worth
  settling empirically, the measurement is: how many companies move
  between BORDERLINE and REJECTED at 10 / 15 / 20, and which.
- **No exceptions, for anyone.** The mechanism itself was removed in
  v2.3 — see §3.5. A company clears the bar or it does not.

**There are no open questions.** New ones should be added here with the
measurement that would settle them, not as opinions.

---

## Credits

- **SEC EDGAR XBRL API** — U.S. Securities and Exchange Commission.
  Public-domain filing data. `https://data.sec.gov`
- **S&P 500 constituent list and GICS sector labels** — Wikipedia,
  *List of S&P 500 companies*, CC BY-SA.
- **S&P 500 Quality Index** — S&P Dow Jones Indices. Used only as an
  independent cross-check when assembling the golden set; no index
  methodology or data is reproduced here.
- **yfinance** — Ran Aroussi and contributors, Apache 2.0. An unofficial
  client for Yahoo Finance data; used for prices and analyst figures, not
  for fundamentals. `https://github.com/ranaroussi/yfinance`
- **ASU 2016-01** (equity securities measured at fair value through net
  income) — Financial Accounting Standards Board. The accounting change
  that explains Berkshire's 2022 reported loss.
- No external code was copied into this project.
