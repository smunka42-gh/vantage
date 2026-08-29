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
| **You** | Is it worth buying? | — | The links the tool hands you |

Stage 1 is a **hard gate** — quality is a precondition, not a factor to
trade off. Stage 2 is a percentage, not a verdict.

**There is no Stage 3.** One was specified and removed before being
built: every candidate signal turned out to be circular, near-constant,
or lagging the event it was meant to judge — and two stages already
reduce 500 companies to about 16, ranked, which is a short enough list to
read yourself. See §5 of the spec.

## Status

- **Stage 1 — built.** Five gates across four sector tracks, running
  against live SEC filings, with a 17-company regression test (17/17)
  plus two assertions on the data itself: that it is the newest filed
  year, and that every figure is a whole year rather than a quarter
  posing as one. The gates do not run on REITs, so the scan covers
  **470 of the 500** constituents. Latest full run: 224 pass,
  38 borderline, 190 rejected, 18 without enough filing history —
  **262 eligible**.
- **Stage 2 — built.** Two moving-average components blended as real
  percentages, with an absolute 10% bar so the honest answer on a calm
  day is an empty list. 13-check validation suite passing. Latest run:
  **17 of 262 below normal**.
- **Stage 3 — does not exist, deliberately.** See spec §5.
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

.venv/bin/python tests/test_golden_set.py   # Stage 1 regression, ~20s
.venv/bin/python tests/test_stage2.py       # Stage 2 validation, ~30s
.venv/bin/python scripts/run_stage1.py      # quality gate, ~9 min
.venv/bin/python scripts/run_stage2.py      # below-normal, ~1 min
.venv/bin/python scripts/build_site.py      # rebuild docs/index.html
```

## Layout

```
funnel/stage1.py     the five quality gates, grading and tiers
funnel/universe.py   S&P 500 constituents, sectors, track assignment
funnel/prices.py     price history and the checks that gate publishing
funnel/stage2.py     the below-normal figure and shape labels
scripts/run_stage1.py  quality gate over the whole index
scripts/run_stage2.py  below-normal over the whole index
scripts/build_site.py  renders docs/index.html from the two result files
site/template.html   the page layout, with placeholders
docs/                what GitHub Pages serves
tests/               golden-set regression + Stage 2 validation suite
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
