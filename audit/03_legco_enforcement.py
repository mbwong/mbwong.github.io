#!/usr/bin/env python3
"""
Audit step 3: harvest LegCo question replies carrying vice-enforcement counts.

This builds the enforcement panel -- the right-hand-side variable for the
event-study design, and the only public series that is broken out by offence
and (sometimes) by district.

Confirmed to exist: LCQ5 "Combating illegal prostitution" (28 Oct 2015),
https://www.info.gov.hk/gia/general/201510/28/P201510280666.htm , whose
Annex 1 gives persons arrested for "procuring/controlling of prostitution"
and "keeping a vice establishment" over the preceding five years. A 2004
LegCo paper separately reports 700+ detected cases of managing a vice
establishment and living on the earnings of prostitution over eight months,
so annual counts are in the hundreds. That is enough variation to work with.

Approach: every LegCo written reply is published verbatim as an info.gov.hk
press release. Walk the daily index pages, keep releases whose titles look
like Council questions on vice, fetch those, and pull out every HTML table.
Tables are written as-is for hand-checking; do not trust automatic parsing of
government annexes without eyeballing them.

Usage:
    python 03_legco_enforcement.py --from 2005 --to 2026
    python 03_legco_enforcement.py --from 2015 --to 2015   # smoke test
"""

import argparse
import csv
import datetime as dt
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.info.gov.hk"
CACHE = ".cache_gia"

# Titles worth opening. Deliberately broad: recall matters more than precision
# here, since a false positive costs one fetch and a false negative loses a
# year of the panel.
TITLE_HINTS = re.compile(
    r"(vice|prostitut|brothel|sex\s*work|one[- ]woman|massage|"
    r"trafficking in persons|sexual exploitation)", re.I)

# Within a matched release, these tell us the reply actually carries numbers.
NUMERIC_HINTS = re.compile(
    r"(arrest|prosecut|convict|detect|raid|operation|annex)", re.I)

HEADERS = {
    "User-Agent": ("academic-feasibility-audit/0.1 "
                   "(research use; contact: berlin.wong@gmail.com)")
}


def get(session, url, delay=0.4):
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url)[-180:]
    path = os.path.join(CACHE, key + ".html")
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    for attempt in range(4):
        try:
            r = session.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 404:
                return ""
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 3:
                print(f"  FAILED {url}: {e}", file=sys.stderr)
                return ""
            time.sleep(2 ** (attempt + 1))
    time.sleep(delay)
    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)
    return r.text


def daily_index(session, day):
    """Return (title, url) pairs from one day's press-release index."""
    url = f"{BASE}/gia/general/{day:%Y%m}/{day:%d}.htm"
    html = get(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        href = urljoin(url, a["href"])
        if re.search(r"/gia/general/\d{6}/\d{2}/P\d+\.htm", href):
            out.append((title, href))
    return out


def extract_tables(html):
    """Return every HTML table as a list of row-lists."""
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [td.get_text(" ", strip=True)
                     for td in tr.find_all(["td", "th"])]
            if any(c for c in cells):
                rows.append(cells)
        if len(rows) >= 2:
            tables.append(rows)
    return tables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="y0", type=int, default=2005)
    ap.add_argument("--to", dest="y1", type=int, default=2026)
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    session = requests.Session()

    hits_path = os.path.join(args.outdir, "legco_vice_releases.csv")
    tables_path = os.path.join(args.outdir, "legco_vice_tables.csv")

    n_days = n_hits = n_tables = 0
    start = dt.date(args.y0, 1, 1)
    end = min(dt.date(args.y1, 12, 31), dt.date.today())

    with open(hits_path, "w", newline="", encoding="utf-8") as fh, \
         open(tables_path, "w", newline="", encoding="utf-8") as ft:
        wh = csv.writer(fh)
        wh.writerow(["date", "title", "url", "has_numbers", "n_tables"])
        wt = csv.writer(ft)
        wt.writerow(["date", "url", "table_idx", "row_idx", "cells"])

        day = start
        while day <= end:
            n_days += 1
            if n_days % 200 == 0:
                print(f"  ...{day} ({n_hits} hits so far)", file=sys.stderr)
            for title, url in daily_index(session, day):
                if not TITLE_HINTS.search(title):
                    continue
                html = get(session, url)
                if not html:
                    continue
                text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
                has_num = bool(NUMERIC_HINTS.search(text))
                tables = extract_tables(html)
                n_hits += 1
                n_tables += len(tables)
                wh.writerow([day.isoformat(), title, url, has_num, len(tables)])
                for ti, tbl in enumerate(tables):
                    for ri, row in enumerate(tbl):
                        wt.writerow([day.isoformat(), url, ti, ri, " | ".join(row)])
            day += dt.timedelta(days=1)

    print(f"\n{'='*64}\nLEGCO / GIA HARVEST {args.y0}-{args.y1}\n{'='*64}")
    print(f"  days scanned        {n_days:,}")
    print(f"  vice-related items  {n_hits:,}")
    print(f"  tables extracted    {n_tables:,}")
    print(f"\nwrote {hits_path}\nwrote {tables_path}")
    print("\nNext: open legco_vice_tables.csv and hand-check the annex tables. "
          "Government annexes are inconsistently formatted across years; "
          "budget a day for reconciliation, not an hour.")


if __name__ == "__main__":
    main()
