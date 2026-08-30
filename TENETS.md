# Project tenets

Six rules that govern every stage of this project. Each was earned by
something that actually went wrong here, and each is written to be
testable rather than aspirational — a proposal either violates one or it
doesn't.

They outrank convenience, and they outrank my own earlier recommendations
in this repository's history. Where a tenet and a design disagree, the
design changes.

[`docs/FUNNEL_SPEC.md`](docs/FUNNEL_SPEC.md) carries a one-line summary of
each and links here. This file is the full text and the only copy that
should be edited.

---

## 1 · No reconstruction of time periods

**Use figures exactly as filed. Never derive a period the filer did not
report.**

**Forbids:** deriving Q4 as `FY − YTD`; building trailing-twelve-month
figures by adding or subtracting periods; stitching quarters into a
window nobody published.

**Permits:** ratios of as-filed figures — `ROA = filed operating income ÷
filed assets` — where both inputs appear verbatim in a single filing. The
distinction is *reconstruction* versus *arithmetic on published numbers*.

**Why.** A reconstructed figure looks exactly like a real one and there is
nothing to check it against. Every attempt at TTM in this project
introduced a silent selection bug within minutes of being written — the
worst of them produced a "trailing twelve months" ending three months
*before* the fiscal year it was meant to replace, which would have made
the data staler while appearing to make it fresher.

Note what this does **not** forbid: reading more of what is filed. The
frame-filter fix recovers a year of data by stopping the code discarding
figures the SEC published. That is the opposite of reconstruction.

---

## 2 · Don't display what isn't used

**Every element on screen falls into one of three categories.**

| Category | Test | Treatment |
|---|---|---|
| **Driver** | Feeds the verdict, or changes what the reader would do | Show |
| **Audit trail** | Lets a reader verify a driver — `8.7% = $12.4B ÷ $142B`, "data as of March 2026" | Show, subordinate to the driver |
| **Decoration** | Neither | **Cut** |

**Why.** A number on screen implies it counts. Showing *"44% below its
52-week high"* beside *"18.7% below its own normal"* invites the reader to
weight it themselves, inconsistently, and to reach for the larger, more
alarming figure. "Keep it around as context" is usually a way of avoiding
a decision about whether something matters.

**What this cut:** the 52-week high as displayed context; Gate 6 as a
"displayed fact"; volume character in Stage 3. All three had been
*demoted* rather than removed, which this tenet does not allow.

---

## 3 · Measure before deciding

**Every threshold comes from a measurement on real data — never from
intuition, and never from a small sample.**

**Why.** Three predictions in this project were confidently wrong, and
measurement caught all three:

| Prediction | Reality |
|---|---|
| 50-day and 200-day averages correlate above 0.8, so weighting both is redundant | **0.53** — substantially independent |
| Short interest needs sector-specific thresholds | Within-sector spread dominates; one bar is fine |
| A trailing-twelve-month figure is always fresher than the annual one | False for any company that has just filed its 10-K |

Separately, Stage 3's volume thresholds were set from an eight-name
sample and, measured against the full index, awarded +1 to 89% of
companies and −1 to none.

---

## 4 · A check must change outcomes, or be cut

**Every gate, signal and component must survive a drop-one test: remove
it, and if nothing changes, it stays removed.**

**Why.** Gate 6 (liquidity) rejects zero of 500 companies. The 52-week
high correlates 0.74 with the 200-day average and its distinctive part
measures whether a stock *spiked* in the past year rather than whether it
is cheap now. Both were carried because they seemed reasonable, not
because they did work.

A check kept for a future that has not arrived — "so the universe can
widen later" — fails this tenet. Build it when the universe widens.

---

## 5 · Thresholds never move to admit a company

**If a company you believe in fails, it stays out. The bar does not
move, and there is no escape hatch.**

**Why.** The returns bar drifted 12% → 8% chasing Costco and Amazon; the
solvency bar went 20% → 15% → 10% chasing Apple and Oracle. Each move
silently changed the answer for five hundred companies in order to
accommodate one, and overfitted the thresholds to whichever names
happened to be in the test set.

The four-way grading — pass / near-pass / near-fail / fail — exists
precisely so that a near-miss is *recorded* as a near-miss rather than
prompting anyone to move a bar. A single near-fail already yields
BORDERLINE, which is eligible, so a company that nearly clears is kept
without anything being overridden.

An exceptions mechanism existed until 29 Aug 2026 and was removed. It
could relabel a named near-fail as EXCEPTION rather than BORDERLINE and
did nothing else — both tiers were already eligible and treated
identically downstream — so it changed no outcome, which tenet 4 does
not allow. It also never covered the case that actually creates pressure
to move a bar: a company you believe in that is REJECTED.

---

## 6 · Every file must earn its place, and keep earning it

**A file stays only if something breaks or is lost when it goes.**
Duplicating another file's content is not a reason to exist, and
scaffolding is deleted when the thing it scaffolded is finished.

**Why.** A repository is read as a whole. Files that no longer pull
weight make a reader distrust the ones that do — and a document nobody
maintains does not sit there neutrally, it goes stale and starts telling
people things that are no longer true.

**What this has cut:** the `?resize=1` column-drag tool, deleted the day
the widths it existed to choose were frozen into the stylesheet. The REIT
note in `detail.js`, which proved unreachable — REITs are excluded from
the page, so no row could ever render it. `CONTRIBUTING.md`, whose three
sections were a rule about an archived private repository the reader
cannot see, plus two restatements of things the spec already says.

**The test this implies.** Deletion is easy; noticing is not. The same
failure that makes a file go stale makes a LIST go stale — see the
coverage checks in `tests/test_docs_current.py`, which assert that every
gate has wording and every source file is covered by the pre-commit risk
map. Both exist because something was added and a list was not updated.

---

## Credits

These tenets are original to this project and were derived from its own
defects and measurements; no external framework or methodology is
reproduced here.
