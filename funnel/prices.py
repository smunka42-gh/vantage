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

# `auto_adjust=True` is SUPPOSED to make splits invisible, and usually
# does — but not always for a split that happened days ago. On 31 Aug
# 2026 IESC (2-for-1 on the 24th) and MNST (2-for-1) both arrived
# unadjusted, and both were published as the two largest falls on the
# page: 47.9% and 40.8% "below normal" for companies that had not fallen
# at all. POWL's 3-for-1 in April and MIDD's in July were adjusted
# correctly, so this is specifically a recency problem in the feed.
#
# The check is cheap because it is two-stage. A split-shaped BREAK is
# found by arithmetic already in memory; only the handful of tickers that
# show one cost a request to confirm against the split record. Across
# 1,389 companies that was 25 candidates and exactly 2 real artefacts,
# with no false positives — the other 23 were genuine one-day crashes.
SPLIT_BREAK = 0.70          # a one-day ratio at or below this is suspicious
SPLIT_NEAR_DAYS = 45        # how far the recorded split may sit from the break
# Only RECENT history is scanned. Splits older than a year are adjusted
# correctly by the feed; the failure is specifically a recent one. This
# is not a nicety — fetch() returns five years, and over five years
# hundreds of companies have had a one-day fall past the threshold, each
# of which would cost a separate per-ticker request. Across 1,389
# companies that is ~25 candidates over one year against several hundred
# over five, and the extra ones cannot be the bug being fixed.
SPLIT_SCAN_BARS = 252       # one trading year


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


def repair_splits(frames: dict[str, pd.DataFrame]) -> tuple[dict, list]:
    """Back-adjust history the feed left unadjusted for a split.

    Returns (repairs, rejected).

    **This acts only where a split is actually on record.** A large
    one-day fall with no recorded split is left alone and scored as the
    real fall it almost certainly is — flattening those would erase
    exactly the signal this page exists to find. Checked on the four
    candidates of 31 Aug 2026: the one with a recorded split (IESC) saw
    volume barely move and dollar volume FALL, the signature of a split;
    the three without (VRRM, PRIM, UTI) spiked volume 2.5-7x, which is
    people trading news. The split record and the volume agreed.

    Where a split IS on record, two outcomes:

    * ONE break. The feed did not apply a recent split. Divide
      everything before the break by the factor, then re-check — a
      repair that leaves a break behind is rejected rather than
      published on a number nothing verified.
    * MANY breaks. On 31 Aug 2026 MNST arrived with FOUR, its days
      alternating between the two bases — 99.94, 97.50, 47.72, 47.23,
      47.83, 93.56. That is a corrupt series, not an unapplied split,
      and dividing "everything before the last break" would halve the
      days that were already right. Rejected.
    """
    repairs, rejected = {}, []
    # Anything with a split-shaped break MUST end up in one of the three
    # buckets below. Falling through silently is the failure mode.
    for t, f in frames.items():
        close = f["Close"]
        recent = close.tail(SPLIT_SCAN_BARS + 1)
        breaks = (recent / recent.shift(1)).pipe(lambda r: r[r <= SPLIT_BREAK])
        if breaks.empty:
            continue
        try:
            splits = yf.Ticker(t).splits
        except Exception as exc:
            # NEVER swallow this. A failed lookup here is indistinguishable
            # from "no split on record", and treating it as the latter
            # publishes the false 50% fall this function exists to stop.
            # Yahoo rate-limits these calls, and on 31 Aug 2026 that
            # silently disarmed the whole check while the run reported
            # "no unadjusted splits found".
            rejected.append((t, f"split record unreadable ({type(exc).__name__})"))
            continue
        recorded = [(d.date(), float(v)) for d, v in splits.items()
                    if float(v) > 1.01
                    and any(abs((d.date() - w.date()).days) <= SPLIT_NEAR_DAYS
                            for w in breaks.index)]
        if not recorded:
            continue                       # a real fall, not our business
        if len(breaks) > 1:
            rejected.append((t, f"{len(breaks)} split-shaped breaks around a "
                                f"recorded split — series is on mixed bases"))
            continue
        when, drop = breaks.index[0], float(breaks.iloc[0])
        factor = max(v for _, v in recorded)
        f.loc[f.index < when, "Close"] = f.loc[f.index < when, "Close"] / factor
        again = f["Close"] / f["Close"].shift(1)
        if (again <= SPLIT_BREAK).any():
            rejected.append((t, f"still broken after dividing by {factor:g}"))
            continue
        repairs[t] = (f"divided pre-{when.date()} closes by {factor:g} "
                      f"(one-day {100*(drop-1):.1f}%)")
    return repairs, rejected


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
