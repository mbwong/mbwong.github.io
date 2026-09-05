"""Collect YouTube comments on Hong Kong ticketing coverage.

The one Tier A source with a public, documented, terms-permitted API and no
application process. Two phases:

  discover  search.list        100 quota units per call, up to 50 videos each
  fetch     commentThreads.list  1 quota unit per call, up to 100 threads each

That asymmetry drives the design. Discovery is the scarce resource, so video
queries are curated and stored; comments are close to free once you have the
video ids. Default daily quota is 10,000 units, so roughly 20 searches leaves
about 8,000 units, which is far more comment pages than a pilot needs.

Raw API responses are written to disk before any transformation, so the corpus
can be rebuilt if the codebook or normalisation changes without re-spending
quota.

    export YOUTUBE_API_KEY=...
    export TICKETING_SALT=...
    python src/collect/youtube.py --queries-file data/queries.txt \\
        --out-raw data/raw/youtube --out-units data/units_youtube.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import normalise  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
SEARCH_COST = 100
COMMENT_COST = 1
DEFAULT_DAILY_QUOTA = 10_000


class QuotaLedger:
    """Track spend so a run cannot silently exhaust the day's allowance."""

    def __init__(self, budget: int = DEFAULT_DAILY_QUOTA) -> None:
        self.budget = budget
        self.spent = 0
        self.calls = 0

    def charge(self, cost: int) -> None:
        if self.spent + cost > self.budget:
            raise QuotaExhausted(
                f"would spend {self.spent + cost} of {self.budget} units; stopping"
            )
        self.spent += cost
        self.calls += 1

    def __str__(self) -> str:
        return f"{self.spent}/{self.budget} quota units over {self.calls} calls"


class QuotaExhausted(RuntimeError):
    pass


def get(
    endpoint: str, params: Dict[str, Any], key: str, ledger: QuotaLedger, cost: int
) -> Dict[str, Any]:
    """One API call, with quota accounting and bounded retry on 5xx."""
    ledger.charge(cost)
    query = urllib.parse.urlencode({**params, "key": key})
    url = f"{API}/{endpoint}?{query}"

    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            raise ApiError(exc.code, body) from exc
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError("unreachable")


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:400]}")
        self.status = status
        self.body = body

    @property
    def reason(self) -> str:
        try:
            errors = json.loads(self.body)["error"].get("errors", [])
            return errors[0].get("reason", "") if errors else ""
        except Exception:  # noqa: BLE001 - best-effort parse of an error body
            return ""


def search_videos(
    query: str,
    key: str,
    ledger: QuotaLedger,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    region: str = "HK",
    language: str = "zh-Hant",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(limit, 50),
        "regionCode": region,
        "relevanceLanguage": language,
        "order": "relevance",
    }
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before

    payload = get("search", params, key, ledger, SEARCH_COST)
    videos = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item["snippet"]
        videos.append(
            {
                "video_id": video_id,
                "title": snippet.get("title"),
                "channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "query": query,
            }
        )
    return videos


