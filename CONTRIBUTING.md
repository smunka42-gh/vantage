# Working on Vantage

## This repo does not inherit from anything

Vantage replaced an earlier screener (`dere`, now archived). **Nothing
from that project may be copied into this one** — not the UI, the theme,
the page layout, the scan pipeline, or any module. It is not a reference
and it is not a source of parts. Vantage starts clean.

The one exception, already applied: the Stage 1 funnel code, which was
written for Vantage from the start.

The reason is not tidiness. The old app's page is being replaced
wholesale — its filter panel, composite score and heatmap are all
deliberately gone — and most of its CSS exists to position widgets that
no longer have a place here. Carrying it over would mean fighting it.

## The spec is the source of truth

`docs/FUNNEL_SPEC.md` defines every gate, threshold, and the measurement
behind it. Change the spec and the code together, or they drift.

## Build order

1. Stage 1 — quality gate ✅
2. Stage 2 — dislocation score
3. Stage 3 — cheap-or-broken corroboration
4. UI specification and mockups
5. The interface itself

**No interface work until all three stages produce real numbers.** The
predecessor's layout was designed around a guessed watchlist size and the
guess was wrong by 2x, which invalidated most of the design.

## Two rules learned the hard way

**Never run side effects at import time.** A module-level `SystemExit`
guarding a missing environment variable once took the deployed
predecessor down with an opaque error. Validate lazily, at the point of
use.

**Never hard-code a contact address.** This repo is public. The SEC
requires a contact address on every request; it comes from
`SEC_USER_AGENT` and nowhere else.
