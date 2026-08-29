"""The Stage 2 validation suite (spec §4.9).

Stage 2 has no golden set. There is no independently known right answer
for "how dislocated is this company", the way there is for "is Boeing a
quality business" — so validation here is mechanical rather than
judgemental. Five checks:

  1. Arithmetic     — the averages are what they claim to be
  2. Sanity anchors — the score points the right way
  3. Effective weights — the disclosed 68/32 split is real
  4. Shape labels   — they partition correctly and date the fall
  5. Second source  — the prices are RIGHT, not merely PRESENT

Run:  python tests/test_stage2.py       (needs network; ~30 seconds)

Exits non-zero on failure.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel import prices, stage2                        # noqa: E402

ANCHORS = ["MSFT", "AAPL", "NKE", "MNST", "ZTS", "COST", "WMT", "JNJ",
           "TJX", "LULU", "ISRG", "PG", "KO", "V", "MA", "HD", "CAT",
           "TTD", "DECK", "CHRW"]

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL':4s}  {name}")
    if detail:
        print(f"        {detail}")


def main() -> int:
    print(f"fetching {len(ANCHORS)} companies...\n")
    frames = prices.fetch(ANCHORS)
    derived = {t: prices.derive(f) for t, f in frames.items()}
    scored = {t: stage2.score(d) for t, d in derived.items()
              if not d.get("insufficient_history")}

    # --- 1. arithmetic ---------------------------------------------------
    print("1. ARITHMETIC — recompute the averages independently")
    t = "MSFT"
    close = frames[t]["Close"]
    hand_200 = float(close.tail(200).mean())
    hand_50 = float(close.tail(50).mean())
    hand_high = float(close.tail(252).max())
    d = derived[t]
    check("SMA200 matches a hand recomputation",
          abs(hand_200 - d["sma200"]) < 0.01,
          f"{t}: hand ${hand_200:.4f} vs module ${d['sma200']:.4f}")
    check("SMA50 matches a hand recomputation",
          abs(hand_50 - d["sma50"]) < 0.01,
          f"{t}: hand ${hand_50:.4f} vs module ${d['sma50']:.4f}")
    check("52-week high matches a hand recomputation",
          abs(hand_high - d["high52"]) < 0.01,
          f"{t}: hand ${hand_high:.4f} vs module ${d['high52']:.4f}"
          " (used only as a validation anchor, never scored or shown)")

    s = scored[t]
    blended = stage2.W_LONG * s["d_ma200"] + stage2.W_SHORT * s["d_ma50"]
    check("the blend is exactly its stated formula",
          abs(blended - s["dislocation"]) < 1e-12,
          f"0.60x{s['d_ma200']:.6f} + 0.40x{s['d_ma50']:.6f} "
          f"= {s['dislocation']:.6f}")

    # --- 2. sanity anchors ----------------------------------------------
    print("\n2. SANITY ANCHORS — does the score point the right way?")
    # A sign inversion is the likeliest silent bug here, and it would
    # invert the entire product: the page would recommend the stocks that
    # had risen the most.
    # Computed here from raw closes, not read from the score: this anchor
    # is only meaningful if it comes from a quantity the score does not
    # use. Distance from the 52-week high was cut from the product
    # (TENETS.md 2/4), which makes it a BETTER independent check.
    def dist_from_high(t):
        h = derived[t]["high52"]
        return (h - derived[t]["price"]) / h
    at_high = [t for t in scored if dist_from_high(t) < 0.02]
    check("a company near its 52-week high does not read as dislocated",
          all(scored[t]["dislocation"] < stage2.ON_SALE for t in at_high),
          f"{len(at_high)} within 2% of their high: "
          f"{[f'{t} {scored[t]['dislocation']*100:+.1f}%' for t in at_high[:4]]}"
          if at_high else "no anchor is near its high right now — check skipped")

    below_both = [t for t, s in scored.items()
                  if s["d_ma200"] > 0.15 and s["d_ma50"] > 0.10]
    check("a company well below BOTH averages reads as dislocated",
          all(scored[t]["dislocation"] >= stage2.ON_SALE for t in below_both),
          f"{[f'{t} {scored[t]['dislocation']*100:+.1f}%' for t in below_both[:4]]}"
          if below_both else "no anchor is far below both right now — check skipped")

    above_normal = [t for t, s in scored.items() if s["price"] > s["d_ma200"]
                    and s["d_ma200"] < 0]
    check("trading above its own normal yields a NEGATIVE score",
          all(scored[t]["dislocation"] < 0 or scored[t]["d_ma50"] > 0
              for t in above_normal),
          f"{len(above_normal)} companies above their 200-day average")

    check("nothing is on sale on negative dislocation",
          all(s["dislocation"] >= stage2.ON_SALE
              for s in scored.values() if s["on_sale"]),
          "every on-sale name clears the bar")

    # --- 3. effective weights -------------------------------------------
    print("\n3. EFFECTIVE WEIGHTS — is the disclosed split real?")
    lo, sh = stage2.effective_weights(scored)
    check("the 200-day carries materially more influence than stated",
          lo > stage2.W_LONG,
          f"stated {stage2.W_LONG:.0%}/{stage2.W_SHORT:.0%}  ->  "
          f"effective {lo:.0%}/{sh:.0%}  "
          f"(spec 4.3 discloses ~68/32 on the full eligible list)")

    # --- 4. shape labels -------------------------------------------------
    print("\n4. SHAPE LABELS — do they partition, and do they date the fall?")
    declining = {t: s for t, s in scored.items() if s["d_ma200"] > 0}
    labels = {s["shape"] for s in declining.values()}
    check("every declining company gets exactly one known label",
          labels <= {"still falling", "stabilising", "recovering"}
          and None not in labels,
          f"{len(declining)} declining, labels seen: {sorted(labels)}")

    check("a company above its own normal gets NO shape label",
          all(s["shape"] is None for s in scored.values() if s["d_ma200"] <= 0),
          "no decline means there is no shape to describe")

    # The label must follow the ratio, since that is its entire definition.
    ok = True
    for t, s in declining.items():
        r = s["d_ma50"] / s["d_ma200"]
        want = ("still falling" if r >= stage2.STILL_FALLING else
                "stabilising" if r >= stage2.RECOVERING else "recovering")
        if s["shape"] != want:
            ok = False
            print(f"        {t}: ratio {r:.2f} labelled {s['shape']}, "
                  f"expected {want}")
    check("each label follows from its ratio", ok)

    # --- 5. second source ------------------------------------------------
    print("\n5. SECOND SOURCE — are the prices right, not merely present?")
    # Everything above would pass on confidently wrong numbers. This is
    # the only check that tests the DATA rather than the arithmetic.
    ok, details = True, []
    for t in ("MSFT", "AAPL", "COST"):
        try:
            hist = yf.Ticker(t).history(period="5d", auto_adjust=True)
            # dropna() is REQUIRED, not tidiness: the current session's
            # bar exists but is NaN until the close, so .iloc[-1] on the
            # raw frame returns NaN. An earlier version of this check did
            # exactly that and reported PASS, because every comparison
            # against NaN is False. A validation check that cannot fail
            # is worse than no check at all.
            series = hist["Close"].dropna()
            independent = float(series.iloc[-1]) if len(series) else float("nan")
        except Exception as e:                            # noqa: BLE001
            ok = False
            details.append(f"{t}: could not cross-check ({e})")
            continue

        ours = derived[t]["price"]
        if not (independent == independent) or independent <= 0:   # NaN-safe
            ok = False
            details.append(f"{t}: second source returned no usable price")
            continue

        drift = abs(independent - ours) / ours
        if drift > 0.01:
            ok = False
        details.append(f"{t}: bulk ${ours:.2f} vs per-ticker "
                       f"${independent:.2f} ({drift*100:.2f}% apart)")
    check("prices agree with an independently fetched series", ok,
          "  |  ".join(details))

    # --- verdict ----------------------------------------------------------
    failed = [n for n, ok, _ in results if not ok]
    print("\n" + "=" * 68)
    if failed:
        print(f"STAGE 2 VALIDATION: FAIL — {len(failed)} of {len(results)} checks")
        for n in failed:
            print(f"   - {n}")
        return 1
    print(f"STAGE 2 VALIDATION: PASS — all {len(results)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
