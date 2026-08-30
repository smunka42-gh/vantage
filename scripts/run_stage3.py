"""Run Stage 3 over the Stage 1 eligible list.

    export SEC_USER_AGENT="vantage you@example.com"
    python scripts/run_stage1.py     # must have been run first
    python scripts/run_stage2.py
    python scripts/run_stage3.py

One EDGAR request per company serves BOTH gates — annual EPS for gate 1
and quarterly operating income for gate 2 come out of the same
companyfacts document. Prices come from one bulk yfinance download.

Stage 3 annotates; it does not rank. Nothing here feeds back into the
Stage 2 ordering.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pandas as pd                                        # noqa: E402
import yfinance as yf                                      # noqa: E402
from funnel.stage1 import (S, _facts, _resolve_cik,          # noqa: E402
                           CHAINS as TAG_CHAINS)
from funnel.stage3 import cheapness, intact, label         # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "stage3_results.json"
ELIGIBLE_TIERS = {"PASS", "BORDERLINE"}

# Diluted EPS first: it is what a share actually earned after everything
# that could dilute it. All are per-share and restated for splits by the
# filer, so a price series adjusted the same way is comparable.
EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
            "EarningsPerShareBasic"]
# Operating income, with the same pre-tax fallback stage1 uses for
# companies that file no operating subtotal.
# Reuses stage1's proven chain rather than a shorter one of its own.
# A two-tag chain left Bank of New York and Arch Capital on quarters from
# 2016 and 2021: both are financials that file no OperatingIncomeLoss at
# all and abandoned the first fallback years ago.
OPINC_TAGS = list(TAG_CHAINS["op_income"])

# A chain also has to REACH THE PRESENT. Taking the freshest chain is not
# enough when every chain is stale — the result is a confident answer
# about 2016.
#
# The tolerance differs by period, and conflating them was a bug: one
# 400-day limit rejected Clorox, which has 18 years of EPS but whose
# newest ANNUAL figure was 426 days old simply because its next 10-K was
# not filed yet. An annual figure is legitimately 12-18 months old
# between filings; a quarter is not.
MAX_CHAIN_AGE = {"annual": 550, "quarter": 400}

ANNUAL = (350, 380)      # 52- and 53-week fiscal years
QUARTER = (80, 100)


def _periods(facts, tags, span, unit="USD", kind="annual"):
    """Reported figures of a given period LENGTH, keyed by end date.

    Length, not form: a 10-K carries quarters inside it too, which is the
    defect that made Accenture's return on assets read 2.7% instead of
    12.4% (§3.17).

    Among tag chains, take the one reaching the LATEST period rather than
    the first that matches. Chains are ordered by PREFERENCE and
    preference is unrelated to freshness — Lam Research still carries a
    `Revenues` series that stops in 2012.
    """
    lo, hi = span
    found = {}
    for tag in tags:
        node = facts.get("us-gaap", {}).get(tag)
        if not node:
            continue
        best = {}
        for u in node["units"].get(unit, []):
            if not u.get("start"):
                continue
            days = (dt.date.fromisoformat(u["end"])
                    - dt.date.fromisoformat(u["start"])).days
            if not (lo <= days <= hi):
                continue
            # A later filing restates an earlier one; take the newest.
            if u["end"] not in best or u["filed"] > best[u["end"]]["filed"]:
                best[u["end"]] = u
        if len(best) >= 3:
            found[tag] = best
    if not found:
        return {}
    freshest = max(found.values(), key=lambda b: max(b))
    stale_by = (dt.date.today() - dt.date.fromisoformat(max(freshest))).days
    # No usable series beats a stale one presented as current.
    return freshest if stale_by <= MAX_CHAIN_AGE[kind] else {}


def _yoy(periods, tolerance):
    """Each period against the one ending ~a year earlier, oldest first.

    Both figures are as filed. Nothing is reconstructed: no deriving Q4
    by subtraction, no summing quarters into a trailing twelve months.
    """
    ends, out = sorted(periods), []
    for end in ends:
        target = dt.date.fromisoformat(end) - dt.timedelta(days=365)
        near = [k for k in ends
                if abs((dt.date.fromisoformat(k) - target).days) <= tolerance]
        if not near:
            continue
        prior = periods[min(near, key=lambda k:
                            abs((dt.date.fromisoformat(k) - target).days))]
        if prior["val"] > 0:
            out.append((end, periods[end]["val"] / prior["val"] - 1))
    return out


def main() -> None:
    s1 = json.loads((HERE / "stage1_results.json").read_text())
    # Every company STAGE 1 ACTUALLY RAN ON — not just the eligible ones,
    # because the ticker lookup has to answer for rejected companies too
    # and "pricier than usual, profit falling" is exactly what explains
    # why one is not on the list. Only the eligible list is ever ranked.
    #
    # REITs are excluded because Stage 1 never assessed them: they are
    # judged on funds from operations, and their reported earnings are
    # depressed by depreciation, so an earnings YIELD understates the
    # whole asset class. Printing "pricier than usual" for every REIT
    # would contradict the page's own explanation of why they are skipped.
    # The rule is simply: whatever Stage 1 did not run on, Stage 3 does
    # not either.
    tickers = sorted(t for t, r in s1.items() if not r["tier"].startswith("REIT"))
    eligible = sum(1 for r in s1.values() if r["tier"] in ELIGIBLE_TIERS)
    print(f"{len(tickers)} constituents, {eligible} eligible from Stage 1\n")

    m = S.get("https://www.sec.gov/files/company_tickers.json", timeout=30).json()
    cik = {v["ticker"].replace(".", "-"): str(v["cik_str"]).zfill(10)
           for v in m.values()}

    # Six years so a five-year yield history has a price at every fiscal
    # year end. auto_adjust matches the split-restated EPS the filer reports.
    print("downloading prices...", flush=True)
    px = yf.download(tickers, period="6y", interval="1d", auto_adjust=True,
                     progress=False, threads=False)["Close"]
    print(f"   {px.shape[1]} series returned\n", flush=True)

    out, no_cik = {}, []
    for i, t in enumerate(tickers, 1):
        if t not in cik:
            no_cik.append(t)
            continue
        rec = {"tier": s1[t]["tier"],
               "eligible": s1[t]["tier"] in ELIGIBLE_TIERS}
        try:
            facts = _facts(cik[t])
            # Stage 1 resolves filers that moved to a new CIK; Exxon's
            # 2025 reorganisation left the new ID with almost no history,
            # so calling _facts directly returned nothing usable and
            # gate 1 silently reported "no earnings history".
            _, facts, _ = _resolve_cik(t, cik[t], facts)

            # --- gate 1 -------------------------------------------------
            eps = _periods(facts, EPS_TAGS, ANNUAL, unit="USD/shares")
            if len(eps) < 4:
                # Monster's EarningsPerShareDiluted stops in 2011 — it
                # changed how it tags, and it is not alone. Earnings per
                # share is net income divided by shares, so where the
                # ready-made figure is missing, divide. Both figures come
                # from the SAME filed annual period: this derives a ratio
                # like return on assets, it does not reconstruct a period.
                ni = (_periods(facts, ["NetIncomeLoss"], ANNUAL)
                      or _periods(facts, ["ProfitLoss"], ANNUAL))
                sh = _periods(facts, ["WeightedAverageNumberOfDilutedSharesOutstanding",
                                      "WeightedAverageNumberOfSharesOutstandingBasic"],
                              ANNUAL, unit="shares")
                shared = sorted(set(ni) & set(sh))
                if len(shared) >= 4:
                    eps = {e: {"val": ni[e]["val"] / sh[e]["val"], "derived": True}
                           for e in shared if sh[e]["val"]}
            series = px[t].dropna() if t in px else pd.Series(dtype=float)
            history, now = [], None
            if len(series):
                for end in sorted(eps)[-6:]:
                    upto = series[series.index <= pd.Timestamp(end)]
                    if len(upto):
                        history.append(eps[end]["val"] / float(upto.iloc[-1]))
                if eps:
                    now = eps[max(eps)]["val"] / float(series.iloc[-1])
            rec["cheap"] = cheapness(now, history)
            # The fiscal years each median is built from. "its own 0.66%
            # over three years" is not checkable without them.
            used = [e for e in sorted(eps)[-6:]
                    if len(series) and len(series[series.index <= pd.Timestamp(e)])]
            if used:
                rec["yield_years"] = {"3": used[-3:], "5": used[-5:]}
                # The yields themselves, so the five-year record can show
                # the trend the two medians are drawn from.
                rec["yield_series"] = [round(v * 100, 2) for v in history[-5:]]
                rec["yield_ends"] = used[-5:]
                rec["eps_asof"] = max(eps)

            # --- gate 2 -------------------------------------------------
            quarters = _periods(facts, OPINC_TAGS, QUARTER, kind="quarter")
            yoy = _yoy(quarters, tolerance=20)
            rec["intact"] = intact([v for _, v in yoy])
            if yoy:
                rec["quarter_ends"] = [q[0] for q in yoy[-2:]]
                rec["quarter_end"] = yoy[-1][0]
                rec["quarter_age_days"] = (
                    dt.date.today() - dt.date.fromisoformat(yoy[-1][0])).days

            rec["label"] = label(rec["cheap"], rec["intact"])
            out[t] = rec
        except Exception as e:                              # noqa: BLE001
            out[t] = {"tier": s1[t]["tier"],
                      "eligible": s1[t]["tier"] in ELIGIBLE_TIERS,
                      "cheap": None, "intact": None,
                      "label": "not enough history", "error": str(e)[:60]}
        if i % 60 == 0:
            print(f"   ...{i}/{len(tickers)}", flush=True)
        time.sleep(0.11)                                    # SEC fair-use

    OUT.write_text(json.dumps(out, indent=1))

    import collections
    print(f"\n{'='*62}\nSTAGE 3 — {len(out)} companies\n{'='*62}")
    el = [r for r in out.values() if r.get("eligible")]
    print(f"   gate 1 usable: {sum(1 for r in out.values() if r.get('cheap')):3d}"
          f"   (of the eligible: {sum(1 for r in el if r.get('cheap')):3d}/{len(el)})")
    print(f"   gate 2 usable: {sum(1 for r in out.values() if r.get('intact')):3d}"
          f"   (of the eligible: {sum(1 for r in el if r.get('intact')):3d}/{len(el)})")
    ages = sorted(r["quarter_age_days"] for r in out.values()
                  if r.get("quarter_age_days") is not None)
    if ages:
        print(f"   newest quarter: median {ages[len(ages)//2]}d, "
              f"p90 {ages[9*len(ages)//10]}d, max {ages[-1]}d")
    print()
    for lab, n in collections.Counter(r["label"] for r in out.values()).most_common():
        print(f"   {lab:38s} {n:4d}")
    falling = sorted(t for t, r in out.items()
                     if r.get("intact") and r["intact"]["falling"])
    print(f"\n   profit falling ({len(falling)}): {', '.join(falling)}")
    if no_cik:
        print(f"   no CIK: {no_cik}")
    print(f"\nwrote {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
