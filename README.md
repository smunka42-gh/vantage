# Vantage

**[smunka42-gh.github.io/vantage](https://smunka42-gh.github.io/vantage/)**

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
  **260 eligible**.
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
- **UI — built and published.** A static page rebuilt by the daily
  scan, served by GitHub Pages at the link above. Every constituent is
  embedded, so any ticker can be looked up, not only the ranked ones.

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
.venv/bin/python scripts/run_stage1.py      # quality gate, ~9 min
.venv/bin/python scripts/run_stage2.py      # below-normal, ~4 min
.venv/bin/python scripts/run_stage3.py      # cheap or deteriorating, ~9 min
.venv/bin/python scripts/build_site.py      # rebuild docs/index.html
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
scripts/build_site.py  renders docs/index.html from the three result files
site/template.html   the page layout, with placeholders
.githooks/pre-commit  blocks a commit whose docs no longer match the code
docs/                what GitHub Pages serves
tests/               golden-set regression, Stage 2 validation, doc currency
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
