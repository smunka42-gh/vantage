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

    # ---- COVERAGE CHECKS ------------------------------------------
    #
    # Everything above asks "is this entry correct?". Every miss this
    # project has had was the other question: "does the list cover
    # everything it should?" — and nothing asked it.
    #
    #   GATE_LABEL held 5 entries for 6 gates, so gate 6 rendered raw on
    #   ~470 companies. plain() held the shapes I had seen, so 628 details
    #   reached the reader as backend strings. The pre-commit risk map
    #   held the files that existed when it was written, so three files
    #   added later warned nobody.
    #
    # Each fails when something is ADDED, which is when these gaps open.

    # 5c. Every gate stage1.py emits must have a label and plain wording.
    detail_js = (ROOT / "site/detail.js").read_text()
    gate_names = sorted(set(re.findall(r'out\.append\(\("(\d+ [^"]+)"',
                                      (ROOT / "funnel/stage1.py").read_text())))
    for full in gate_names:
        bare = re.sub(r"^\d+\s+", "", full)
        labelled = (f'"{bare}"' in detail_js)
        worded = (f'gate==="{bare}"' in detail_js
                  or f'raw==="{bare}"' in detail_js)
        check(labelled, f"gate '{bare}' has no entry in detail.js's label tables "
                        f"— it will render with its internal name")
        check(worded, f"gate '{bare}' has no wording case in detail.js's plain() "
                      f"— its detail will render as the backend string")

    # 5d. Every source file must be covered by the pre-commit risk map,
    #     which tells a human which docs a change puts at risk.
    hook = ROOT / ".githooks/pre-commit"
    if hook.exists():
        pats = re.findall(r"risk '(\^[^']+)'", hook.read_text())
        for path in sorted(list(ROOT.glob("funnel/*.py"))
                           + list(ROOT.glob("site/*"))
                           + list(ROOT.glob("scripts/*.py"))):
            rel = str(path.relative_to(ROOT))
            if path.name == "__init__.py":
                continue
            check(any(re.match(p, rel) for p in pats),
                  f"{rel} matches no pattern in .githooks/pre-commit — a change "
                  f"there will flag no documentation for re-reading")

    # 5f. Numbered lists must not repeat or skip a number.
    #     §6 carried TWO principles numbered 9 for a day, because a tenth
    #     was added without reading what was already there. A duplicate
    #     number also silently breaks every "see principle N" reference.
    for heading in ("### 6.", "## 6."):
        pass
    body = spec.split("## 6. Interface principles", 1)[-1].split("### 6.1", 1)[0]
    nums = [int(n) for n in re.findall(r"^(\d+)\. \*\*", body, re.M)]
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    check(not dupes, f"§6 has more than one principle numbered {dupes} — "
                     f"a duplicate silently breaks every reference to it")
    check(nums == sorted(nums),
          f"§6's principles are numbered out of order: {nums}")

    # 5g. The tenets are counted in three places and were consistent in two.
    tenets = ROOT / "TENETS.md"
    if tenets.exists():
        t = tenets.read_text()
        n_head = len(re.findall(r"^## \d+ · ", t, re.M))
        words = {"Four":4, "Five":5, "Six":6, "Seven":7, "Eight":8}
        m = re.search(r"^(\w+) rules that govern", t, re.M)
        if m and m.group(1) in words:
            check(words[m.group(1)] == n_head,
                  f"TENETS.md says '{m.group(1)} rules' but contains {n_head}")
        n_spec = len(re.findall(r"^\d+\. \*\*[^*]+\.\*\* ", spec[:spec.index("## What this version is")], re.M))
        check(n_spec == n_head,
              f"the spec summarises {n_spec} tenets but TENETS.md has {n_head}")

    # 5e. Sentences the project has already outgrown.
    #
    # Every other check compares a NUMBER. These are claims in prose, and
    # prose that was true once reads exactly like prose that still is —
    # which is how "There is no Stage 3" survived thirteen versions, in
    # two separate places.
    #
    # This is deliberately a LIST, not a clever general check. It cannot
    # catch a sentence nobody has written yet, and pretending otherwise
    # would be worse than the honest version. APPEND TO IT whenever a
    # stale claim is found: the cost is one line, and the same sentence
    # never gets to go stale twice.
    #
    # Each entry: (pattern, is-wrong-when, what to say instead)
    claims = [
        (r"[Tt]here is no Stage 3",
         (ROOT / "funnel/stage3.py").exists(),
         "Stage 3 shipped in v2.8 — see §5.2"),
        (r"[Bb]oth stages are (built|running)",
         (ROOT / "funnel/stage3.py").exists(),
         "there are three stages, not two"),
        (r"complete at two stages",
         (ROOT / "funnel/stage3.py").exists(),
         "the funnel runs to three stages"),
        (r"[Nn]o Stage 3 (is|and none is) planned",
         (ROOT / "funnel/stage3.py").exists(),
         "Stage 3 was reopened in v2.8"),
        (r"UI (is )?not started|[Nn]o UI yet|interface is not built",
         PAGE.exists(),
         "the interface is built and published"),
        (r"[Bb]uild the interface last",
         PAGE.exists(),
         "the interface is built — this reads as a plan, not a record"),
        (r"a single (static )?page(?! at)",
         SIMPLE.exists(),
         "there are two pages: / and /simple/"),
    ]
    # Changelog ROWS legitimately quote what a document used to say, so
    # they are dropped — but only the rows. Check 4 drops the whole region
    # between the table and section 1, which is precisely where the second
    # instance of "There is no Stage 3" had been sitting undisturbed.
    for doc, name in ((spec, "the spec"), (readme, "the README")):
        prose = "\n".join(l for l in doc.splitlines() if not l.startswith("|"))
        for pattern, wrong_now, instead in claims:
            if not wrong_now:
                continue
            hit = re.search(pattern, prose)
            check(not hit,
                  f"{name} still says \"{hit.group(0)}\" — {instead}"
                  if hit else "")
    # Changelog ROWS legitimately quote what a document used to say, so
    # they are dropped -- but only the rows. Check 4 drops the whole
    # region between the table and section 1, which is precisely where
    # the second instance of this had been sitting undisturbed.

    # 5h. The memory index must actually index the memory.
    #
    # MEMORY.md is loaded every session; the individual files are pulled in
    # only when judged relevant. So a file nobody links is a file that may
    # never be read, and a link to a deleted file is a promise the index
    # cannot keep. Both are silent failures — nothing errors, the memory is
    # simply absent when it matters.
    mem_dir = (pathlib.Path.home() /
               ".claude/projects/<derived-from-repo-location>/memory")
    index = mem_dir / "MEMORY.md"
    if index.exists():
        linked = set(re.findall(r"\]\(([^)]+\.md)\)", index.read_text()))
        present = {f.name for f in mem_dir.glob("*.md")} - {"MEMORY.md"}
        for orphan in sorted(present - linked):
            check(False, f"memory/{orphan} exists but MEMORY.md never links it — "
                         f"it may never be recalled")
        for dangling in sorted(linked - present):
            check(False, f"MEMORY.md links memory/{dangling}, which does not exist")

        # cross-references between memories must resolve too
        stems = {f.stem for f in mem_dir.glob("*.md")}
        for f in sorted(mem_dir.glob("*.md")):
            for link in re.findall(r"\[\[([^\]]+)\]\]", f.read_text()):
                ok = link in stems or link.replace("-", "_") in stems
                check(ok, f"memory/{f.name} references [[{link}]], which is not a "
                          f"memory file")

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
