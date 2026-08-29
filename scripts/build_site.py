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

ELIGIBLE_TIERS = {"PASS", "BORDERLINE"}


def build() -> int:
    for f in (STAGE1, STAGE2, TEMPLATE):
        if not f.exists():
            print(f"error: {f.relative_to(ROOT)} not found")
            return 1

    s1 = json.loads(STAGE1.read_text())
    s2 = json.loads(STAGE2.read_text())
    sectors = {c["ticker"]: c["sector"] for c in load_sp500()}

    rows = []
    for t, r in s2.items():
        if not (r.get("far_below_normal") and r.get("eligible")):
            continue
        a = s1.get(t, {})
        asof = a.get("asof") or {}
        at_risk = a.get("at_risk") or []
        # the at-risk gate's own wording, straight from Stage 1 — the page
        # never restates a gate result in its own words
        risk = ""
        for g in a.get("gates", []):
            if g["gate"] in at_risk:
                risk = f"{g['gate']}|{g['detail']}"
        rows.append({
            "t": t, "n": r.get("name"), "s": sectors.get(t),
            "b": round(r["below_normal"] * 100, 1),
            "m2": round(r["d_ma200"] * 100, 1),
            "m5": round(r["d_ma50"] * 100, 1),
            "p": round(r["price"], 2), "sh": r["shape"],
            "lo": round(r["low52"], 2), "hi": round(r["high52"], 2),
            "c": round(r["market_cap"] / 1e9, 1) if r.get("market_cap") else None,
            "fy": asof.get("fiscal_year"), "pe": asof.get("period_end"),
            "y": r.get("yahoo"), "g": r.get("google"), "ar": risk,
            "gt": [[g["gate"], g["grade"], g["detail"]] for g in a.get("gates", [])],
        })
    rows.sort(key=lambda x: -x["b"])

    eligible = sum(1 for r in s1.values() if r["tier"] in ELIGIBLE_TIERS)
    n = len(rows)
    n_risk = sum(1 for r in rows if r["ar"])
    as_of = next((r.get("as_of") for r in s2.values() if r.get("as_of")), None)
    as_of_txt = (dt.date.fromisoformat(as_of).strftime("%a %-d %b %Y")
                 if as_of else "unknown")

    page = TEMPLATE.read_text()
    for k, v in {
        "ROWS": json.dumps(rows, separators=(",", ":")),
        "COUNT": str(n),
        # the page must read correctly when the answer is 1, or 0
        "NOUN": "company" if n == 1 else "companies",
        "VERB": "is" if n == 1 else "are",
        "BAR": f"{stage2.BELOW_NORMAL_BAR:.0%}".rstrip("%"),
        "ELIGIBLE": str(eligible),
        "UNIVERSE": str(len(s1)),
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
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(page):,} bytes)")
    print(f"   {n} of {eligible} companies more than "
          f"{stage2.BELOW_NORMAL_BAR:.0%} below normal · prices {as_of_txt}")
    print(f"   {n_risk} grazing a Stage 1 gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
