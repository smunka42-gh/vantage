"""Do the documents still describe what the code actually does?

Every documentation failure in this project has been the same shape: a
document asserting a fact that the data had since changed. The spec said
v0.7 while the code was at v2.7. The README said "UI not started" days
after the site shipped. A memory file said "there is no Stage 3" the
night Stage 3 was built.

None of those was caught by review, because a stale sentence reads
exactly like a fresh one. They are all catchable by COMPARISON, which is
what this does. It is deliberately mechanical: a rule someone has to
remember is the thing that already failed.

    python tests/test_docs_current.py

Exits non-zero on failure, so the daily scan and a commit can gate on it.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/FUNNEL_SPEC.md"
README = ROOT / "README.md"
SCAN = ROOT / "docs/scan.json"
PAGE = ROOT / "docs/index.html"
S1 = ROOT / "scripts/stage1_results.json"

problems: list[str] = []


def check(ok: bool, msg: str) -> None:
    if not ok:
        problems.append(msg)


def main() -> int:
    spec = SPEC.read_text()
    readme = README.read_text()

    # 1. The spec's header version must match its newest changelog entry.
    #    These drifted apart once already.
    header = re.search(r"Funnel Spec (v[\d.]+)", spec)
    newest = re.search(r"\|\s*\*\*(v[\d.]+)\*\*\s*\|", spec)
    if header and newest:
        check(header.group(1) == newest.group(1),
              f"spec header says {header.group(1)} but the newest changelog "
              f"entry is {newest.group(1)}")

    # 2. Every module and script the README names must exist. The README
    #    listed five gates after a sixth was added, and omitted Stage 3
    #    entirely for a while.
    for path in re.findall(r"^(funnel/\S+\.py|scripts/\S+\.py|tests/\S+\.py)",
                           readme, re.M):
        check((ROOT / path).exists(), f"README names {path}, which does not exist")
    for path in sorted(ROOT.glob("funnel/*.py")):
        if path.name == "__init__.py":
            continue
        check(path.name in readme, f"{path.name} exists but the README never mentions it")
    for path in sorted(ROOT.glob("scripts/run_*.py")):
        check(path.name in readme, f"{path.name} exists but the README never mentions it")

    # 3. CURRENT counts must match the data. Deliberately narrow: a
    #    changelog entry saying "239 eligible" is a correct historical
    #    record, and flagging it would train everyone to ignore this test
    #    — which is how the last over-eager check earned 18 false
    #    positives in one run.
    if SCAN.exists():
        scan = json.loads(SCAN.read_text())
        eligible = scan.get("eligible")

        # the README states the live figure in bold in its Status section
        status = readme.split("## Status", 1)[-1].split("##", 1)[0]
        for m in re.finditer(r"\*\*(\d[\d,]*) eligible\*\*", status):
            check(int(m.group(1).replace(",", "")) == eligible,
                  f"README Status says '{m.group(1)} eligible' but the last "
                  f"scan produced {eligible}")

        # the spec states it once, in the full-index result table
        for m in re.finditer(r"\| \*\*Eligible for Stage 2\*\* \| \*\*(\d+)\*\*", spec):
            check(int(m.group(1)) == eligible,
                  f"spec §3.19 says '{m.group(1)} eligible' but the last "
                  f"scan produced {eligible}")

    # 4. The number of gates the docs claim must match the code.
    # DISTINCT gate numbers: each gate appends once per branch, so
    # counting append calls gave 16 for six gates.
    gates = len(set(re.findall(r'out\.append\(\("(\d) ',
                               (ROOT / "funnel/stage1.py").read_text())))
    # A "*(Revised vX ...)*" note exists precisely to record what a
    # document USED to say, so its contents are quotations, not claims.
    # Without this the spec's own correction of "the five gates" trips
    # the check that made it write the correction.
    strip_revisions = lambda t: re.sub(r"\*\(Revised .*?\)\*", "", t, flags=re.S)
    spec_now = strip_revisions(
        spec.split("### Version history", 1)[0] +
        spec.split("## 1. The thesis", 1)[-1])
    for doc, name in ((readme, "README"), (spec_now, "spec")):
        # "across three gates" counts gates that share a property; it is
        # not a claim about how many exist. Only totals are checked.
        for m in re.finditer(r"(?<!across )(?<!of )\b(\w+) (?:quality )?gates\b", doc):
            word = m.group(1).lower()
            words = {"five": 5, "six": 6, "seven": 7, "four": 4, "three": 3}
            if word in words:
                check(words[word] == gates,
                      f"{name} says '{m.group(0)}' but stage1.py implements {gates}")

    # 5. The built page must have no unfilled placeholders.
    if PAGE.exists():
        left = set(re.findall(r"\{\{[A-Z_]+\}\}", PAGE.read_text()))
        check(not left, f"built page still contains placeholders: {sorted(left)}")

    # 6. Memory must hold no counts — they rot, and pointers do not.
    mem = (pathlib.Path.home() /
           ".claude/projects/<derived-from-repo-location>/memory")
    if mem.exists() and S1.exists():
        live = {str(len(json.loads(S1.read_text())))}
        if SCAN.exists():
            sc = json.loads(SCAN.read_text())
            live |= {str(sc.get("eligible")), str(sc.get("below_normal"))}
        for f in mem.glob("*vantage*.md"):
            text = f.read_text()
            for n in live:
                check(n and n not in text,
                      f"{f.name} contains the live count {n} — memory stores "
                      f"pointers, not snapshots, because counts go stale")

    print(f"{'=' * 62}\nDOCUMENTATION CURRENCY\n{'=' * 62}")
    if not problems:
        print("  ok — spec, README, page and memory all agree with the data")
        return 0
    for p in problems:
        print(f"  STALE: {p}")
    print(f"\n{len(problems)} document(s) describe something the code no longer does.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
