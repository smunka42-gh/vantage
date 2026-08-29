"""The companies Vantage screens, and how they are classified.

Deliberately self-contained: the constituent list and every sector label
come from one public source, fetched at run time. Nothing is inherited
from an earlier project, and no scan file has to exist first.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Wikipedia asks that automated readers identify themselves and blocks
# some default library agents outright. Unlike the SEC's, this is a
# courtesy rather than a hard requirement, so a project string is enough
# and no contact address is embedded here.
WIKI_USER_AGENT = "vantage/0.1 (stock quality screener; contact via repository)"

# The index lists ~503 tickers for ~500 companies because a few file two
# share classes. Keeping both would double-count one business and skew
# any sector tally, so one is kept per company. Which one is NOT
# guessable from the letter: Alphabet's plain ticker is the non-voting
# retail line, while for Fox and News Corp the "A" line is the widely
# traded one. Each was checked individually rather than pattern-matched.
DUPLICATE_SHARE_CLASSES_TO_DROP = {"GOOGL", "FOX", "NWS"}

# Which Stage 1 track a company is judged on. The rule for adding one:
# a track is justified when a metric MISREADS a business model, never
# because a sector simply scores lower. See docs/FUNNEL_SPEC.md.
FINANCIAL_SECTORS = {"Financials"}
UTILITY_SECTORS = {"Utilities"}
CAPITAL_INTENSIVE_SECTORS = {"Communication Services"}
UNASSESSED_SECTORS = {"Real Estate"}      # REITs need funds-from-operations

# Managed-care insurers that the index files under Health Care. They are
# insurance companies — premiums in, claims out, large investment float —
# so return on assets misreads them exactly as it does a bank. Named
# explicitly: matching on company name wrongly swept in hospital chains,
# a drug distributor and a device maker.
HEALTH_INSURERS = {"UNH", "ELV", "CI", "HUM", "CNC", "MOH", "CVS"}


def load_sp500() -> list[dict]:
    """Return [{ticker, name, sector}, ...] for the current index.

    The page is fetched with requests rather than handed to pandas as a
    URL. pandas would download it through urllib, which on macOS relies
    on a system certificate store that a python.org install does not
    populate — so the fetch fails with CERTIFICATE_VERIFY_FAILED on a
    machine where everything else works. requests carries its own CA
    bundle, and this is also the only way to set a User-Agent.
    """
    html = requests.get(WIKI_SP500, headers={"User-Agent": WIKI_USER_AGENT},
                        timeout=30)
    html.raise_for_status()
    table = pd.read_html(io.StringIO(html.text))[0]
    rows = []
    for _, r in table.iterrows():
        ticker = str(r["Symbol"]).strip().replace(".", "-")
        if ticker in DUPLICATE_SHARE_CLASSES_TO_DROP:
            continue
        rows.append({
            "ticker": ticker,
            "name": str(r["Security"]).strip(),
            "sector": str(r["GICS Sector"]).strip(),
        })
    return sorted(rows, key=lambda x: x["ticker"])


def track_for(ticker: str, sector: str) -> str:
    """Which Stage 1 track judges this company."""
    if ticker in HEALTH_INSURERS or sector in FINANCIAL_SECTORS:
        return "financial"
    if sector in UTILITY_SECTORS:
        return "utility"
    if sector in CAPITAL_INTENSIVE_SECTORS:
        return "capital_intensive"
    if sector in UNASSESSED_SECTORS:
        return "unassessed"
    return "standard"


if __name__ == "__main__":
    import collections
    rows = load_sp500()
    print(f"{len(rows)} companies after de-duplication")
    by_track = collections.Counter(track_for(r["ticker"], r["sector"]) for r in rows)
    for t, n in by_track.most_common():
        print(f"   {t:18s} {n:3d}")
