"""Run Stage 2 across the index and report what is on sale.

Reads the Stage 1 verdicts, fetches prices, scores everything, and
refuses to write anything if the price data does not pass its checks.

    python scripts/run_stage1.py      # must have been run first
    python scripts/run_stage2.py

Components are computed for ALL constituents, not just the eligible
ones, because the ticker inspector has to answer for rejected companies
too. Only the eligible list is ranked and only it can be "on sale".
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel import prices, stage2                        # noqa: E402
from funnel.universe import load_sp500                   # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
STAGE1 = HERE / "stage1_results.json"
OUT = HERE / "stage2_results.json"

ELIGIBLE_TIERS = {"PASS", "BORDERLINE", "EXCEPTION"}


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

    OUT.write_text(json.dumps(scored, indent=1))

    # --- report ---------------------------------------------------------
    elig_scored = {t: s for t, s in scored.items()
                   if s["eligible"] and s["status"] == "scored"}
    on_sale = {t: s for t, s in elig_scored.items() if s["on_sale"]}

    print("=" * 68)
    print(f"STAGE 2 — DISLOCATION   ({len(elig_scored)} eligible companies scored)")
    print("=" * 68)

    if not on_sale:
        print("\n   Nothing is on sale today.\n")
        print("   That is a real answer, not a failure — the bar is absolute,")
        print("   so on a day when no quality company has been marked down,")
        print("   the correct output is an empty list.")
    else:
        print(f"\n{len(on_sale)} of {len(elig_scored)} companies are on sale "
              f"(>= {stage2.ON_SALE:.0%} below their own normal)\n")
        print(f"  {'tkr':6s} {'below own':>10s} {'200d':>8s} {'50d':>8s}  "
              f"{'shape':14s} tier")
        print("  " + "-" * 64)
        for t, s in sorted(on_sale.items(),
                           key=lambda kv: -kv[1]["dislocation"]):
            print(f"  {t:6s} {s['dislocation']*100:9.1f}% "
                  f"{s['d_ma200']*100:7.1f}% {s['d_ma50']*100:7.1f}%  "
                  f"{s['shape'] or '—':14s} {s['tier']}")

    # Distribution, so the bar can be judged against reality rather than
    # taken on faith.
    vals = sorted(s["dislocation"] for s in elig_scored.values())
    def pct(q: float) -> float:
        return vals[min(int(q * len(vals)), len(vals) - 1)] * 100
    print(f"\ndistribution across the eligible list:")
    print(f"   median {pct(0.50):+.1f}%   p75 {pct(0.75):+.1f}%   "
          f"p90 {pct(0.90):+.1f}%   p95 {pct(0.95):+.1f}%   "
          f"max {vals[-1]*100:+.1f}%")
    if pct(0.50) < 0:
        print(f"   (the median eligible company is trading ABOVE its own "
              f"normal — the market is in an uptrend)")

    shapes = collections.Counter(s["shape"] for s in on_sale.values())
    if shapes:
        print(f"\nshape of the decline, among the on-sale names:")
        for k, n in shapes.most_common():
            print(f"   {k or 'n/a':16s} {n}")

    lo, sh = stage2.effective_weights(elig_scored)
    print(f"\nweights: stated {stage2.W_LONG:.0%}/{stage2.W_SHORT:.0%}  ->  "
          f"effective {lo:.0%}/{sh:.0%} (200d/50d)")
    print("   they differ because a component only moves a ranking as far")
    print("   as it varies; this is disclosed, not corrected — see spec 4.3")

    if short_history:
        print(f"insufficient history ({len(short_history)}): "
              f"{short_history[:8]}")
    print(f"\nwrote {OUT.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
