"""The Stage 1 regression test.

Seventeen companies where the right answer is known independently of this
code. It exists to stop the gates being tuned until they merely flatter
whichever names happen to be in the test set — every threshold change
must be run past it, and it fails loudly if any anchor moves.

Hits the live SEC EDGAR API, so it takes about twenty seconds and needs
a contact address:

    export SEC_USER_AGENT="vantage you@example.com"
    python tests/test_golden_set.py

Exits non-zero on failure, so it can gate a commit or a CI step.
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from funnel.stage1 import S, load, run, decide, eligible      # noqa: E402

# Positives are the high-conviction compounders, plus names the S&P 500
# Quality Index independently selects. Negatives are widely-recognised
# quality-deterioration cases.
#
# Debatable names — TXN, CSCO, GE, ORCL, CVS, DG, EL — are deliberately
# EXCLUDED. A golden set may only contain cases we are certain about, or
# it stops being a reliable alarm.
EXPECTED = {
    "AMZN": True, "META": True, "AAPL": True, "NVDA": True, "NFLX": True,
    "GOOG": True, "BRK-B": True, "COST": True, "WMT": True, "MA": True,
    "V": True, "ISRG": True, "MSFT": True,
    "INTC": False, "BA": False, "F": False, "MMM": False,
}

# Judged on the financials track: Berkshire is an insurer, and the card
# networks carry no meaningful operating-income subtotal.
FINANCIALS = {"BRK-B", "V", "MA"}


def main() -> int:
    m = S.get("https://www.sec.gov/files/company_tickers.json", timeout=30).json()
    cik = {v["ticker"].replace(".", "-"): str(v["cik_str"]).zfill(10)
           for v in m.values()}

    results, verdict = {}, {}
    for t in EXPECTED:
        results[t] = run(t, load(t, cik[t]), is_financial=t in FINANCIALS)
        verdict[t] = eligible(decide(results[t], t))
        time.sleep(0.2)                          # SEC fair-use pacing

    def block(title: str, names: list[str]) -> None:
        print(f"\n{title}")
        print(f"  {'tkr':7s} {'got':>6s} {'want':>6s}  {'':2s} failing gates")
        print("  " + "-" * 62)
        for t in names:
            agree = verdict[t] == EXPECTED[t]
            bad = ", ".join(
                f"{n.split()[0]}{'~' if o == 'near-fail' else ''}"
                for n, o, _ in results[t] if o in ("fail", "near-fail"))
            print(f"  {t:7s} {('PASS' if verdict[t] else 'FAIL'):>6s} "
                  f"{('PASS' if EXPECTED[t] else 'FAIL'):>6s}  "
                  f"{'ok' if agree else '<<':2s} {bad or '—'}")

    block("POSITIVES — must pass", [t for t in EXPECTED if EXPECTED[t]])
    block("NEGATIVES — must fail", [t for t in EXPECTED if not EXPECTED[t]])

    wrong = [t for t in EXPECTED if verdict[t] != EXPECTED[t]]
    print("\n" + "=" * 66)
    if not wrong:
        print(f"REGRESSION TEST: PASS — all {len(EXPECTED)} anchors "
              f"behaved as specified")
        return 0

    print(f"REGRESSION TEST: FAIL — {len(wrong)} anchor(s) moved: "
          f"{', '.join(wrong)}")
    for t in wrong:
        print(f"\n  {t} detail:")
        for name, outcome, detail in results[t]:
            print(f"     {(outcome or 'n/a'):>10s}  {name:22s} {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
