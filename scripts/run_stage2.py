"""Run Stage 2 across the index and report what is far below normal.

Reads the Stage 1 verdicts, fetches prices, scores everything, and
refuses to write anything if the price data does not pass its checks.

    python scripts/run_stage1.py      # must have been run first
    python scripts/run_stage2.py

Components are computed for ALL constituents, not just the eligible
ones, because the ticker inspector has to answer for rejected companies
too. Only the eligible list is ranked and flagged below normal.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel import prices, stage2                        # noqa: E402
from funnel.universe import load_sp500                   # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
STAGE1 = HERE / "stage1_results.json"
OUT = HERE / "stage2_results.json"

ELIGIBLE_TIERS = {"PASS", "BORDERLINE"}

# Yahoo's exchange codes, mapped to what Google Finance expects in a URL.
# Anything unrecognised gets no Google link rather than a broken one.
GOOGLE_EXCHANGE = {"NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ",
                   "NYQ": "NYSE", "ASE": "NYSEAMERICAN", "PCX": "NYSEARCA"}


def _links_and_caps(tickers: list[str]) -> dict[str, dict]:
    """Market cap and deep-dive links for every company with a price.

    Fetched for ALL constituents, not just the flagged ones, because the
    ticker lookup has to answer for any S&P 500 company — and especially
    for the ones that did not qualify. ~2.4 minutes for 500.

    Market cap plays NO part in the funnel — it neither gates nor ranks.
    It is here because it changes what a reader would do, which under
    TENETS.md 2 makes it a driver rather than decoration. It is a column
    to sort by, deliberately not a grouping: grouping by size would bury
    exactly the unfamiliar names the screen exists to surface.
    """
    import yfinance as yf
    out = {}
    for t in tickers:
        cap, exch = None, None
        try:
            info = yf.Ticker(t).info
            cap, exch = info.get("marketCap"), info.get("exchange")
        except Exception:                                    # noqa: BLE001
            pass
        g = GOOGLE_EXCHANGE.get(exch or "")
        out[t] = {
            "market_cap": cap,
            "yahoo": f"https://finance.yahoo.com/quote/{t}",
            "google": f"https://www.google.com/finance/quote/{t}:{g}" if g else None,
        }
        time.sleep(0.05)
    return out


def main() -> int:
    if not STAGE1.exists():
        print(f"error: {STAGE1.name} not found — run scripts/run_stage1.py first")
        return 1

    s1 = json.loads(STAGE1.read_text())
    companies = load_sp500()
    names = {c["ticker"]: c["name"] for c in companies}
    tickers = [c["ticker"] for c in companies]
    eligible = {t for t, r in s1.items() if r["tier"] in ELIGIBLE_TIERS}
    print(f"{len(tickers)} constituents, {len(eligible)} eligible from Stage 1\n")

    print("downloading prices...", flush=True)
    frames = prices.fetch(tickers)
    print(f"   {len(frames)}/{len(tickers)} returned data\n")

    # --- refuse to publish bad data ------------------------------------
    problems = prices.validate(frames, tickers)
    if problems:
        print("PRICE DATA FAILED VALIDATION — refusing to write results:")
        for p in problems:
            print(f"   - {p}")
        print("\nPrevious results left untouched.")
        return 1
    print("price data passed validation\n")

    # --- score ----------------------------------------------------------
    scored, short_history = {}, []
    for t, frame in frames.items():
        s = stage2.score(prices.derive(frame))
        s["tier"] = s1.get(t, {}).get("tier", "NOT IN STAGE 1")
        s["eligible"] = t in eligible
        s["name"] = names.get(t, t)
        scored[t] = s
        if s["status"] == "insufficient history":
            short_history.append(t)

    # --- market cap and deep-dive links, every company ----------------
    # Every company, not just the flagged ones: the ticker lookup has to
    # answer for any S&P 500 constituent, and especially for the ones that
    # did not qualify.
    extra = _links_and_caps(sorted(scored))
    for t, e in extra.items():
        scored[t].update(e)

    OUT.write_text(json.dumps(scored, indent=1))

    # --- report ---------------------------------------------------------
    elig_scored = {t: s for t, s in scored.items()
                   if s["eligible"] and s["status"] == "scored"}
    flagged = {t: s for t, s in elig_scored.items()
               if s["far_below_normal"]}

    print("=" * 68)
    print(f"STAGE 2 — BELOW NORMAL   ({len(elig_scored)} eligible companies scored)")
    print("=" * 68)

    if not flagged:
        print(f"\n   Nothing is more than "
              f"{stage2.BELOW_NORMAL_BAR:.0%} below normal today.\n")
        print("   That is a real answer, not a failure — the bar is absolute,")
        print("   so on a day when no quality company has been marked down,")
        print("   the correct output is an empty list.")
    else:
        print(f"\n{len(flagged)} of {len(elig_scored)} companies are more than "
              f"{stage2.BELOW_NORMAL_BAR:.0%} below their own normal\n")
        print(f"  {'tkr':6s} {'below normal':>13s} {'mkt cap':>9s} "
              f"{'200d':>7s} {'50d':>7s}  {'shape':16s} tier")
        print("  " + "-" * 76)
        for t, s in sorted(flagged.items(),
                           key=lambda kv: -kv[1]["below_normal"]):
            cap = s.get("market_cap")
            cap_s = f"{cap/1e9:8.1f}B" if cap else "       —"
            print(f"  {t:6s} {s['below_normal']*100:12.1f}% {cap_s} "
                  f"{s['d_ma200']*100:6.1f}% {s['d_ma50']*100:6.1f}%  "
                  f"{s['shape'] or '—':16s} {s['tier']}")

        # The two things a finance site cannot tell you, because both
        # depend on OUR gates: which bar this company is closest to
        # failing, and how much recent history those gates have not seen.
        print("\n  worth knowing before you read:")
        for t in sorted(flagged, key=lambda t: -flagged[t]["below_normal"]):
            r1 = s1.get(t, {})
            risk = r1.get("at_risk") or []
            asof = r1.get("asof") or {}
            bits = []
            if risk:
                for g in r1.get("gates", []):
                    if g["gate"] in risk:
                        bits.append(f"closest to failing -> {g['gate']}: {g['detail']}")
            if asof.get("period_end"):
                months = (dt.date.today()
                          - dt.date.fromisoformat(asof["period_end"])).days / 30.44
                bits.append(f"quality gate reads FY{asof.get('fiscal_year')} "
                            f"(ended {asof['period_end']}) — {months:.0f} months "
                            f"of business it has not seen")
            print(f"    {t:6s} " + ("\n           ".join(bits) if bits else "—"))

        print("\n  deep-dive links:")
        for t in sorted(flagged, key=lambda t: -flagged[t]["below_normal"]):
            e = extra.get(t, {})
            print(f"    {t:6s} {e.get('yahoo', '')}"
                  + (f"   {e['google']}" if e.get("google") else ""))

    # Distribution, so the bar can be judged against reality rather than
    # taken on faith.
    vals = sorted(s["below_normal"] for s in elig_scored.values())
    def pct(q: float) -> float:
        return vals[min(int(q * len(vals)), len(vals) - 1)] * 100
    print(f"\ndistribution across the eligible list:")
    print(f"   median {pct(0.50):+.1f}%   p75 {pct(0.75):+.1f}%   "
          f"p90 {pct(0.90):+.1f}%   p95 {pct(0.95):+.1f}%   "
          f"max {vals[-1]*100:+.1f}%")
    if pct(0.50) < 0:
        print(f"   (the median eligible company is trading ABOVE its own "
              f"normal — the market is in an uptrend)")

    shapes = collections.Counter(s["shape"] for s in flagged.values())
    if shapes:
        print(f"\nshape of the decline, among the flagged names:")
        for k, n in shapes.most_common():
            print(f"   {k or 'n/a':16s} {n}")

    lo, sh = stage2.effective_weights(elig_scored)
    print(f"\nweights: stated {stage2.W_LONG:.0%}/{stage2.W_SHORT:.0%}  ->  "
          f"effective {lo:.0%}/{sh:.0%} (200d/50d)")
    print("   they differ because a component only moves a ranking as far")
    print("   as it varies; this is disclosed, not corrected — see spec §4.3")

    if short_history:
        print(f"insufficient history ({len(short_history)}): "
              f"{short_history[:8]}")
    print(f"\nwrote {OUT.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
