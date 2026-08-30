"""Stage 3 — is this fall an opportunity or a warning?

Two gates, both reading filed figures only. Stage 3 ANNOTATES Stage 2's
ranking: it never reorders, filters, scores or contributes a number to
it. See spec §5.

Gate 1  is it cheaper than its own normal?   earnings yield vs its own
                                             3- and 5-year medians
Gate 2  is the business still intact?        two consecutive quarters of
                                             operating income down >10%

Everything here is pure: it takes already-loaded figures and returns
labels. Fetching lives in scripts/run_stage3.py, the same split stage1
and stage2 use.
"""
from __future__ import annotations

import statistics as st

# Gate 1 needs no threshold: a company's own median IS its normal, so
# zero is structural. What it does need is BOTH windows, because 3 and 5
# years disagree for 8% of the index but for 4 of the 16 PUBLISHED names
# — a quarter of what the reader sees would otherwise be decided by a
# window choice with no principled reason to prefer either.
YIELD_WINDOWS = (3, 5)
MIN_YIELD_YEARS = 4          # fewer than this and a median means nothing

# Gate 2. The ONLY judged number in Stage 3.
#
# A single quarter is never rare: measured across 11,536 year-on-year
# quarter pairs, 19.7% fall more than 10% and 12.5% fall more than 20%,
# and 92% of companies clearing six quality gates have had a -20%
# quarter. An earlier draft called -20% "material by any reading"; it is
# not. There is no single-quarter threshold at which this becomes rare.
#
# Two consecutive is 2.3x rarer at every threshold, and is the difference
# between Lululemon (-11.2% then -36.9%) and The Trade Desk (+22.4% then
# -13.0% — one soft quarter after a strong one). Persistence is what
# "deteriorating" means and no single-quarter rule can express it.
QUARTER_FALL = -0.10
CONSECUTIVE = 2


def cheapness(yield_now, yield_history):
    """Gate 1. Where does today's earnings yield sit in its own history?

    `yield_history` is that company's own (EPS / price at that fiscal
    year end), oldest first. Compared in PERCENTAGE POINTS, never as a
    ratio: a ratio explodes as historical earnings approach zero —
    Insulet's own-normal P/E computes to 595x — and inverting P/E to a
    yield moves the explosion into the ratio rather than removing it.
    Differencing two yields is bounded.

    "The windows disagree" and "today lies between the two medians" are
    the same statement: if today is above one median and below the other
    it is between them by definition. So the three states answer one
    question — where does today sit relative to the band its own history
    spans?
    """
    if yield_now is None or not yield_history or len(yield_history) < MIN_YIELD_YEARS:
        return None
    meds = {n: st.median(yield_history[-n:]) for n in YIELD_WINDOWS}
    pts = {n: (yield_now - m) * 100 for n, m in meds.items()}
    if all(v > 0 for v in pts.values()):
        state = "cheaper than usual"
    elif all(v <= 0 for v in pts.values()):
        state = "pricier than usual"
    else:
        state = "priced about as usual"
    return {"state": state, "now": yield_now * 100,
            "medians": {n: m * 100 for n, m in meds.items()},
            "points": pts}


def intact(quarterly_yoy):
    """Gate 2. Two consecutive year-on-year quarters down more than 10%.

    `quarterly_yoy` is that company's own sequence of (this quarter vs
    the same quarter a year earlier) changes, oldest first.

    Three things this deliberately does NOT do, each measured before
    being rejected — see spec §5.3:

      * exclude swings into an operating loss. Redundant here: the
        exclusion only bites when BOTH quarters breach, and in both such
        cases the company posted two consecutive operating LOSSES, which
        is worth reporting whatever caused it.
      * fall back to an annual comparison when the newest period is a
        fiscal year. 10-Ks do not tag Q4 as a quarter, so the newest
        QUARTER can be ~6 months old — but measured, the annual view
        detects nothing the quarterly rule misses and LOSES Nike, whose
        full year was flat while its last two quarters fell 29% and 23%.
      * apply a staleness cutoff. The only companies it would exclude are
        a tag-selection bug (BNY resolves to 2016), and a cutoff would
        hide the bug rather than fix it. The age is displayed instead.
    """
    if not quarterly_yoy or len(quarterly_yoy) < CONSECUTIVE:
        return None
    recent = quarterly_yoy[-CONSECUTIVE:]
    return {"falling": all(v < QUARTER_FALL for v in recent), "recent": recent}


def label(cheap, still_intact):
    """The one line the page shows. A description, never a verdict.

    Where a gate is unavailable the label reports only what WAS
    established rather than collapsing to "no data" — 14 of 260 have no
    usable yield history while their quarters are fine.

    §6 forbids "WARNING" as a word: the funnel refuses to say whether a
    fall is good or bad, and a judging label would put that judgement
    back in.
    """
    falling = still_intact["falling"] if still_intact else None
    if cheap is None and still_intact is None:
        return "not enough history"
    if cheap is None:
        return "profit falling" if falling else "profit holding up"
    if falling is None:
        return cheap["state"]
    return cheap["state"] + (", profit falling" if falling else "")
