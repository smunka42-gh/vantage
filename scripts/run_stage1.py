"""Run Stage 1 across the S&P 500 and report the tier distribution.

Self-contained: the constituent list, sectors and track assignment all
come from funnel.universe, and every financial figure comes from SEC
EDGAR. Nothing depends on a pre-existing scan file.

    export SEC_USER_AGENT="vantage you@example.com"
    python scripts/run_stage1.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel.stage1 import load, run, decide, at_risk, S      # noqa: E402
from funnel.universe import load_sp500, track_for            # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "stage1_results.json"

# A year where most of a sector's LARGEST companies were KNOCKED INTO an
# operating loss is an exogenous, industry-wide event rather than evidence
# about any one company, so it is excluded from Gate 1 for that sector.
SHOCK_SHARE = 0.50
SHOCK_TOP_N = 10
SHOCK_MIN_ASSESSABLE = 4      # too few evaluable names to call a trend


def _cik_map() -> dict[str, str]:
    m = S.get("https://www.sec.gov/files/company_tickers.json", timeout=30).json()
    return {v["ticker"].replace(".", "-"): str(v["cik_str"]).zfill(10) for v in m.values()}


def _shock_years(data: dict, sectors: dict) -> dict[str, set[str]]:
    """Detect sector-wide loss years.

    Sector size is ranked on TOTAL ASSETS, which Stage 1 already loads
    from EDGAR, rather than market capitalisation. That avoids pulling in
    a second data source for one ranking, and balance-sheet size is the
    more appropriate measure of "one of this sector's big names" anyway.

    A company counts toward a shock year only if it was PROFITABLE THE
    YEAR BEFORE — the loss has to be specific to that year. Counting
    every loss instead lets chronically unprofitable companies stand in
    as evidence of an industry-wide event, which is exactly backwards:
    a company that loses money every year says nothing about whether one
    particular year was exceptional.

    Measured, this is the difference between detecting a shock and
    detecting a weak sector:

        share of the ten largest posting an operating loss
                             2019    2020    2021
        Energy                10%     77%      0%   <- spike
        Industrials           20%     50%     30%   <- plateau

    Industrials 2020 tripped the old rule at exactly the 50% threshold,
    carried there by Boeing and DuPont, which were losing money either
    side of 2020 as well. Requiring a profitable prior year drops it to
    30% (does not fire) while Energy 2020 holds at 67% (still fires).
    """
    by_sector = collections.defaultdict(list)
    for t in data:
        by_sector[sectors[t]].append(t)

    shock: dict[str, set[str]] = collections.defaultdict(set)
    for sector, names in by_sector.items():
        def size(t: str) -> float:
            assets = data[t].get("assets") or {}
            return max(assets.values()) if assets else 0.0

        biggest = sorted(names, key=size, reverse=True)[:SHOCK_TOP_N]

        # knocked_down: lost money in year y having earned it in y-1.
        # assessable: had figures for BOTH years, so the question could
        # actually be asked of them. A company missing either year is
        # left out of both, rather than silently diluting the share.
        knocked_down, assessable = collections.Counter(), collections.Counter()
        for t in biggest:
            oi = data[t]["op_income"]
            for y in sorted(oi)[-5:]:          # same window the gates judge on
                prior = oi.get(str(int(y) - 1))
                if prior is None:
                    continue
                assessable[y] += 1
                if oi[y] <= 0 < prior:
                    knocked_down[y] += 1

        for y, n in assessable.items():
            if n >= SHOCK_MIN_ASSESSABLE and knocked_down[y] / n >= SHOCK_SHARE:
                shock[sector].add(y)
    return shock


def main() -> None:
    companies = load_sp500()
    sectors = {c["ticker"]: c["sector"] for c in companies}
    tracks = {c["ticker"]: track_for(c["ticker"], c["sector"]) for c in companies}
    cik = _cik_map()
    print(f"{len(companies)} companies in the index\n")

    # --- Pass 1: fetch every company's filings once -------------------
    print("loading filings from SEC EDGAR...", flush=True)
    data, errors, no_cik = {}, [], []
    assessable = [c["ticker"] for c in companies if tracks[c["ticker"]] != "unassessed"]
    for i, t in enumerate(assessable, 1):
        if t not in cik:
            no_cik.append(t)
            continue
        try:
            data[t] = load(t, cik[t])
        except Exception as e:                                # noqa: BLE001
            errors.append((t, str(e)[:60]))
        if i % 100 == 0:
            print(f"   ...{i}/{len(assessable)}", flush=True)
        time.sleep(0.11)                                      # SEC fair-use pacing

    shock = _shock_years(data, sectors)
    if shock:
        print("\nsector-wide shock years detected:")
        for sec, ys in sorted(shock.items()):
            print(f"   {sec:26s} {', '.join(sorted(ys))}")

    # --- Pass 2: apply the gates --------------------------------------
    out, tiers = {}, collections.Counter()
    for c in companies:
        t, sector, track = c["ticker"], c["sector"], tracks[c["ticker"]]
        if track == "unassessed":
            tiers["REIT (not assessed)"] += 1
            out[t] = {"tier": "REIT (not assessed)", "sector": sector, "track": track}
            continue
        if t not in data:
            tier = "NO CIK" if t in no_cik else "ERROR"
            tiers[tier] += 1
            out[t] = {"tier": tier, "sector": sector, "track": track}
            continue
        gates = run(
            t, data[t],
            is_financial=track == "financial",
            is_utility=track == "utility",
            is_capital_intensive=track == "capital_intensive",
            shock_years=shock.get(sector, set()),
        )
        tier = decide(gates, t)
        tiers[tier] += 1
        out[t] = {
            "tier": tier, "sector": sector, "track": track,
            "name": c["name"],
            "gates": [{"gate": n, "grade": g, "detail": d} for n, g, d in gates],
            "at_risk": at_risk(gates),
            # Which filing this verdict rests on. Stage 1 reads annual
            # 10-Ks, so this is 2-12 months old depending on the company's
            # fiscal calendar — the reader needs to know how much recent
            # history the gates have not seen.
            "asof": data[t].get("_asof"),
        }

    OUT.write_text(json.dumps(out, indent=1))

    total = len(companies)
    print(f"\n{'='*60}\nSTAGE 1 — S&P 500  (n={total})\n{'='*60}")
    for k in ["PASS", "BORDERLINE", "EXCEPTION", "REJECTED",
              "CANNOT ASSESS", "REIT (not assessed)", "NO CIK", "ERROR"]:
        if tiers.get(k):
            print(f"   {k:22s} {tiers[k]:4d}   {tiers[k]/total*100:5.1f}%")
    elig = tiers["PASS"] + tiers["BORDERLINE"] + tiers["EXCEPTION"]
    print(f"\n   -> {elig} companies ({elig/total*100:.0f}%) go through to Stage 2")

    print("\nWhich gate rejects the most?")
    fails, nears = collections.Counter(), collections.Counter()
    for r in out.values():
        for g in r.get("gates", []):
            if g["grade"] == "fail":
                fails[g["gate"]] += 1
            elif g["grade"] == "near-fail":
                nears[g["gate"]] += 1
    for g in sorted(set(fails) | set(nears)):
        print(f"   {g:24s} fail {fails[g]:3d}   near-fail {nears[g]:3d}")

    print("\nBy sector:")
    by_sec = collections.defaultdict(collections.Counter)
    for r in out.values():
        by_sec[r["sector"]][r["tier"]] += 1
    for sec in sorted(by_sec, key=lambda s: -sum(by_sec[s].values())):
        c = by_sec[sec]
        n = sum(c.values())
        p = c["PASS"] + c["BORDERLINE"] + c["EXCEPTION"]
        print(f"   {sec:26s} {p:3d}/{n:3d} eligible   "
              f"(pass {c['PASS']}, borderline {c['BORDERLINE']}, "
              f"rejected {c['REJECTED']}, n/a {c['CANNOT ASSESS']})")

    if errors:
        print(f"\nerrors ({len(errors)}): {errors[:6]}")
    if no_cik:
        print(f"no CIK ({len(no_cik)}): {no_cik[:10]}")
    print(f"\nwrote {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