def fetch_comment_threads(
    video_id: str, key: str, ledger: QuotaLedger, max_pages: int = 10
) -> Iterator[Dict[str, Any]]:
    """Yield raw commentThread items. Skips videos with comments disabled."""
    page_token = None
    for _ in range(max_pages):
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
            "order": "time",
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            payload = get("commentThreads", params, key, ledger, COMMENT_COST)
        except ApiError as exc:
            if exc.reason in {"commentsDisabled", "videoNotFound", "forbidden"}:
                return
            raise

        yield from payload.get("items", [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            return


def flatten_thread(item: Dict[str, Any], video: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One thread into adapter-shaped records.

    The codebook treats a top-level comment and each reply as separate units,
    so they are flattened here rather than nested.
    """
    records = []
    top = item["snippet"]["topLevelComment"]
    comments = [top] + list(item.get("replies", {}).get("comments", []))
    for comment in comments:
        snippet = comment["snippet"]
        author = snippet.get("authorChannelId", {}).get("value")
        if not author:
            # No stable author id means no panel membership and no dedupe key.
            # Fall back to the comment id so the unit is still usable, and mark
            # it so the panel analysis can exclude it.
            author = f"anon:{comment['id']}"
        text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""
        if not text.strip():
            continue
        records.append(
            {
                "id": comment["id"],
                "author_id": author,
                "posted_at": snippet["publishedAt"],
                "text": text,
                "thread_title": video.get("title"),
                "url": f"https://www.youtube.com/watch?v={video['video_id']}"
                f"&lc={comment['id']}",
            }
        )
    return records


def read_queries(path: pathlib.Path) -> List[str]:
    queries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            queries.append(line)
    return queries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries-file", type=pathlib.Path)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--published-after", help="RFC3339, e.g. 2024-01-01T00:00:00Z")
    parser.add_argument("--published-before")
    parser.add_argument("--videos-per-query", type=int, default=25)
    parser.add_argument("--max-comment-pages", type=int, default=10)
    parser.add_argument("--quota", type=int, default=DEFAULT_DAILY_QUOTA)
    parser.add_argument("--events", type=pathlib.Path)
    parser.add_argument("--out-raw", type=pathlib.Path, required=True)
    parser.add_argument("--out-units", type=pathlib.Path, required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and the quota estimate. No API calls, no key needed.",
    )
    args = parser.parse_args()

    queries = list(args.query)
    if args.queries_file:
        queries += read_queries(args.queries_file)
    if not queries:
        raise SystemExit("no queries given; use --query or --queries-file")

    estimate = len(queries) * SEARCH_COST + (
        len(queries) * args.videos_per_query * args.max_comment_pages * COMMENT_COST
    )
    print(f"{len(queries)} queries, up to {args.videos_per_query} videos each")
    print(f"worst-case quota: {estimate} units against a budget of {args.quota}")
    if estimate > args.quota:
        print("  note: the run will stop cleanly when the budget is reached")

    if args.dry_run:
        for query in queries:
            print(f"  search: {query}")
        return 0

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("YOUTUBE_API_KEY is not set")
    salt = os.environ.get("TICKETING_SALT")
    if not salt:
        raise SystemExit(
            "TICKETING_SALT is not set; author ids must never be hashed unsalted"
        )

    events = normalise.load_events(args.events) if args.events else None
    ledger = QuotaLedger(args.quota)
    args.out_raw.mkdir(parents=True, exist_ok=True)

    videos: Dict[str, Dict[str, Any]] = {}
    try:
        for query in queries:
            found = search_videos(
                query,
                key,
                ledger,
                args.published_after,
                args.published_before,
                limit=args.videos_per_query,
            )
            for video in found:
                videos.setdefault(video["video_id"], video)
            print(f"  '{query}' -> {len(found)} videos ({ledger})")
    except QuotaExhausted as exc:
        print(f"  stopped during discovery: {exc}")

    (args.out_raw / "videos.json").write_text(
        json.dumps(list(videos.values()), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(videos)} distinct videos")

    units: List[Dict[str, Any]] = []
    skipped = 0
    try:
        for video_id, video in videos.items():
            raw_items = list(
                fetch_comment_threads(video_id, key, ledger, args.max_comment_pages)
            )
            if not raw_items:
                skipped += 1
                continue
            (args.out_raw / f"comments_{video_id}.json").write_text(
                json.dumps(raw_items, ensure_ascii=False), encoding="utf-8"
            )
            for item in raw_items:
                for record in flatten_thread(item, video):
                    units.append(
                        normalise.normalise(record, "youtube", salt=salt, events=events)
                    )
    except QuotaExhausted as exc:
        print(f"  stopped during comment fetch: {exc}")

    before = len(units)
    units = normalise.dedupe(units)
    args.out_units.parent.mkdir(parents=True, exist_ok=True)
    with args.out_units.open("w", encoding="utf-8") as handle:
        for unit in units:
            handle.write(json.dumps(unit, ensure_ascii=False) + "\n")

    print(f"{before} comments, {len(units)} after dedupe, {skipped} videos with none")
    print(f"raw responses in {args.out_raw}, units in {args.out_units}")
    print(f"spent {ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
