#!/usr/bin/env python3
"""
Audit step 4: census of Hong Kong judgments mentioning the vice offences.

Decides whether there are enough usable judgments to support a paper built
purely on public court records -- the version of this project that needs no
adult-site scraping and clears an IRB in an afternoon.

Target offences (Crimes Ordinance, Cap 200). Section numbers are the ones
commonly cited; VERIFY them against the ordinance before you cite them in a
draft, they are not confirmed here:
  s.130-131  causing / procuring another to be a prostitute
  s.137      living on the earnings of prostitution of others
  s.139      keeping or managing a vice establishment
  s.147      soliciting for an immoral purpose

Two modes:

  --mode crawl   Walk /en/cases/<court>/<year>/ index pages, fetch each
                 judgment, keyword-match. Slow but does not depend on
                 guessing a search endpoint. Caches to disk so reruns are
                 cheap. Use this first.

  --mode search  Hit HKLII's search endpoint directly. Much faster, but the
                 endpoint and result selectors are NOT verified -- the audit
                 session that generated this file had no network egress.
                 Expect to fix SEARCH_URL and the selectors on first run.

Output: a CSV of one row per matching judgment (court, year, neutral
citation, URL, which offences matched, character count) plus a per-year
count table. Judgment text is cached but not committed.

Usage:
    python 02_hklii_census.py --mode crawl --court hkdc --from 2005 --to 2025
"""

import argparse
import csv
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.hklii.hk"
SEARCH_URL = BASE + "/en/search"          # UNVERIFIED
CACHE = ".cache_hklii"

# Courts worth crawling. District Court carries most vice prosecutions that
# generate a written judgment; magistrates' courts mostly do not publish, which
# is a real selection problem -- see README.
COURTS = {
    "hkdc": "District Court",
    "hkcfi": "Court of First Instance",
    "hkca": "Court of Appeal",
    "hkcfa": "Court of Final Appeal",
}

OFFENCE_PATTERNS = {
    "vice_establishment": re.compile(
        r"vice establishment", re.I),
    "living_on_earnings": re.compile(
        r"living on (?:the )?earnings of (?:the )?prostitution", re.I),
    "procuring": re.compile(
        r"\bprocur\w+\b[^.]{0,60}\bprostitut", re.I),
    "soliciting": re.compile(
        r"solicit\w*\s+for\s+an?\s+immoral\s+purpose", re.I),
    # Generic catch so we can measure how much the specific patterns miss.
    "any_prostitution": re.compile(r"prostitut", re.I),
}

HEADERS = {
    "User-Agent": ("academic-feasibility-audit/0.1 "
                   "(research use; contact: berlin.wong@gmail.com)")
}


def get(session, url, delay=1.0):
    """Fetch with on-disk cache and polite delay."""
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


def judgment_links(html, base_url):
    """Extract judgment URLs from an index page."""
    soup = BeautifulSoup(html, "html.parser")
    out = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # HKLII judgment paths look like /en/cases/hkdc/2019/1234
        if re.search(r"/cases/[a-z]+/\d{4}/\d+", href):
            out.add(urljoin(base_url, href.split("?")[0]))
    return sorted(out)


def crawl(session, court, y0, y1, writer, counts):
    for year in range(y0, y1 + 1):
        index_url = f"{BASE}/en/cases/{court}/{year}/"
        html = get(session, index_url)
        links = judgment_links(html, index_url)
        print(f"  {court} {year}: {len(links)} judgments", file=sys.stderr)
        if not links and html:
            print(f"    (no links parsed -- index layout may differ; "
                  f"check {index_url})", file=sys.stderr)
        for url in links:
            text = get(session, url, delay=0.5)
            if not text:
                continue
            body = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
            hits = [name for name, pat in OFFENCE_PATTERNS.items()
                    if name != "any_prostitution" and pat.search(body)]
            generic = bool(OFFENCE_PATTERNS["any_prostitution"].search(body))
            if not hits and not generic:
                continue
            cite = url.rstrip("/").split("/")[-1]
            writer.writerow([court, year, cite, url,
                             "|".join(hits) or "generic_only", len(body)])
            counts[(court, year)] = counts.get((court, year), 0) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["crawl", "search"], default="crawl")
    ap.add_argument("--court", default="hkdc", choices=list(COURTS))
    ap.add_argument("--from", dest="y0", type=int, default=2005)
    ap.add_argument("--to", dest="y1", type=int, default=2025)
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    if args.mode == "search":
        sys.exit("search mode: SEARCH_URL and result selectors are unverified. "
                 "Open https://www.hklii.hk/en/search in a browser, copy the "
                 "real query string, then implement. Use --mode crawl for now.")

    os.makedirs(args.outdir, exist_ok=True)
    out_path = os.path.join(args.outdir, f"hklii_{args.court}_{args.y0}_{args.y1}.csv")
    counts = {}
    session = requests.Session()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["court", "year", "citation", "url", "offences_matched", "chars"])
        crawl(session, args.court, args.y0, args.y1, w, counts)

    total = sum(counts.values())
    print(f"\n{'='*64}\nHKLII CENSUS: {COURTS[args.court]} {args.y0}-{args.y1}\n{'='*64}")
    for (c, y) in sorted(counts):
        print(f"  {y}  {counts[(c, y)]:>4}")
    print(f"  {'TOTAL':>4}  {total}")
    print(f"\nwrote {out_path}")
    print("\nDecision rule: >=200 judgments with substantive facts (rents, "
          "takings, worker origin, structure) supports a standalone paper on "
          "court records. <50 means judgments are a supplement, not a "
          "foundation.")


if __name__ == "__main__":
    main()
