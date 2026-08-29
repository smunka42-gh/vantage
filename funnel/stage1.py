"""Stage 1 quality gate.

Reads audited figures straight from SEC EDGAR and applies the six gates
defined in docs/FUNNEL_SPEC.md. Every gate reports the number that caused
its result, so any verdict can be traced back to a filed figure.

Pure library — importing it does nothing. Run
`tests/test_golden_set.py` for the 17-company regression test, or
`scripts/run_stage1.py` for the whole index.
"""
import os
import requests, statistics as st

# The SEC REQUIRES callers to identify themselves with a contact address
# in the User-Agent, and silently returns non-JSON to requests without
# one. Read it from the environment rather than hard-coding it, so no
# personal contact detail is ever committed to this public repository.
#
#   export SEC_USER_AGENT="vantage-screener you@example.com"
#
# Failing loudly here is deliberate: the alternative is an opaque JSON
# decode error hundreds of lines later.
# Checked LAZILY, on first request — never at import time. Importing this
# module must not be able to kill the host process: Streamlit runs with
# runOnSave, which inspects .py files across the repo, so a module-level
# raise here took the deployed site down with an opaque ImportError.
class _SECSession(requests.Session):
    # An explicit flag, not a check on the header: requests.Session ships
    # a default User-Agent ("python-requests/x.y"), so testing whether one
    # is set always passes and the SEC silently rejects the call with
    # non-JSON hundreds of lines later.
    _ua_applied = False

    def request(self, method, url, *a, **kw):
        if not self._ua_applied:
            ua = os.environ.get("SEC_USER_AGENT")
            if not ua:
                raise RuntimeError(
                    "SEC_USER_AGENT is not set. The SEC requires a contact "
                    'address:  export SEC_USER_AGENT="vantage you@example.com"'
                )
            self.headers["User-Agent"] = ua
            self._ua_applied = True
        return super().request(method, url, *a, **kw)


S = _SECSession()

# Fallback chains: companies file the same economic fact under different
# concept names, so ask for any of them and take whichever exists.
CHAINS = {
    # "Operating income" is the concept we want, but banks, insurers,
    # conglomerates and much of pharma never present an operating-income
    # SUBTOTAL on their income statement, so they never tag it — a bank's
    # income statement has no meaningful "revenue minus operating costs"
    # line, because interest IS the business. They report pre-tax income
    # instead. Falling back to it is imperfect (it includes interest and
    # other non-operating items) but it is a far better answer than not
    # assessing JPMorgan, Berkshire, Lilly or J&J at all.
    "op_income": ["OperatingIncomeLoss",
                  "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                  "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
                  "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomesticAndForeign"],
    "net_income": ["NetIncomeLoss", "ProfitLoss",
                   "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets",
              "PaymentsForCapitalImprovements"],
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet"],
    # Interest expense is the better solvency test but is thinly tagged
    # (27% single-tag, 54% chained), so it is PRIMARY where present and
    # equity/assets is the fallback. See gate 4.
    "interest": ["InterestExpense", "InterestExpenseDebt",
                 "InterestExpenseNonoperating", "InterestAndDebtExpense"],
}
INSTANT = {  # balance-sheet items: a point in time, not a period
    "assets": ["Assets"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}


def _pick(facts, tags, instant, min_recent_year=2023):
    """Latest annual value per fiscal year, for the FRESHEST qualifying tag.

    Recency matters as much as length. Mastercard still carries a
    `NetIncomeLoss` series, but it stops in 2013 — modern years are filed
    under a different tag. Accepting the first chain entry with enough
    years would silently score the company on decade-old figures, so a
    series only qualifies if it also reaches the present.

    Among the entries that qualify, take the one reaching the LATEST year
    rather than the first one encountered. Returning on first match meant
    a chain with two live tags settled for whichever happened to be listed
    first: Ford's net income stopped at FY2024 while its operating income,
    revenue and assets all reached FY2025, so Gate 1 judged a different
    five-year window than Gates 2 to 5 for the same company. Chains are
    ordered by PREFERENCE, not by freshness, and the two are unrelated.
    """
    best = {}
    freshest, freshest_year = None, -1
    for tag in tags:
        node = facts.get("us-gaap", {}).get(tag)
        if not node:
            continue
        units = node["units"].get("USD")
        if not units:
            continue
        by_year = {}
        for u in units:
            if u.get("form") != "10-K":
                continue
            if not instant and u.get("fp") != "FY":
                continue
            # Entries carrying a `frame` key are deliberately NOT skipped.
            # EDGAR marks one entry per calendar period as canonical by
            # attaching a frame label, and for the MOST RECENT fiscal year
            # that is frequently the ONLY entry present — Intuitive
            # Surgical's FY2025 10-K appears exactly once, as frame=CY2025.
            # An earlier version skipped framed entries to deduplicate,
            # which discarded the newest year for 99% of the index: the
            # gates scored 2020-2024 while 2021-2025 sat in the data.
            # Deduplication is handled two lines below by keeping the
            # newest-filed entry per year, so a frame filter is both
            # redundant and destructive. See TENETS.md — reading more of
            # what is filed is the opposite of reconstruction.
            yr = u["end"][:4]
            # a year can be restated in a later filing; keep the newest
            if yr not in by_year or u["filed"] > by_year[yr]["filed"]:
                by_year[yr] = u
        if len(by_year) >= 4:
            series = {y: by_year[y]["val"] for y in by_year}
            newest = max(int(y) for y in series)
            if newest >= min_recent_year:
                # Long enough AND current. Keep looking: a later tag in
                # the chain may reach a later year still.
                if newest > freshest_year:
                    freshest, freshest_year = series, newest
            else:
                best = best or series  # stale; keep only as a last resort
    return freshest if freshest is not None else best


# Some filers split a figure across tags and never report the total.
# J&J, for instance, tags pre-tax income as Domestic and Foreign with 13
# years each, but the combined tag has only 4 — so the parts must be added.
SUM_PARTS = {
    "op_income": [["IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
                   "IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign"]],
}


def _facts(cik):
    return S.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                 timeout=90).json()["facts"]


