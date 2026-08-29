# Vantage

Finds durably high-quality companies that are **temporarily** marked down,
and tries to tell the difference between "cheap" and "broken".

Not a ranking of every stock by upside. The goal is a small,
slow-changing watchlist of companies worth owning, plus a signal when one
of them goes on sale for a reason that looks like sentiment rather than
deterioration.

## The funnel

| Stage | Question | Cadence | Source |
|---|---|---|---|
| **1 · Quality** | Would I ever want to own this? | Quarterly, on filings | SEC EDGAR (audited) |
| **2 · Dislocation** | Is it on sale right now? | Daily, on prices | Market data |
| **3 · Corroboration** | Is the sale real, or is it broken? | Daily | Analyst revisions, volume, short interest, fundamentals |

Stage 1 is a **hard gate** — quality is a precondition, not a factor to
trade off. Stages 2 and 3 are scores.

## Status

- **Stage 1 — built.** Five gates across four sector tracks, running
  against live SEC filings, with a 17-company regression test (17/17)
  and a data-recency assertion. Latest full run: 222 pass, 36
  borderline, 193 rejected, 19 not assessable, 30 REITs not yet
  covered — **258 of 500 eligible**.
- **Stage 2 — built.** Two moving-average components blended as real
  percentages, with an absolute 10% "on sale" bar so the honest answer
  on a calm day is an empty list. 13-check validation suite passing.
  Latest run: **16 of 258 on sale**.
- **Stage 3 — not started.**
- **UI — not started, deliberately.** All three stages get built and
  validated first; the interface is specified only once there are real
  numbers to design around.

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
.venv/bin/python scripts/run_stage2.py      # dislocation, ~1 min
```

## Layout

```
funnel/stage1.py     the six quality gates, grading and tiers
funnel/universe.py   S&P 500 constituents, sectors, track assignment
funnel/prices.py     price history and the checks that gate publishing
funnel/stage2.py     the dislocation score and shape labels
scripts/run_stage1.py  quality gate over the whole index
scripts/run_stage2.py  dislocation over the whole index
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
