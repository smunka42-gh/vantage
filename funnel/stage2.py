"""Stage 2 — the dislocation score.

Answers one question about a company that already cleared Stage 1: how
far below its OWN normal is it trading today? Not cheap versus other
companies, and not cheap on a valuation multiple — a P/E screen here
would fight the funnel by rejecting the very dislocations it exists to
find.

Pure library — importing it does nothing. See docs/FUNNEL_SPEC.md §4.
"""
from __future__ import annotations

# Both components are "percent below a moving average", so they are
# measured the same way and can be blended raw. That is what keeps the
# score in real percentage terms, which is what makes an ABSOLUTE "on
# sale" bar possible — and an absolute bar is the only kind that can
# return "nothing today". A percentile always has a 99th percentile and
# would nominate a most-dislocated company every single day.
W_LONG = 0.60
W_SHORT = 0.40

# Measured across the 239 eligible on 29 Aug 2026: 16 companies clear
# this, which is the right width for Stage 3 to narrow to a handful.
# A tighter bar here would do Stage 3's job for it and collapse the
# funnel into a single stage.
ON_SALE = 0.10

# Shape of the decline, from the ratio of the two gaps. The 50-day
# average catches up to a new price level in about two months while the
# 200-day takes a year, so the gap BETWEEN them dates the fall.
STILL_FALLING = 0.70
RECOVERING = 0.20

# Gate 6 (spec §3.14) — a Stage 1 gate, executed here because it is the
# only one needing prices rather than filings.
MIN_DOLLAR_VOLUME = 25_000_000


def components(p: dict) -> dict:
    """The two raw measures, plus the context figures shown but not scored."""
    price = p["price"]
    return {
        "d_ma200": (p["sma200"] - price) / p["sma200"],
        "d_ma50": (p["sma50"] - price) / p["sma50"],
        # Displayed as context only. Dropped from the score in v0.9: it
        # is 0.74-correlated with d_ma200, and its distinctive part
        # measures whether the stock SPIKED in the last year rather than
        # whether it is cheap now.
        "d_high": (p["high52"] - price) / p["high52"],
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
    if ratio >= STILL_FALLING:
        # Includes ratio > 1, where the recent gap exceeds the long-run
        # one — a decline that is accelerating.
        return "still falling"
    if ratio >= RECOVERING:
        return "stabilising"
    return "recovering"


def score(p: dict) -> dict:
    """Score one company from its derived price figures.

    Returns the verdict plus every input that produced it, so a reader
    can check the arithmetic rather than trust it.
    """
    if p.get("insufficient_history"):
        return {
            "status": "insufficient history",
            "bars": p["bars"],
            "dislocation": None,
            "on_sale": False,
        }

    c = components(p)
    dislocation = W_LONG * c["d_ma200"] + W_SHORT * c["d_ma50"]
    liquid = p["median_dollar_volume"] >= MIN_DOLLAR_VOLUME

    return {
        "status": "scored",
        "price": p["price"],
        "as_of": p["as_of"],
        "d_ma200": c["d_ma200"],
        "d_ma50": c["d_ma50"],
        "d_high": c["d_high"],
        "dislocation": dislocation,
        # Liquidity is a Stage 1 gate, so a company failing it is not on
        # sale no matter how far it has fallen — you could not accumulate
        # it without moving the price against yourself.
        "on_sale": bool(dislocation >= ON_SALE and liquid),
        "shape": shape(c["d_ma200"], c["d_ma50"]),
        "median_dollar_volume": p["median_dollar_volume"],
        "gate6_liquidity": "pass" if liquid else "fail",
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