# Reorganised filers whose history sits under a predecessor CIK. EDGAR's
# ticker map returns the NEW entity, and its submissions record carries an
# empty formerNames list, so nothing links the two automatically. These are
# rare enough to name explicitly, and doing so is more honest than a fuzzy
# name search that could silently attach the wrong company's accounts.
PREDECESSOR_CIK = {
    "XOM": "0000034088",   # ExxonMobil Holdings Corp -> Exxon Mobil Corporation
}


def _resolve_cik(ticker, cik, facts):
    """Follow a reorganisation back to the predecessor that holds the history.

    EDGAR's ticker map returns the CURRENT filer. When a company
    reorganises, that entity is brand new: XOM maps to "ExxonMobil
    Holdings Corp" (94 tags, 0 annual years) while the real 19-year
    history sits under the predecessor CIK (438 tags). Without this, any
    restructured company silently loses its entire history.
    """
    ni = facts.get("us-gaap", {}).get("NetIncomeLoss")
    yrs = 0
    if ni:
        yrs = len({x["end"][:4] for x in ni["units"].get("USD", [])
                   if x.get("form") == "10-K" and x.get("fp") == "FY"})
    if yrs >= 4:
        return cik, facts, None
    alt = PREDECESSOR_CIK.get(ticker)
    if alt:
        return alt, _facts(alt), f"history read from predecessor CIK {alt}"
    return cik, facts, None


def filing_asof(facts):
    """Which filing the gates are actually reading, and when it landed.

    Stage 1 judges annual 10-Ks, so its newest figure can be anywhere from
    two to twelve months old depending on a company's fiscal calendar.
    Reporting that is not decoration: a PASS based on a year ending in
    December is blind to everything that happened since, and a reader
    going off to read the news needs to know where our knowledge stops
    and theirs starts.
    """
    best = None
    for tag in CHAINS["net_income"] + CHAINS["op_income"]:
        node = facts.get("us-gaap", {}).get(tag)
        if not node:
            continue
        for u in node["units"].get("USD", []):
            if u.get("form") != "10-K" or u.get("fp") != "FY":
                continue
            if best is None or u["end"] > best["end"]:
                best = u
        if best:
            break
    if not best:
        return None
    return {"fiscal_year": best.get("fy"), "period_end": best["end"],
            "filed": best["filed"]}


def load(ticker, cik):
    f = _facts(cik)
    cik, f, note = _resolve_cik(ticker, cik, f)
    d = {k: _pick(f, tags, False) for k, tags in CHAINS.items()}
    d.update({k: _pick(f, tags, True) for k, tags in INSTANT.items()})
    # Fill gaps by summing component tags where a filer reports only parts.
    for key, part_sets in SUM_PARTS.items():
        if len(d.get(key, {})) >= 4:
            continue
        for parts in part_sets:
            series = [_pick(f, [p], False) for p in parts]
            if all(len(s) >= 4 for s in series):
                yrs = set.intersection(*[set(s) for s in series])
                if len(yrs) >= 4:
                    d[key] = {y: sum(s[y] for s in series) for y in yrs}
                    break
    d["_note"] = note
    d["_asof"] = filing_asof(f)
    return d


