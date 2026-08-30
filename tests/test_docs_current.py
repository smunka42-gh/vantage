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

import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/FUNNEL_SPEC.md"
README = ROOT / "README.md"
SCAN = ROOT / "docs/scan.json"
PAGE = ROOT / "docs/index.html"
SIMPLE = ROOT / "docs/simple/index.html"
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

        # Digits slipped past that: the tier table read "4 of the 5 gates
        # evaluable" for two versions after gate 6 landed, because the map
        # holds only spelled-out numbers. Adding digits to the pattern
        # above produced false positives on real phrases — "the two Stage
        # 3 gates", "Intel fails 4 gates" — so the digit form gets a
        # tighter anchor instead. A TOTAL is written "the N gates" or
        # "all N gates"; a count of some subset is not.
        for m in re.finditer(r"\b(?:all|the) (\d+) (?:quality )?gates\b",
                             doc, re.I):
            check(int(m.group(1)) == gates,
                  f"{name} says '{m.group(0)}' but stage1.py implements {gates}")

    # 5. Neither built page may carry an unfilled placeholder. The simple
    #    page is checked too: it inlines site/detail.js, which carries a
    #    {{TODAY}} of its own, so a change to the substitution ORDER in
    #    build_site.py can leave it unresolved on one page and not the other.
    for path, name in ((PAGE, "built page"), (SIMPLE, "simple page")):
        if path.exists():
            left = set(re.findall(r"\{\{[A-Z_]+\}\}", path.read_text()))
            check(not left, f"{name} still contains placeholders: {sorted(left)}")

    # 5b. A page that has quietly stopped updating.
    #
    # Measured 30 Aug 2026: GitHub fires the schedule but unreliably — one
    # firing in ~22 opportunities, 4h 18m late. Any single miss is
    # harmless (a delayed run has 16.5h of slack before the next open, and
    # the state gate makes it still correct), but several consecutive days
    # of silence would leave the page stale behind a green tick, because a
    # run that never happens cannot fail.
    #
    # FIVE days, not three. The workflow commits only when the PAGE
    # changes, so a market holiday produces no commit at all:
    #     normal weekend        Fri -> Mon = 3 days
    #     Monday holiday        Fri -> Tue = 4 days
    #     Thu+Fri+Mon closed    Thu -> Tue = 5 days
    # Three would fire every ordinary weekend, which is how a check earns
    # being ignored.
    if SCAN.exists():
        stamp = json.loads(SCAN.read_text()).get("generated_utc")
        if stamp:
            age = (dt.datetime.now(dt.timezone.utc)
                   - dt.datetime.fromisoformat(stamp)).days
            check(age <= 5,
                  f"the last scan is {age} days old ({stamp[:10]}). Five days "
                  f"covers any weekend or holiday, so this means the daily "
                  f"scan has stopped and the page is showing stale prices")

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

    # 7. The PRIVATE documents, which CI can never see because they live
    #    outside the repo. Skipped silently where absent so this still
    #    passes in the daily scan.
    private = ROOT.parent / "vantage-private"
    todo = private / "TODO.md"
    if todo.exists():
        text = todo.read_text()
        done = re.findall(r"^## (\d+ · .+?) — (?:DONE|MOSTLY DONE)", text, re.M)
        # A queue, not a record: finished items belong in the spec and
        # should leave. Two or more sitting here means it has started
        # becoming an archive.
        check(len(done) < 2,
              f"TODO.md still lists {len(done)} completed items "
              f"({', '.join(d.split(' · ')[0] for d in done)}) — settled work "
              f"belongs in FUNNEL_SPEC.md, and the list is a queue")

    log = private / "BUILD_LOG.md"
    if log.exists():
        tail = log.read_text()[-4000:]
        # Its "Next" section pointed at Stage 2 for weeks after Stage 3
        # shipped. If it names a stage, that stage should not be built.
        for m in re.finditer(r"##\s*Next(.*)$", tail, re.S):
            nxt = m.group(1)
            for stage, module in (("Stage 2", "funnel/stage2.py"),
                                  ("Stage 3", "funnel/stage3.py")):
                check(not (stage in nxt and (ROOT / module).exists()),
                      f"BUILD_LOG's 'Next' still points at {stage}, but "
                      f"{module} exists")

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
