"""Stage 2 — how far below its own normal.

Answers one question about a company that already cleared Stage 1: how
far below its OWN normal is it trading today? Not cheap versus other
companies, and not cheap on a valuation multiple — a P/E screen here
would fight the funnel by rejecting the very falls it exists to find.

"Below normal" measures price against its OWN price history — how far
this has moved from where it usually trades. It is NOT a claim about
value: a business worth 40% less, priced 40% lower, reads the same as an
unchanged business priced 40% lower. Never call it a discount.

Pure library — importing it does nothing. See docs/FUNNEL_SPEC.md §4.
"""
from __future__ import annotations

# Both components are "percent below a moving average", so they are
# measured the same way and can be blended raw. That is what keeps the
# score in real percentage terms, which is what makes an ABSOLUTE "on
# sale" bar possible — and an absolute bar is the only kind that can
# return "nothing today". A percentile always has a 99th percentile and
# would nominate a furthest-below-normal company every single day.
W_LONG = 0.60
W_SHORT = 0.40

# The bar below which you are content not to look. Measured across the
# eligible list on 29 Aug 2026, 16 companies clear it — a short enough
# list to read properly, and it is ranked, so a reader works down from
# the top and stops when they choose.
#
# Deliberately NOT called "on sale": that would claim the fall is a
# bargain, and this figure has no idea whether it is. A business worth
# 40% less, priced 40% lower, reads identically to an unchanged business
# priced 40% lower. Same reason the metric is not called a discount.
BELOW_NORMAL_BAR = 0.10

# Shape of the decline, from the ratio of the two gaps. The 50-day
# average catches up to a new price level in about two months while the
# 200-day takes a year, so the gap BETWEEN them dates the fall.
#
# The labels describe PRICE BEHAVIOUR ONLY and deliberately imply no
# judgement. Wording like "high confidence dip" was rejected: Stage 2 has
# no idea whether a dip is good — that is Stage 3's entire job — and a
# card reading "high confidence dip / not worth buying" would contradict
# itself.
FALLING_NOW = 0.70          # as far below its 50-day as its 200-day
NOW_RISING = 0.20           # back at its recent normal

# Gate 6 (liquidity) used to be enforced here, being the one Stage 1 gate
# that needed prices rather than filings. It is GONE: it rejected zero of
# 500 companies, and TENETS.md 4 requires a check to change outcomes or be
# cut. Median dollar volume is no longer computed or displayed either —
# TENETS.md 2 rules out keeping an unused number on screen.


def components(p: dict) -> dict:
    """The two raw measures the score is built from.

    Distance from the 52-week high was here as "displayed context" and is
    now gone entirely. It is 0.74-correlated with d_ma200, and its
    distinctive part measures whether a stock SPIKED in the past year
    rather than whether it is cheap now. TENETS.md 4 cut it from the
    score; TENETS.md 2 cut it from the display, because showing "44%
    below its 52-week high" beside "18.7% below its own normal" invites a
    reader to weight it themselves.
    """
    price = p["price"]
    return {
        "d_ma200": (p["sma200"] - price) / p["sma200"],
        "d_ma50": (p["sma50"] - price) / p["sma50"],
    }


def shape(d_ma200: float, d_ma50: float) -> str | None:
    """When did the fall happen? A label, never a score adjustment.

    Undefined for a company trading at or above its long-run normal —
    there is no decline to characterise, so it returns None rather than
    inventing a shape.
    """
    if d_ma200 <= 0:
        return None
    ratio = d_ma50 / d_ma200
    if ratio >= FALLING_NOW:
        # Includes ratio > 1, where the recent gap exceeds the long-run
        # one — a decline that is accelerating.
        return "falling now"
    if ratio >= NOW_RISING:
        return "fell, now flat"
    return "fell, now rising"


def score(p: dict) -> dict:
    """Score one company from its derived price figures.

    Returns the verdict plus every input that produced it, so a reader
    can check the arithmetic rather than trust it.
    """
    if p.get("insufficient_history"):
        return {
            "status": "insufficient history",
            "bars": p["bars"],
            "below_normal": None,
            "far_below_normal": False,
        }

    c = components(p)
    below_normal = W_LONG * c["d_ma200"] + W_SHORT * c["d_ma50"]

    return {
        "status": "scored",
        "price": p["price"],
        "as_of": p["as_of"],
        "d_ma200": c["d_ma200"],
        "d_ma50": c["d_ma50"],
        "high52": p["high52"],
        "low52": p["low52"],
        "below_normal": below_normal,
        "far_below_normal": bool(below_normal >= BELOW_NORMAL_BAR),
        "shape": shape(c["d_ma200"], c["d_ma50"]),
    }


def effective_weights(scored: dict[str, dict]) -> tuple[float, float]:
    """How much each component ACTUALLY moved the ranking.

    A component only influences a ranking to the extent it VARIES across
    the names being ranked, so influence is weight x spread, not weight
    alone. Stating 60/40 while delivering something else is precisely the
    bug that broke the predecessor; this measures the real split so it
    can be disclosed rather than assumed.
    """
    rows = [s for s in scored.values() if s["status"] == "scored"]
    if len(rows) < 4:
        return (float("nan"), float("nan"))

    def iqr(key: str) -> float:
        vals = sorted(r[key] for r in rows)
        n = len(vals)
        return vals[int(0.75 * n)] - vals[int(0.25 * n)]

    a, b = W_LONG * iqr("d_ma200"), W_SHORT * iqr("d_ma50")
    total = a + b
    return (a / total, b / total) if total else (float("nan"), float("nan"))