def last5(series, years):
    return [series[y] for y in years if y in series]


# How close to a threshold still counts as "borderline", as a fraction of
# the bar itself. Proportional rather than absolute so it means the same
# thing whether the bar is 8% (returns) or 4x (interest coverage).
BORDERLINE = 0.15

# How many gates must be EVALUABLE before a verdict means anything.
# Exists because an early version let a company pass by failing nothing:
# Exxon was admitted having been measured on ZERO gates, because none of
# its data was reachable. That silently admits exactly the companies you
# know least about.
CANNOT_ASSESS_FLOOR = 4


def grade(value, bar, higher_is_better=True):
    """Classify a measurement against its threshold.

    Returns one of: pass · near-pass · near-fail · fail.

    A plain pass/fail hides how a company got there. A company clearing a
    bar by a hair is materially different from one clearing it by triple,
    and one missing by a hair is different from one missing by half — but
    boolean logic reports those pairs identically. The margin is the
    information, so it is kept rather than discarded.
    """
    if value is None or bar in (None, 0):
        return None, None
    slack = (value - bar) / abs(bar)
    if not higher_is_better:
        slack = -slack
    if slack >= BORDERLINE:
        return "pass", slack
    if slack >= 0:
        return "near-pass", slack
    if slack > -BORDERLINE:
        return "near-fail", slack
    return "fail", slack


