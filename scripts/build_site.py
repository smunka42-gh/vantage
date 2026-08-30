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
STAGE3 = ROOT / "scripts/stage3_results.json"
TEMPLATE = ROOT / "site/template.html"
OUT = ROOT / "docs/index.html"
SCAN = ROOT / "docs/scan.json"

ELIGIBLE_TIERS = {"PASS", "BORDERLINE"}

# The reader-facing name for a Stage 1 tier. "uncertain" is deliberate:
# CANNOT ASSESS means the funnel could not measure the company, which is
# not a quality verdict and must not read as one.
QUALITY = {"PASS": "high", "BORDERLINE": "medium",
           "REJECTED": "low", "CANNOT ASSESS": "uncertain"}


def _built() -> str:
    """When this page was generated, and from which commit if known."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y %H:%M UTC")
    try:
        import subprocess
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=5).stdout.strip()
        if sha:
            stamp += f" · {sha}"
    except Exception:                                       # noqa: BLE001
        pass
    return stamp


def build() -> int:
    for f in (STAGE1, STAGE2, TEMPLATE):
        if not f.exists():
            print(f"error: {f.relative_to(ROOT)} not found")
            return 1

    s1 = json.loads(STAGE1.read_text())
    s2 = json.loads(STAGE2.read_text())
    # Stage 3 is optional: the page must still build from stages 1 and 2
    # alone, so a missing file degrades to no annotation rather than a
    # crash. It ANNOTATES the ranking and never reorders it (spec §5.4).
    s3 = json.loads(STAGE3.read_text()) if STAGE3.exists() else {}
    sectors = {c["ticker"]: c["sector"] for c in load_sp500()}

    def _series_for(t, a):
        """The five-year record, GROUPED by the question each row answers.

        Ungrouped, the reader had no way to tell which trend belonged to
        which stage. Each group carries the question its stage asks, so a
        row is never orphaned from the thing it is evidence for.

        Two rows stay conditional, both under tenet 2 — do not display
        what was not used:

          * coverage only where gate 4 actually used it. A bank's interest
            expense IS its business (JPMorgan reads 0.8x), so the ratio is
            meaningless wherever the gate fell back to equity/assets.
          * revenue only where gate 6 ran the 3-year-average test. Where it
            passed on growth, that average was never the bar.
        """
        sr = a.get("series") or {}
        if not sr.get("years"):
            return None
        gate = {g["gate"][:1]: g["detail"] for g in a.get("gates", [])}
        own = []
        if sr.get("return"):
            bar = "10%" if "equity" in sr.get("return_label", "") else "8%"
            own.append([sr["return_label"], sr["return"], bar])
        if sr.get("margin"):
            own.append(["operating margin", sr["margin"], "70% of 3y avg"])
        if sr.get("net_income"):
            own.append(["net income ($bn)", sr["net_income"], "above 0"])
        if sr.get("fcf"):
            own.append(["free cash flow ($bn)", sr["fcf"], "5y sum above 0"])
        if sr.get("coverage") and "interest coverage" in gate.get("4", ""):
            own.append(["interest coverage", sr["coverage"], "4.0x"])
        if sr.get("revenue") and "3y average" in gate.get("6", ""):
            own.append(["revenue ($bn)", sr["revenue"], "own 3y avg"])

        groups = []
        if own:
            groups.append({"stage": 1, "q": "Stage 1 — would I ever want to own this?",
                           "barhead": "at least",
                           "years": sr["years"], "rows": own})

        # Stage 3's own trend: the yields its two medians are drawn from.
        # Its own fiscal years, which need not match Stage 1's window.
        r3 = s3.get(t) or {}
        ys, ye = r3.get("yield_series"), r3.get("yield_ends")
        cheap = r3.get("cheap")
        if ys and ye and len(ys) == len(ye):
            # TODAY as the final column. Without it the card quotes one
            # figure ("a dollar buys 1.95%") and the row ends on another
            # (2.1 for 2025) and they read as a contradiction — they are
            # the same measure on different DATES, which the row label
            # alone was too quiet about.
            today = round(cheap["now"], 1) if cheap else None
            meds = (cheap or {}).get("medians") or {}
            m3 = meds.get("3", meds.get(3))
            m5 = meds.get("5", meds.get(5))
            # publish the medians rather than naming them: every other
            # row's bar column carries a NUMBER, so this one should too
            bar = (f"{m3:.1f}% / {m5:.1f}%" if m3 is not None and m5 is not None
                   else "—")
            groups.append({
                "stage": 3, "q": "Stage 3 — is it cheaper than usual?",
                # not "at least": a yield is compared with a median, not
                # required to clear a minimum
                "barhead": "its own median",
                "years": [e[:4] for e in ye] + (["today"] if today is not None else []),
                # "at year end" matters: each value uses the price on that
                # fiscal year end, while the Stage 3 card quotes today's
                # yield. Same measure, different dates — without the label
                # the two read as a contradiction.
                "rows": [["earnings yield (%)",
                          ys + ([today] if today is not None else []), bar]]})
        return {"groups": groups} if groups else None

    def _size_of(cap):
        """Size bucket, labelled by its RANGE rather than large/mid/small.

        Measured across the index: 86% of the S&P 500 is "large cap" by
        conventional thresholds and there are NO small caps — the
        smallest company is $6.4bn. Conventional labels would put almost
        everything in one bucket, and index-relative ones would call a
        $20bn company "small cap", which is wrong by any market reading.
        The ranges say what they mean and need no convention.

        These split 4% / 22% / 74%, which is deliberately uneven: they
        are the numbers people actually think in, and the useful cut is
        at the top — 18 companies over $500bn — rather than an even
        three-way division at figures ($28bn) nobody recognises.
        """
        if not cap:
            return None
        bn = cap / 1e9
        return ("over $500bn" if bn > 500 else
                "$100-500bn" if bn >= 100 else "under $100bn")

    def _stage3_for(t):
        """Stage 3's label and the evidence behind it.

        Carries the AGE of the quarterly evidence, which is not decoration:
        a company just past its fiscal year end files no Q4 10-Q, so its
        newest quarter can honestly be ~6 months old. The reader has to be
        able to see that rather than trust a bare label (spec §5.4).
        """
        r = s3.get(t)
        if not r or r.get("label") in (None, "not enough history"):
            return None
        c, i = r.get("cheap"), r.get("intact")
        return {
            "l": r["label"],
            # yield now, and its own two medians, as real percentages
            "y": None if not c else [round(c["now"], 2),
                                     round(c["medians"]["3"], 2) if "3" in c["medians"]
                                     else round(c["medians"][3], 2),
                                     round(c["medians"]["5"], 2) if "5" in c["medians"]
                                     else round(c["medians"][5], 2)],
            # the two year-on-year quarters the gate actually judged
            "q": None if not i else [round(v * 100, 1) for v in i["recent"]],
            "qe": r.get("quarter_end"), "qa": r.get("quarter_age_days"),
            "qq": r.get("quarter_ends"),
            # first and last fiscal year behind each median, so the page
            # can say WHICH three years "over three years" means
            "yy": None if not r.get("yield_years") else {
                k: [v[0][:4], v[-1][:4]] for k, v in r["yield_years"].items()},
        }

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
            "sr": _series_for(t, a),
            "s3": _stage3_for(t),
            "q": QUALITY.get(a.get("tier")),
            "z": _size_of(r.get("market_cap")),
        }

    # ONE list: every company Stage 1 assessed, ranked by how far below its
    # own usual price it trades. The page filters this rather than the
    # build pre-selecting — the 10% bar and the quality gate are now
    # filter DEFAULTS, not a hard cut, so nothing is hidden and the
    # separate ticker-lookup row is no longer needed.
    #
    # A static page cannot fetch live (SEC and Yahoo both block
    # cross-origin browser requests), so every answer has to already be
    # here. It compresses well.
    rows = [pack(t, s2.get(t, {}), a) for t, a in s1.items()
            if not (a.get("tier") or "").startswith("REIT")]
    rows.sort(key=lambda x: (x["b"] is None, -(x["b"] or 0)))

    eligible = sum(1 for r in s1.values() if r["tier"] in ELIGIBLE_TIERS)
    # The gates never run on REITs, so "all 500 are tested" was untrue
    reits = sum(1 for r in s1.values()
                if str(r.get("tier", "")).startswith("REIT"))
    # The table now holds every assessed company and the page filters it,
    # so these describe the DEFAULT VIEW — high quality, at least the bar
    # below its usual price — not the whole table.
    default_view = [r for r in rows
                    if r["q"] == "high" and (r["b"] or 0) >= stage2.BELOW_NORMAL_BAR * 100]
    n = len(default_view)
    n_risk = sum(1 for r in default_view if r["ar"])
    as_of = next((r.get("as_of") for r in s2.values() if r.get("as_of")), None)
    as_of_txt = (dt.date.fromisoformat(as_of).strftime("%a %-d %b %Y")
                 if as_of else "unknown")

    page = TEMPLATE.read_text()
    for k, v in {
        "ROWS": json.dumps(rows, separators=(",", ":")),
        "COUNT": str(n),
        # the page must read correctly when the answer is 1, or 0
        "VERB": "is" if n == 1 else "are",
        "BAR": f"{stage2.BELOW_NORMAL_BAR:.0%}".rstrip("%"),
        "ELIGIBLE": str(eligible),
        "UNIVERSE": str(len(s1)),
        "REITS": str(reits),
        "TESTED": str(len(s1) - reits),
        "ASOF": as_of_txt,
        "TODAY": dt.date.today().isoformat(),
        # A build stamp, GENERATED — never hand-written. v2.6 removed a
        # hardcoded spec version from the footer precisely because it had
        # gone stale. This says when the page was actually rebuilt, which
        # is the one thing that cannot be wrong, and makes it obvious at a
        # glance whether the daily scan ran.
        "BUILT": _built(),
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
