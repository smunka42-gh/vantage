"""Render the public page from the latest scan.

Reads the two results files and fills site/template.html, writing
docs/index.html — which is what GitHub Pages serves.

    python scripts/run_stage1.py     # quarterly, on filings
    python scripts/run_stage2.py     # daily, on prices
    python scripts/build_site.py     # then rebuild the page

The page is static by design. Everything it shows was decided by the
scan; nothing is computed in the browser except sorting and expanding a
row. That is why it can live on a CDN with no server to sleep, wedge or
restart — the failure mode that took the predecessor down.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel import stage2                                   # noqa: E402
from funnel.universe import load_sp500                      # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGE1 = ROOT / "scripts/stage1_results.json"
STAGE2 = ROOT / "scripts/stage2_results.json"
TEMPLATE = ROOT / "site/template.html"
OUT = ROOT / "docs/index.html"
SCAN = ROOT / "docs/scan.json"

ELIGIBLE_TIERS = {"PASS", "BORDERLINE"}


def build() -> int:
    for f in (STAGE1, STAGE2, TEMPLATE):
        if not f.exists():
            print(f"error: {f.relative_to(ROOT)} not found")
            return 1

    s1 = json.loads(STAGE1.read_text())
    s2 = json.loads(STAGE2.read_text())
    sectors = {c["ticker"]: c["sector"] for c in load_sp500()}

    def _series_for(a):
        """The five-year rows, with the bar each was judged against.

        Coverage is included ONLY when gate 4 actually used it. A bank's
        interest expense IS its business — JPMorgan's coverage reads 0.8x
        with interest at 132% of profit — so the ratio is meaningless
        wherever the gate fell back to equity/assets, and showing it would
        invite a conclusion the gate never drew.
        """
        sr = a.get("series") or {}
        if not sr.get("years"):
            return None
        gate = {g["gate"][:1]: g["detail"] for g in a.get("gates", [])}
        rows = []
        if sr.get("return"):
            bar = "10%" if "equity" in sr.get("return_label", "") else "8%"
            rows.append([sr["return_label"], sr["return"], bar])
        if sr.get("margin"):
            rows.append(["operating margin", sr["margin"], "70% of 3y avg"])
        if sr.get("coverage") and "interest coverage" in gate.get("4", ""):
            rows.append(["interest coverage", sr["coverage"], "4.0x"])
        # Only where gate 6 ran the ratio test. Where it passed on growth
        # the 3-year average was never the bar, and showing it with one
        # would imply a test that did not happen (tenet 2).
        if sr.get("revenue") and "3y average" in gate.get("6", ""):
            rows.append(["revenue ($bn)", sr["revenue"], "own 3y avg"])
        return {"years": sr["years"], "rows": rows} if rows else None

    def pack(t, r, a):
        """One company, in the shape the page reads."""
        asof = a.get("asof") or {}
        at_risk = a.get("at_risk") or []
        # the at-risk gate's own wording, straight from Stage 1 — the page
        # never restates a gate result in its own words
        risk = ""
        for g in a.get("gates", []):
            if g["gate"] in at_risk:
                risk = f"{g['gate']}|{g['detail']}"
        # Every price field is optional. The lookup answers for companies
        # the funnel never priced — REITs, and names with too little
        # history — so a missing figure must travel as null rather than
        # crash the build or, worse, be filled in with a zero.
        def pct(key):
            v = r.get(key)
            return None if v is None else round(v * 100, 1)

        def usd(key):
            v = r.get(key)
            return None if v is None else round(v, 2)

        return {
            "t": t, "n": r.get("name") or a.get("name"), "s": sectors.get(t),
            "tier": a.get("tier"),
            "b": pct("below_normal"),
            "m2": pct("d_ma200"),
            "m5": pct("d_ma50"),
            "p": usd("price"), "sh": r.get("shape"),
            "lo": usd("low52"), "hi": usd("high52"),
            "c": round(r["market_cap"] / 1e9, 1) if r.get("market_cap") else None,
            "fy": asof.get("fiscal_year"), "pe": asof.get("period_end"),
            "y": r.get("yahoo"), "g": r.get("google"), "ar": risk,
            "gt": [[g["gate"], g["grade"], g["detail"]] for g in a.get("gates", [])],
            "sr": _series_for(a),
        }

    # The ranked list: only what clears the bar.
    rows = [pack(t, r, s1.get(t, {})) for t, r in s2.items()
            if r.get("far_below_normal") and r.get("eligible")]
    rows.sort(key=lambda x: -x["b"])

    # Every company, for the lookup. A static page cannot fetch live —
    # SEC and Yahoo both block cross-origin browser requests — so the
    # answer has to already be here. It compresses to a few KB.
    everything = sorted(
        (pack(t, s2.get(t, {}), a) for t, a in s1.items()),
        key=lambda x: x["t"])

    eligible = sum(1 for r in s1.values() if r["tier"] in ELIGIBLE_TIERS)
    # The gates never run on REITs, so "all 500 are tested" was untrue
    reits = sum(1 for r in s1.values()
                if str(r.get("tier", "")).startswith("REIT"))
    n = len(rows)
    n_risk = sum(1 for r in rows if r["ar"])
    as_of = next((r.get("as_of") for r in s2.values() if r.get("as_of")), None)
    as_of_txt = (dt.date.fromisoformat(as_of).strftime("%a %-d %b %Y")
                 if as_of else "unknown")

    page = TEMPLATE.read_text()
    for k, v in {
        "ROWS": json.dumps(rows, separators=(",", ":")),
        "ALL": json.dumps(everything, separators=(",", ":")),
        "COUNT": str(n),
        # the page must read correctly when the answer is 1, or 0
        "NOUN": "company" if n == 1 else "companies",
        "VERB": "is" if n == 1 else "are",
        "BAR": f"{stage2.BELOW_NORMAL_BAR:.0%}".rstrip("%"),
        "ELIGIBLE": str(eligible),
        "UNIVERSE": str(len(s1)),
        "REITS": str(reits),
        "TESTED": str(len(s1) - reits),
        "ATRISK": {0: "None", 1: "One"}.get(n_risk, str(n_risk)),
        "ATRISK_VERB": "is" if n_risk == 1 else "are",
        "ASOF": as_of_txt,
        "TODAY": dt.date.today().isoformat(),
    }.items():
        page = page.replace("{{" + k + "}}", v)

    if "{{" in page:
        print("error: unfilled placeholder remains — refusing to write")
        return 1

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)

    # The state the daily workflow's gate reads to answer "have we already
    # scanned today?". Written HERE, by the same run that renders the page,
    # so the two can never disagree.
    #
    # It used to be written by the workflow instead, which meant every
    # local rebuild left it behind: the published page read 262 eligible
    # and 17 below normal while the published scan.json still said 258 and
    # 16. Two writers, one of which only ran in CI. Now there is one.
    SCAN.write_text(json.dumps({
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prices_as_of": as_of,
        "universe": len(s1),
        "eligible": eligible,
        "below_normal": n,
    }, indent=1) + "\n")

    print(f"wrote {OUT.relative_to(ROOT)}  ({len(page):,} bytes)")
    print(f"wrote {SCAN.relative_to(ROOT)}")
    print(f"   {n} of {eligible} companies more than "
          f"{stage2.BELOW_NORMAL_BAR:.0%} below normal · prices {as_of_txt}")
    print(f"   {n_risk} grazing a Stage 1 gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