def run(ticker, d, is_financial=False, is_utility=False,
        is_capital_intensive=False, shock_years=()):
    """Apply the six gates. Returns list of (gate, passed|None, detail)."""
    # Year spine: built from whichever profit series exists, so a thin
    # tag in ONE concept cannot blank out gates that don't depend on it.
    # (Mastercard's stale NetIncomeLoss previously emptied this list and
    # took two unrelated gates down with it.)
    profit_years = set(d["op_income"]) | set(d["net_income"])
    yrs = sorted(profit_years & set(d["assets"]))[-5:]
    out = []

    # --- Test 1: sustained profitability -----------------------------
    # Financials get the same one-bad-year allowance on the profit series
    # that everyone gets on net income. Insurers must mark their
    # investment portfolio to market, so Berkshire's 2022 pre-tax figure
    # was -$30.5B purely from unrealised equity revaluation while its
    # operating businesses were fine. Penalising that is measuring the
    # stock market, not the company.
    # Years the WHOLE sector lost money are excluded before counting. A
    # year in which most of an industry's largest companies posted an
    # operating loss is an exogenous shock, not evidence about any one
    # company: in 2020, 5 of the 7 largest energy names went negative,
    # against 0% in every other year. Excusing that year is mechanical
    # (it identifies an industry-wide event) rather than a lowered bar —
    # a company that also lost money OUTSIDE the shock year still fails.
    judged = [y for y in yrs if y not in shock_years]
    oi = last5(d["op_income"], judged)
    ni = last5(d["net_income"], judged)
    # Banks, insurers and asset managers frequently have NO usable
    # operating-income series at all — Allstate tags none, and Aflac's
    # stops in 2021 — because the concept is not meaningful for them.
    # Requiring it made 8 established financials "cannot assess" purely
    # on a missing tag. For those, net income IS the profit measure, and
    # it has excellent coverage; gate 2 already judges them on ROE, which
    # is built from the same figure.
    if is_financial and len(oi) < 4 and len(ni) >= 4:
        oi = ni
    if len(oi) >= 4 and len(ni) >= 4:
        neg_allowed = 1 if is_financial else 0
        oi_neg = sum(1 for x in oi if x <= 0)
        ok = oi_neg <= neg_allowed and sum(1 for x in ni if x > 0) >= len(ni) - 1
        out.append(("1 Sustained profit", "pass" if ok else "fail",
                    f"profit negative {oi_neg}/{len(oi)}y (allowed {neg_allowed})"
                    f"{' [shock yrs excluded: '+','.join(sorted(shock_years))+']' if shock_years else ''} · "
                    f"net income positive {sum(1 for x in ni if x>0)}/{len(ni)}"))
    else:
        out.append(("1 Sustained profit", None, "insufficient history"))

    # --- Test 2: returns on capital (level OR improving) -------------
    # SECTOR RULE, and the only one the evidence forced. Banks and
    # insurers hold enormous balance sheets against thin spreads, so
    # return on ASSETS is structurally ~1-1.5% for a perfectly healthy
    # bank: JPMorgan runs 1.0-1.5% ROA while earning 12.9-17.0% ROE. An
    # 8% ROA bar is not strict for a bank, it is impossible. Financials
    # are therefore judged on return on EQUITY, the yardstick the
    # industry itself uses.
    if is_financial or is_utility or is_capital_intensive:
        vals = [d["net_income"][y] / d["equity"][y] for y in yrs
                if y in d["net_income"] and d["equity"].get(y)]
        # Utilities: 8% anchors to the ALLOWED ROE regulators grant, which
        # runs 9-10.5% in the US. A utility earning well under its own
        # allowance (Duke at 5.8%) is genuinely underperforming, not merely
        # capital-intensive — so the bar still discriminates.
        if is_utility:
            bar, near, label = 0.08, 0.07, "return on equity"
        else:
            # Financials and capital-intensive competitive businesses
            # (telecom, cable, media) share a 10% bar. Unlike a regulated
            # utility they carry competitive risk and have no allowed
            # return to anchor to, so they should out-earn one.
            bar, near, label = 0.10, 0.09, "return on equity"
    else:
        vals = [d["op_income"][y] * 0.79 / d["assets"][y] for y in yrs
                if y in d["op_income"] and d["assets"].get(y)]
        bar, near, label = 0.08, 0.07, "return on assets"
    if len(vals) >= 4:
        med, latest = st.median(vals), vals[-1]
        improving = latest >= near and latest > med
        g, slack = grade(med, bar)
        if improving and g in ("near-fail", "fail"):
            g, slack = "pass", 0.0          # improvement clause overrides level
            why = "improving"
        else:
            why = "level"
        out.append(("2 Return on capital", g,
                    f"{label} median {med*100:.1f}% vs {bar*100:.0f}% bar · "
                    f"latest {latest*100:.1f}% ({why})"))
    else:
        out.append(("2 Return on capital", None, "insufficient history"))

    # --- Test 3: cumulative free cash flow ---------------------------
    # Utilities are judged on OPERATING cash flow instead. Free cash flow
    # is negative by design for a regulated utility: it continuously funds
    # grid capex with debt against regulator-guaranteed returns, so 26 of
    # 31 showed negative cumulative 5y FCF. What matters is whether the
    # business throws off cash before that investment, every year.
    if is_utility and d["ocf"]:
        cy = sorted(d["ocf"])[-5:]
        vals = [d["ocf"][y] for y in cy]
        out.append(("3 Cumulative 5y FCF", "pass" if min(vals) > 0 else "fail",
                    f"operating cash flow positive {sum(1 for v in vals if v>0)}/{len(vals)}y "
                    f"(utility track: capex excluded)"))
    elif d["ocf"] and d["capex"]:
        cy = sorted(set(d["ocf"]) & set(d["capex"]))[-5:]
        fcf = sum(d["ocf"][y] - d["capex"][y] for y in cy)
        out.append(("3 Cumulative 5y FCF", "pass" if fcf > 0 else "fail",
                    f"${fcf/1e9:+.1f}B over {len(cy)}y"))
    elif d["ocf"]:
        cy = sorted(d["ocf"])[-5:]
        tot = sum(d["ocf"][y] for y in cy)
        out.append(("3 Cumulative 5y FCF", "pass" if tot > 0 else "fail",
                    f"${tot/1e9:+.1f}B operating cash (no capex tag)"))
    else:
        out.append(("3 Cumulative 5y FCF", None, "no cash-flow tag"))

    # --- Test 4: can the debt be serviced? ---------------------------
    # Coverage asks the real question ("can it pay the interest?") and is
    # tried FIRST. Equity/assets is only the fallback, because on its own
    # it fails Apple (15.6%) and GE (16.2%) for buybacks and restructuring
    # rather than for any quality problem — leverage is not a defect if
    # the earnings comfortably service it.
    y = yrs[-1] if yrs else None
    ie = d["interest"].get(y) if y else None
    if y and ie and d["op_income"].get(y):
        cov = d["op_income"][y] / abs(ie)
        # Regulated utilities carry more debt against far more predictable
        # cash flows, so 2.5x there is the equivalent of 4x elsewhere.
        cov_bar = 2.5 if is_utility else 4.0
        g, _ = grade(cov, cov_bar)
        out.append(("4 Debt serviceable", g,
                    f"interest coverage {cov:.1f}x vs {cov_bar}x bar"))
    elif y and d["equity"].get(y) and d["assets"].get(y):
        ratio = d["equity"][y] / d["assets"][y]
        # Deliberately loose: this is a crude proxy used ONLY when the
        # real test is unavailable, so it should catch the obviously
        # over-levered without second-guessing companies it cannot
        # properly measure. At 15% Apple cleared by 0.6 points, which is
        # luck rather than judgement.
        bar = 0.08 if is_financial else 0.10
        g, _ = grade(ratio, bar)
        out.append(("4 Debt serviceable", g,
                    f"equity/assets {ratio*100:.1f}% vs {bar*100:.0f}% bar (no interest tag)"))
    else:
        out.append(("4 Debt serviceable", None, "no interest or equity tag"))

    # --- Test 5: operating margin not deteriorating ------------------
    # RELATIVE, not absolute. An absolute band cannot serve both ends of
    # the margin range: 6 percentage points is a rounding error to a 40%-
    # margin semiconductor firm and a catastrophe to a 5%-margin retailer.
    # Dollar General's margin roughly HALVED (8.2% -> 4.2%) and still
    # passed a 6pp band. Requiring the latest to hold 70% of the 3-year
    # average fails DG at 51% while passing TXN at 74%.
    om = [d["op_income"][y] / d["revenue"][y] for y in yrs
          if y in d["op_income"] and d["revenue"].get(y)]
    if len(om) >= 4:
        ref = st.mean(om[-4:-1])
        ratio = (om[-1] / ref) if ref > 0 else 0.0
        g, _ = grade(ratio, 0.70)
        out.append(("5 Op margin durable", g,
                    f"latest {om[-1]*100:.1f}% is {ratio*100:.0f}% of 3y avg "
                    f"{ref*100:.1f}% (70% bar)"))
    else:
        out.append(("5 Op margin durable", None, "no revenue tag match"))

    # Gate 6 (liquidity, >= $25M median daily dollar volume) was REMOVED.
    # It rejected zero of 500 companies and was kept only "so the universe
    # can widen later" — a check earning its place from a future that has
    # not arrived. TENETS.md 4: a check must change outcomes or be cut;
    # TENETS.md 2 rules out keeping it as a displayed fact instead.
    # Rebuild it when the universe actually widens beyond the S&P 500.
    return out


