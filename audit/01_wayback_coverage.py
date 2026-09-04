#!/usr/bin/env python3
"""
Audit step 1+2: archival coverage and panel-linkage feasibility.

Answers two questions without downloading a single page of listing content:

  Q1 (coverage)  Do pre-2020 snapshots exist, at what cadence, and do they
                 straddle the Feb-2020 border closure? If not, the
                 border-closure design is dead.

  Q2 (linkage)   If listing URLs carry a stable ID, can the same listing be
                 observed in multiple months? The distribution of
                 months-observed-per-ID is the single number that decides
                 whether this is a panel or a repeated cross-section.

Method: the Wayback CDX API returns pure metadata rows
(urlkey, timestamp, original, mimetype, statuscode, digest, length).
We never request the archived pages themselves. The `digest` field is a
content hash, so we can measure how often a listing's content *changed*
between captures (a proxy for price/menu revisions) while remaining unable
to see what it said.

Privacy: extracted listing IDs are salted-hashed before they touch disk, and
URLs are never written out. Only distributions are persisted. This is the
pattern the real collection should follow too.

Usage:
    python 01_wayback_coverage.py --domain sex141.com
    python 01_wayback_coverage.py --domain sex141.com --id-regex '/(\\d{5,})'

Note: the CDX API is slow and paginates badly on large domains. --limit caps
rows; raise it once you know the domain is worth the wait.
"""

import argparse
import collections
import csv
import hashlib
import os
import re
import sys
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
FIELDS = ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"]

# Salt lives in the environment, not the repo. Without it the hashes are not
# reproducible across runs, which is deliberate for throwaway audit output.
SALT = os.environ.get("AUDIT_SALT", "").encode() or os.urandom(16)


def hid(s: str) -> str:
    return hashlib.blake2b(SALT + s.encode(), digest_size=8).hexdigest()


def fetch_cdx(domain, limit, from_ts=None, to_ts=None, session=None):
    """Page through the CDX API. Returns list of dicts."""
    session = session or requests.Session()
    params = {
        "url": domain,
        "matchType": "domain",
        "output": "json",
        "fl": ",".join(FIELDS),
        "collapse": "digest",      # drop consecutive identical-content captures
        "filter": "statuscode:200",
        "limit": str(limit),
    }
    if from_ts:
        params["from"] = from_ts
    if to_ts:
        params["to"] = to_ts

    for attempt in range(5):
        try:
            r = session.get(CDX, params=params, timeout=180)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 4:
                sys.exit(f"CDX request failed after 5 attempts: {e}")
            wait = 2 ** (attempt + 1)
            print(f"  retry in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)

    rows = r.json()
    if not rows:
        return []
    header, body = rows[0], rows[1:]
    return [dict(zip(header, row)) for row in body]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True,
                    help="bare domain, e.g. sex141.com")
    ap.add_argument("--id-regex", default=r"/(\d{4,})",
                    help="regex with one capture group extracting the stable "
                         "listing ID from the URL path. Inspect a few URLs "
                         "first; the default is a guess.")
    ap.add_argument("--limit", type=int, default=200000)
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", args.domain.lower())

    print(f"Querying CDX for {args.domain} (limit {args.limit})...", file=sys.stderr)
    rows = fetch_cdx(args.domain, args.limit)
    print(f"  {len(rows)} capture rows returned", file=sys.stderr)

    if not rows:
        print("\nNO CAPTURES. Either the domain never existed under this name, "
              "or it was excluded from the archive (robots.txt / takedown). "
              "Adult sites are frequently excluded. Check alternates before "
              "concluding the design is dead.")
        return

    # ---- Q1: coverage over time -------------------------------------------
    by_month = collections.Counter()
    for r_ in rows:
        ts = r_["timestamp"]
        by_month[f"{ts[:4]}-{ts[4:6]}"] += 1

    cov_path = os.path.join(args.outdir, f"{slug}_coverage_by_month.csv")
    with open(cov_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year_month", "captures"])
        for ym in sorted(by_month):
            w.writerow([ym, by_month[ym]])

    months = sorted(by_month)
    pre = [m for m in months if m < "2020-02"]
    post = [m for m in months if m >= "2020-02"]

    # ---- Q2: panel linkage -------------------------------------------------
    id_re = re.compile(args.id_regex)
    # listing_id -> set of months seen; listing_id -> set of content digests
    seen_months = collections.defaultdict(set)
    digests = collections.defaultdict(set)
    unmatched = 0

    for r_ in rows:
        m = id_re.search(r_["original"])
        if not m:
            unmatched += 1
            continue
        key = hid(m.group(1))
        seen_months[key].add(r_["timestamp"][:6])
        digests[key].add(r_["digest"])

    span = collections.Counter(len(v) for v in seen_months.values())
    span_path = os.path.join(args.outdir, f"{slug}_months_per_listing.csv")
    with open(span_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["distinct_months_observed", "n_listings"])
        for k in sorted(span):
            w.writerow([k, span[k]])

    n_ids = len(seen_months)
    multi = sum(v for k, v in span.items() if k >= 2)
    six_plus = sum(v for k, v in span.items() if k >= 6)
    changed = sum(1 for k, v in digests.items() if len(v) >= 2)

    # ---- verdict -----------------------------------------------------------
    print(f"\n{'='*64}\nCOVERAGE\n{'='*64}")
    print(f"  capture rows            {len(rows):,}")
    print(f"  distinct months         {len(months)}  ({months[0]} .. {months[-1]})")
    print(f"  months before 2020-02   {len(pre)}")
    print(f"  months from 2020-02 on  {len(post)}")
    print(f"  -> border-closure design: "
          f"{'VIABLE' if len(pre) >= 12 and len(post) >= 12 else 'NOT VIABLE on this domain'}")

    print(f"\n{'='*64}\nPANEL LINKAGE\n{'='*64}")
    print(f"  URLs matching id-regex  {len(rows)-unmatched:,} / {len(rows):,}"
          f"  ({unmatched:,} unmatched)")
    if unmatched > len(rows) * 0.5:
        print("  WARNING: >50% unmatched. Your --id-regex is probably wrong.")
        print("  Inspect real URLs before trusting anything below.")
    print(f"  distinct listing IDs    {n_ids:,}")
    if n_ids:
        print(f"  seen in >=2 months      {multi:,}  ({multi/n_ids:.1%})")
        print(f"  seen in >=6 months      {six_plus:,}  ({six_plus/n_ids:.1%})")
        print(f"  content changed >=once  {changed:,}  ({changed/n_ids:.1%})")
        print(f"  -> panel: {'VIABLE' if multi/n_ids > 0.3 else 'WEAK — likely repeated cross-section only'}")

    print(f"\nwrote {cov_path}\nwrote {span_path}")
    print("\nNo listing content was downloaded or stored.")


if __name__ == "__main__":
    main()
