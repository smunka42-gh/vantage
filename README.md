# Vantage

**Two ways in, one scan behind both:**

**[smunka42-gh.github.io/vantage](https://smunka42-gh.github.io/vantage/)**

One page, two views of the same list. It opens as a readable statement
per company; a switch above the list shows the same companies as a
table, for scanning and comparing. The switch keeps your filters and
sort, so it changes the arrangement and never which companies are shown.

Neither view is a reduced version of the other. The expanded panel —
every gate, the five-year record, the 52-week scale — is one
implementation inlined into
both, so they cannot drift apart. What differs is the way in, not the
depth.

Finds durably high-quality companies that are trading well below where
they usually trade, and hands you the short list plus links to go read
about them.

Not a ranking of every stock by upside, and not a buy signal. The goal is
a small, slow-changing watchlist of companies worth owning, and a short
daily answer to *"has any of them moved a long way from its own normal?"*
Most days the answer is none, and that is the correct answer.

## The funnel

| Stage | Question | Cadence | Source |
|---|---|---|---|
| **1 · Quality** | Would I ever want to own this? | Quarterly, on filings | SEC EDGAR (audited) |
| **2 · Below normal** | Has it moved a long way from where it usually trades? | Daily, on prices | Yahoo Finance |
| **3 · Opportunity or warning** | Is it cheap, and is the business still intact? | Daily | SEC EDGAR (quarterly) |
| **You** | Is it worth buying? | — | The links the tool hands you |

Stage 1 is a **quality gate**, and the page defaults to showing only what
clears it. It is a filter default rather than a hard cut: every assessed
company is on the page and the filters open it up, because hiding a
company answers no question a reader actually has. Stage 2 is a
percentage, not a verdict.

**Stage 3 was cancelled, then reopened on evidence.** The original
design died because every candidate signal was circular, near-constant,
or lagged the event it judged. The spec set its own condition for
revisiting — *"if a lagging signal can be replaced by a current one"* —
and that was met: quarterly filings are a median 60 days old against
annual filings at 2-12 months. It annotates the ranking; it never
reorders, filters or scores it. See §5 of the spec.

## Status

- **Stage 1 — built.** Six gates across four sector tracks, running
  against live SEC filings, with a 17-company regression test (17/17)
  plus two assertions on the data itself: that it is the newest filed
  year, and that every figure is a whole year rather than a quarter
  posing as one. The gates do not run on REITs, so the scan covers
  **470 of the 500** constituents. Latest full run: 209 pass,
  51 borderline, 194 rejected, 16 without enough filing history —
  **259 eligible**.
- **Stage 2 — built.** Two moving-average components blended as real
  percentages, with an absolute 10% bar so the honest answer on a calm
  day is an empty list. 13-check validation suite passing. Latest run:
  **14 high-quality companies more than 10% below their usual price**,
  which is what the page shows by default.
- **Stage 3 — built.** Two gates: cheapness against a company's own
  earnings-yield history over both 3 and 5 years, and operating income
  against the year-ago quarter. It annotates the ranking and never
  reorders it. Latest run: **14 of 260 show profit falling**, two of them
  on the published list. See spec §5.
- **UI — built and published.** One static page rebuilt by the daily
  scan and served by GitHub Pages, at the link above. Every constituent
  is embedded in it, so any ticker can be looked up, not only the ranked
  ones. It opens with the funnel and one statement per company, and
  switches to a nine-column table on request. `/simple/`, the address
  the statement page used to have, redirects to the main page.

## Running it

The SEC requires a contact address on every request and will reject
anonymous calls:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

export SEC_USER_AGENT="vantage you@example.com"

# documentation staleness blocks a commit; enable the hook once per clone
git config core.hooksPath .githooks

.venv/bin/python tests/test_golden_set.py   # Stage 1 regression, ~20s
.venv/bin/python tests/test_stage2.py       # Stage 2 validation, ~30s
.venv/bin/python tests/test_docs_current.py  # do the docs match the code, instant
.venv/bin/python tests/test_whole_years.py   # a quarter is never a year, instant
.venv/bin/python scripts/run_stage1.py      # quality gate, ~9 min
.venv/bin/python scripts/run_stage2.py      # below-normal, ~4 min
.venv/bin/python scripts/run_stage3.py      # cheap or deteriorating, ~9 min
.venv/bin/python scripts/build_site.py      # rebuild both pages
```

## Layout

```
funnel/stage1.py     the six quality gates, grading and tiers
funnel/universe.py   S&P 500 constituents, sectors, track assignment
funnel/prices.py     price history and the checks that gate publishing
funnel/stage2.py     the below-normal figure and shape labels
funnel/stage3.py     the two Stage 3 gates and the label they produce
scripts/run_stage1.py  quality gate over the whole index
scripts/run_stage2.py  below-normal over everything stage 1 assessed
scripts/run_stage3.py  cheapness and quarterly profit, same coverage
scripts/build_site.py  renders the page from the three result files
site/template_simple.html  the page — cards, the table view, and the filters
site/detail.js       the expanded panel, shared by both views
site/detail.css      its styles, likewise — one source, so they cannot drift
.githooks/pre-commit  blocks a commit whose docs no longer match the code
docs/                what GitHub Pages serves — index.html, plus
                     simple/index.html redirecting to it
tests/               golden-set regression, Stage 2 validation, doc currency,
                     whole-year guard
docs/FUNNEL_SPEC.md  the specification
```

## Design

[`docs/FUNNEL_SPEC.md`](docs/FUNNEL_SPEC.md) is the single source of
truth: every gate, every threshold, and the measurement behind each one.
Read it before changing anything in `funnel/`.

## Not financial advice

This encodes one person's screening rules in software. It is not
investment advice, is not from a licensed advisor, and should be used at
your own risk. Data comes from SEC filings and Yahoo Finance via the
unofficial `yfinance` library — not guaranteed accurate or complete.