# EXCEPTIONS were removed. The mechanism let a named near-fail be
# relabelled EXCEPTION instead of BORDERLINE — and nothing else, because
# both tiers were already ELIGIBLE and treated identically everywhere
# downstream. It changed no outcome, which TENETS.md 4 does not allow.
#
# It also never covered the case that actually creates pressure to move a
# bar: a company you believe in that is REJECTED. An exception could only
# rescue a NEAR-fail, and a single near-fail already yields BORDERLINE,
# which already passes through. There is now no escape hatch at all — the
# company clears the bar or it does not.


def decide(gates, ticker=None):
    """Resolve the five graded gates into a watchlist tier.

      PASS           every gate cleared (a near-pass IS a pass)
      BORDERLINE     exactly one near-fail, nothing worse
      REJECTED       any outright fail, or two or more near-fails
      CANNOT ASSESS  fewer than 4 of the 5 gates evaluable

    PASS and BORDERLINE are both ELIGIBLE for Stage 2 — the tier travels
    with the company rather than being collapsed away, so the page can
    show whether a name is on the list cleanly or barely. That is what
    keeps the thresholds fixed: a near-miss is recorded as a near-miss
    instead of prompting someone to move the bar.

    `ticker` is retained for call-site compatibility and diagnostics; the
    verdict no longer depends on which company it is, which is the point.
    """
    # Every gate is substantive. This used to slice off a trailing
    # always-passing liquidity gate; that gate is gone (TENETS.md 4), so
    # the count below must never be hard-coded again — it is derived.
    grades = [(n, g) for n, g, _ in gates if g is not None]
    if len(grades) < CANNOT_ASSESS_FLOOR:
        return "CANNOT ASSESS"
    if any(g == "fail" for _, g in grades):
        return "REJECTED"
    near = [n for n, g in grades if g == "near-fail"]
    if not near:
        return "PASS"
    if len(near) > 1:
        return "REJECTED"
    return "BORDERLINE"


ELIGIBLE = {"PASS", "BORDERLINE"}


def eligible(verdict):
    """Does this company go through to Stages 2 and 3?"""
    return verdict in ELIGIBLE


def at_risk(gates):
    """Gates a watchlist member is closest to failing — Stage 3 input."""
    return [n for n, g, _ in gates if g == "near-pass"]
