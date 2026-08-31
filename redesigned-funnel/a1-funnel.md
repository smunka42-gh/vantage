# Stage A1 — Eligibility

**Status:** locked, 31 August 2026.
**Universe produced:** 3,863 companies.

A1 answers one question: **is this the kind of company the screen covers?**
It makes no judgement about business quality. A company failing A1 is out of
scope and does not appear at all. Companies disqualified *for cause* are
handled in Stage A2 and do appear, with the reason shown.

Every rule runs on a field published by the SEC. No value is ever supplied,
inferred, or hand-curated.

---

## The funnel

| # | Rule | Left | Removed |
|---|---|---|---|
| — | Every company in the SEC ticker file | 8,004 | — |
| 1 | Listed on NYSE or Nasdaq | 6,054 | 1,762 OTC · 169 no exchange assigned · 19 CBOE-only |
| 2 | Operating companies only | 5,660 | 290 SPACs · 92 commodity and crypto trusts · 12 other vehicles |
| 3 | Excluding REITs | 5,480 | 180 REITs |
| 4 | Filed a 10-K or 10-KT covering a period ending 2025 or later | **3,863** | 997 file 20-F · 480 no annual report · 113 file 40-F · 27 stale |

---

## Rule 1 — NYSE or Nasdaq only

OTC securities are excluded: no listing standards, no governance requirements,
no minimum size, thin liquidity, and difficulty exiting a position. For a
buy-and-hold screen, exit difficulty matters more than it would for trading.

CBOE is excluded at a known cost — one S&P 500 constituent lists only there.
Of the 23 CBOE listings, 17 are crypto or commodity trusts and 4 are
dual-listed on a major exchange.

## Rule 2 — Operating companies only

Funds, ETFs, trusts, SPACs and blank-check shells are removed by SEC industry
classification code.

This rule was added after inspection rather than reasoning. Bitcoin, Ethereum
and gold trusts file annual reports, carry tickers, and would have passed every
other rule before producing meaningless answers on revenue growth and operating
margin.

**Known imperfection:** the classification codes are the SEC's own and are
occasionally wrong. At least one genuine operating company is coded as a
commodity dealer, and one index constituent is coded as an investment trust.
The published field is followed rather than overridden.

## Rule 3 — REITs excluded

Excluded for **measurability, not quality**, and to be served separately by a
view using metrics appropriate to them (funds from operations, occupancy, lease
terms, net asset value).

Four of the screen's ten question groups misfire on REITs:

- **Compounding is unanswerable.** A REIT must distribute at least 90% of
  taxable income, so "what does it earn on what it retains" has no meaning.
- **Dilution fires on every healthy REIT.** Unable to retain earnings, a REIT
  funds growth by issuing shares. Constant dilution is the model working.
- **Returns are wrong in both directions.** Buildings depreciate on the books
  while often appreciating in reality, understating profit; and they sit at
  historical cost, falsifying the asset base.
- **Leverage is misread.** Mortgages are the business, not a warning sign.

Equity and mortgage REITs are excluded together.

## Rule 4 — A recent annual report

**Filed a 10-K or 10-KT covering a period ending 2025 or later.**

This single rule replaces both a domestic-filer test and a recency test.

**Why not incorporation.** An earlier version required US incorporation. The
SEC does not populate that field reliably — 649 of 6,054 NYSE and Nasdaq
companies have it blank, including several of the largest US companies by
market value. Three separate SEC sources were checked and none carry it.
Treating a blank field as "not US" silently removed 53 S&P 500 constituents.

Filing a 10-K is the SEC's own operative definition of a US domestic filer:
foreign private issuers file 20-F, Canadian issuers file 40-F. The field is
fully populated and loses nothing the incorporation rule kept.

**Accepted consequence:** companies incorporated abroad but reporting as US
domestic filers — the tax-inversion group — are included. No published field
separates them, and a hand-written exclusion list would violate the rule
against introducing our own data into a filter.

**10-KT is included.** It is the transition report filed when a company changes
its fiscal year end — a full annual report, not a notice. Its period is
deliberately not twelve months. Excluding it wrongly marks fiscal-year-changers
as delinquent.

