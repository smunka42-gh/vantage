"""Price history for Stage 2, and the checks that decide it is trustworthy.

Pure library — importing it does nothing.

The one rule worth stating twice: every figure here comes from
SPLIT- AND DIVIDEND-ADJUSTED closes. On raw prices a 2-for-1 split looks
like a company falling 50% overnight and every ex-dividend date is a
small false fall — and this project's whole job is to notice
companies that have fallen. Unadjusted prices would manufacture exactly
the signal we are hunting for. See docs/FUNNEL_SPEC.md §4.7.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import yfinance as yf

# Windows are in TRADING days, not calendar days: ~252 trading days to
# the year, ~63 to the quarter.
SMA_LONG = 200
SMA_SHORT = 50
WINDOW_52W = 252
# Three calendar years of trading. Where today's price sits in THIS span
# is a different question from how far it is below its moving averages,
# and the two disagree often enough to be worth asking separately: on
# 30 Aug 2026, four of the fourteen names on the page were 10%+ below
# their averages while sitting in the top half of this range.
WINDOW_3Y = 756
# Below this the window is too short to call anything a "3-year" range.
# ~1.6 years still supports the statement honestly; less does not.
MIN_BARS_3Y = 400

# A company needs at least a full long window before it can be compared
# to its own long-run normal. Below this it is reported as insufficient
# history and NEVER scored as though it were trading flat — the same
# distinction Stage 1 draws between CANNOT ASSESS and REJECTED.
MIN_BARS = SMA_LONG

# Publication gates (spec §4.7). The predecessor once committed a
# near-empty scan and blanked its own live page; these exist so a partial
# fetch fails loudly instead of quietly becoming the day's answer.
MIN_COVERAGE = 0.95
MAX_STALENESS_DAYS = 5


class PriceDataError(RuntimeError):
    """Raised when the fetched data is not fit to publish."""


def fetch(tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """Download daily bars for many tickers in one request.

    `auto_adjust=True` is the load-bearing argument — see the module
    docstring. `period` defaults to FIVE years: the 3-year percentile
    needs 756 bars, and two years cannot supply them. The extra history
    costs nothing — it is the same single request.
    """
    raw = yf.download(tickers, period=period, interval="1d",
                      group_by="ticker", auto_adjust=True,
                      threads=True, progress=False)

    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            frame = raw[t][["Close", "Volume"]].dropna()
        except (KeyError, TypeError):
            continue                       # no data returned for this one
        if not frame.empty:
            out[t] = frame
    return out


def derive(frame: pd.DataFrame) -> dict:
    """Turn one company's bars into the figures Stage 2 needs.

    Returns `insufficient_history` rather than a score when the series is
    too short to compare a company to its own long-run normal.
    """
    close = frame["Close"]
    bars = len(close)
    if bars < MIN_BARS:
        return {"bars": bars, "insufficient_history": True}

    return {
        "bars": bars,
        "insufficient_history": False,
        "price": float(close.iloc[-1]),
        "sma200": float(close.tail(SMA_LONG).mean()),
        "sma50": float(close.tail(SMA_SHORT).mean()),
        # The 52-week range. Not part of the score — it was measured out
        # of it (0.74 correlated with the 200-day, and contaminated by
        # one-day spikes). It is shown as the endpoints of a scale, which
        # is a different job: not a competing metric, but where today's
        # price sits in its own recent range. The validation suite also
        # uses the high as an INDEPENDENT sanity anchor against a sign
        # inversion, which only works because the score never touches it.
        "high52": float(close.tail(WINDOW_52W).max()),
        "low52": float(close.tail(WINDOW_52W).min()),
        # Where today sits in its own 3-year distribution, as the share
        # of closes AT OR BELOW today. Deliberately NOT blended into the
        # score: the two measures disagree for a meaningful minority, and
        # that disagreement is the information a reader needs. See §4.8.
        "q3y": _quantile_3y(close),
        "as_of": close.index[-1].date().isoformat(),
    }


def _quantile_3y(close) -> float | None:
    """Share of the last three years' closes at or below today's.

    None when the series is too short to make the claim — a percentile
    computed over eight months is not a three-year range, and saying so
    would be worse than saying nothing.
    """
    window = close.tail(WINDOW_3Y)
    if len(window) < MIN_BARS_3Y:
        return None
    return float((window <= close.iloc[-1]).sum()) / len(window) * 100.0


def validate(frames: dict[str, pd.DataFrame], requested: list[str]) -> list[str]:
    """Check the fetch is fit to publish. Returns a list of problems.

    An empty list means it passed. The caller must refuse to write
    results if anything comes back — a wrong answer published confidently
    is worse than yesterday's answer left in place.
    """
    problems = []

    coverage = len(frames) / len(requested) if requested else 0.0
    if coverage < MIN_COVERAGE:
        problems.append(
            f"only {len(frames)}/{len(requested)} tickers returned data "
            f"({coverage:.1%}, need {MIN_COVERAGE:.0%})")

    bad_prices = [t for t, f in frames.items() if (f["Close"] <= 0).any()]
    if bad_prices:
        problems.append(
            f"{len(bad_prices)} tickers have zero or negative prices: "
            f"{bad_prices[:5]}")

    # Staleness is judged on the NEWEST bar across the whole fetch, not
    # per ticker: one halted stock is normal, everything being days old
    # means the feed itself is stale.
    if frames:
        newest = max(f.index[-1].date() for f in frames.values())
        age = (dt.date.today() - newest).days
        if age > MAX_STALENESS_DAYS:
            problems.append(
                f"most recent bar is {age} days old ({newest}), "
                f"limit is {MAX_STALENESS_DAYS}")

    return problems
