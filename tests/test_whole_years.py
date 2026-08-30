"""A quarter must never be mistaken for a fiscal year.

A 10-K carries the QUARTERS inside it as well as the year, and some
filers tag those `fp=FY` too. `_pick` groups facts by the year in their
end-date and keeps the newest-FILED one, so where a quarter and the year
are filed on the SAME DAY the tie-break falls to the order they happen to
appear in EDGAR's JSON — and the quarter can win.

That happened. Accenture's return on assets read 2.7% instead of 12.4%:
one quarter's profit over a full year's balance sheet. The error is
one-directional — a part-year profit against a full-year balance sheet
always understates — so it could only ever wrongly REJECT a good company.

`_pick` now requires a duration fact to span 350-380 days, and this is
the test that pins that rule in place.

Why a unit test rather than a check over the live index: the bug was
invisible to the golden set, because not one of its seventeen anchors was
affected — all seventeen passed both before and after the fix. And an
index-wide check could only ever fire if someone edited `_pick`, at the
cost of a pass over 500 companies on every scan. The rule is structural,
so the test belongs on the function, pinned to the data that broke it.

The predecessor of this test inferred a part-year figure from a REVENUE
COLLAPSE — flagging any year under 30% of the one before. That was a
guess about values standing in for a fact about periods, and it sat in a
12-point gap it could not see into: Accenture's quarter posing as its
year was 0.22 of the prior year, while Western Digital's entirely real
FY2023 collapse was 0.34. It is replaced by this.

    python tests/test_whole_years.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from funnel.stage1 import _pick

problems: list[str] = []


def check(ok: bool, msg: str) -> None:
    if not ok:
        problems.append(msg)


def fact(start, end, val, filed, fp="FY"):
    f = {"form": "10-K", "fp": fp, "end": end, "val": val, "filed": filed}
    if start:
        f["start"] = start
    return f


def facts_for(entries, tag="Revenues"):
    return {"us-gaap": {tag: {"units": {"USD": entries}}}}


YEAR = 10_230_000_000        # Accenture FY2025 revenue, 364 days
QUARTER = 2_240_000_000      # the quarter inside it, 89 days, tagged FY


def main() -> int:
    # --- 1. the exact shape that broke, with the quarter listed FIRST ---
    # Both are filed the same day, so the newest-filed tie-break cannot
    # separate them and the first one encountered wins. Only the period
    # length can tell them apart.
    accenture = [
        fact("2024-12-01", "2025-02-28", QUARTER, "2025-09-25"),   # 89 days
        fact("2024-09-01", "2025-08-31", YEAR,    "2025-09-25"),   # 364 days
        fact("2023-09-01", "2024-08-31", 9_000_000_000, "2024-09-26"),
        fact("2022-09-01", "2023-08-31", 8_500_000_000, "2023-09-27"),
        fact("2021-09-01", "2022-08-31", 8_000_000_000, "2022-09-28"),
    ]
    got = _pick(facts_for(accenture), ["Revenues"], instant=False)
    check(got.get("2025") == YEAR,
          f"the 89-day quarter won FY2025: picked {got.get('2025'):,} "
          f"instead of {YEAR:,}" if got.get("2025") else
          "FY2025 was dropped entirely")
    check(QUARTER not in got.values(),
          "a quarter's value appears in the series at all")

    # --- 2. a 53-week fiscal year must still be accepted ----------------
    # The rule has to admit 52- and 53-week calendars, or it would reject
    # every retailer. 371 days is a real 53-week year.
    week53 = [
        fact("2024-01-29", "2025-02-03", 5_000_000_000, "2025-03-20"),  # 371
        fact("2023-01-30", "2024-01-28", 4_800_000_000, "2024-03-20"),
        fact("2022-01-31", "2023-01-29", 4_600_000_000, "2023-03-20"),
        fact("2021-02-01", "2022-01-30", 4_400_000_000, "2022-03-20"),
    ]
    got = _pick(facts_for(week53), ["Revenues"], instant=False)
    check(got.get("2025") == 5_000_000_000,
          "a 371-day (53-week) fiscal year was rejected — the rule is too "
          "tight and would exclude retailers")

    # --- 3. an over-long period is not an annual figure -----------------
    # A transition year after a calendar change can span far more than a
    # year. It is not comparable to the others and must not be scored.
    stretched = list(week53)
    stretched[0] = fact("2023-12-01", "2025-02-03", 6_000_000_000, "2025-03-20")
    got = _pick(facts_for(stretched), ["Revenues"], instant=False)
    check(got.get("2025") != 6_000_000_000,
          "a 430-day period was accepted as a fiscal year")

    # --- 4. instant facts carry no start date and are exempt ------------
    # Assets and equity are a snapshot on one date. Applying a duration
    # rule to them would discard every balance-sheet figure we have.
    balance = [
        fact(None, "2025-08-31", 55_000_000_000, "2025-09-25"),
        fact(None, "2024-08-31", 51_000_000_000, "2024-09-26"),
        fact(None, "2023-08-31", 48_000_000_000, "2023-09-27"),
        fact(None, "2022-08-31", 45_000_000_000, "2022-09-28"),
    ]
    got = _pick(facts_for(balance, "Assets"), ["Assets"], instant=True)
    check(got.get("2025") == 55_000_000_000,
          "an instant fact was rejected for having no start date")

    print(f"{'=' * 62}\nWHOLE YEARS — a quarter is never a fiscal year\n{'=' * 62}")
    if problems:
        for p in problems:
            print(f"  FAIL — {p}")
        print(f"\n  {len(problems)} failure(s)")
        return 1
    print("  ok — the quarter loses to the year on the tie it once won,")
    print("       53-week years are kept, over-long periods are not,")
    print("       and balance-sheet snapshots are exempt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