**10-K/A is excluded.** An amendment to an old report is not evidence a company
is current, and counting it patches false continuity into a broken filing
history. Amendments run at roughly 405 per quarter.

**Anchored on the period covered, never the filing date.** 19% of companies
have fiscal years ending outside December. A filing-date rule mis-sorts all of
them, and the bias rotates depending on when the screen is run.

**Express as a rolling window in production** — a period ending within roughly
the last 15 months. A fixed calendar anchor goes stale and begins admitting
companies that have stopped filing.

---

## Validation

Checked against six reference sets whose membership encodes an external
judgement about quality or durability.

| Reference set | Retained |
|---|---|
| S&P 500 | 470 / 500 (94%) |
| S&P MidCap 400 | 370 / 400 (92%) |
| S&P SmallCap 600 | 556 / 600 (93%) |
| S&P 500 Dividend Aristocrats | 65 / 69 (94%) |
| Berkshire Hathaway 13F holdings | 23 / 23 (100%) |

Every excluded member is attributed to a named rule: 96 REITs, one CBOE-only
listing, one SEC misclassification, two banks reporting to a federal banking
regulator rather than the SEC, and one corporate-succession defect.

Reference sets are used to **validate**, never to filter. Filtering on index
membership would outsource the judgement to an index committee and inherit its
lag, since constituents are typically added after a company has already
succeeded.

---

## Rules considered and rejected

**Three consecutive annual reports for fiscal years 2023–2026.** Rejected. It
admits zero companies the chosen rule excludes while costing 324, of which 313
have only one or two annual reports in their entire history — recent listings
and spin-offs. It also converts filing history from a filter into a cut.

**A 10-K filed within the last 365 days.** Rejected. It removes 11 healthy
companies, two of them S&P 500 constituents, by margins of two and three days.
Every company lost had a fiscal year ending between March and July. The bias is
systematic and rotates with the date the screen is run.

**A 10-K filed within the last 450 days.** Workable — an empty 118-day gap in
the data separates the last healthy company from the first delinquent one, so
any threshold in that range gives an identical result. Rejected because
anchoring on the reporting period requires no chosen number at all.

---

## Filing history is a filter, not a cut

Companies are bucketed as 10+ years, 5–9 years, and under 5 years of continuous
annual reporting. A young company is *not yet assessable* rather than
low-quality, and cannot reach the top quality tier regardless.

Buckets are derived at read time from stored facts. The window slides every
year, so a stored bucket value would silently rot.

---

## Known defects

**Corporate succession.** When a company reorganises into a holding structure
or is spun off, it receives a new SEC identifier with no filing history, while
its record remains under the old one. Several large constituents are affected.
Form 8-K12B, the notification of succession, is the published fix. Not yet
implemented.

**Banks reporting to a federal banking regulator.** Banks whose securities are
registered with a banking agency file annual reports with that regulator rather
than the SEC, so they never appear on EDGAR. 44 banks are affected, two of them
index constituents. No EDGAR-based pipeline can see them.

**API truncation.** The SEC submissions endpoint returns only a company's most
recent ~1,000 filings. Companies filing high volumes of routine documents push
their older annual reports outside that window. Archive files must always be
fetched; omitting them produced a wrong result in testing, in which several of
the largest US banks appeared to have filed one or two annual reports ever.

---

## Not part of A1

**Size.** A tradability floor belongs in Stage A2, so an excluded company shows
its reason rather than disappearing. Size bands are a ranking-stage filter.

**Disqualifying events.** Restatements, enforcement actions, bankruptcy,
going-concern warnings and governance failures are Stage A2. Placing them in A1
would remove companies silently, discarding the most useful output the screen
produces.

---

## Data sources

- SEC company ticker and exchange file
- SEC EDGAR full-text filing index
- SEC submissions API, including archive files
- SEC Financial Statement Data Sets
- Index membership from public constituent listings; Berkshire Hathaway
  holdings from its quarterly 13F filing

## Credits

Index constituent data derives from S&P Dow Jones Indices via public listings.
Institutional holdings from SEC Form 13F filings. All company financial and
filing data from the US Securities and Exchange Commission's EDGAR system.
No external datasets or third-party methodologies are used at this stage.
