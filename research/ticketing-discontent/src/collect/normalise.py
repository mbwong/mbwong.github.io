"""Normalise raw records from any source into the unit schema.

Every collector emits whatever its platform returns. This module is the single
place that turns those into the flat unit record the coding pipeline expects,
and the single place that joins the event calendar to compute
`days_from_onsale`. Keeping it separate means a new source needs one adapter
function, not a new pipeline.

Unit record:
    unit_id, source, author_key, posted_at, thread_title, text,
    event_key, days_from_onsale, url

`author_key` is a salted hash, never a platform handle. The salt lives outside
the repository; without it the hashes cannot be reversed to accounts, and with
a per-project salt they still support the within-author panel analysis.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

ISO_DAY = "%Y-%m-%d"


def author_key(platform: str, author_id: str, salt: str) -> str:
    """Stable pseudonymous key. Same author, same key, within a project."""
    if not salt:
        raise ValueError("a salt is required; do not hash identifiers unsalted")
    digest = hashlib.sha256(f"{salt}|{platform}|{author_id}".encode("utf-8"))
    return digest.hexdigest()[:32]


def parse_dt(value: str) -> dt.datetime:
    """Parse an ISO-8601 timestamp, tolerating a trailing Z."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def onsale_moment(event: Dict[str, Any], tzinfo: Optional[dt.tzinfo]) -> dt.datetime:
    """The instant `days_from_onsale` is measured from.

    Anchored to `onsale_date` plus optional `onsale_time` (HH:MM, local). With
    no time given the anchor is midnight, so day 0 covers the whole calendar day
    of the sale. That is the safe default, but supplying the real start time
    sharpens the most important bin in E3: it separates pre-sale anticipation
    from the minutes after the queue opens, which are different grievances.
    """
    moment = dt.datetime.strptime(event["onsale_date"], ISO_DAY)
    clock = event.get("onsale_time")
    if clock:
        hour, minute = (int(part) for part in clock.split(":"))
        moment = moment.replace(hour=hour, minute=minute)
    return moment.replace(tzinfo=tzinfo)


def load_events(path: pathlib.Path) -> List[Dict[str, Any]]:
    events = json.loads(path.read_text(encoding="utf-8"))["events"]
    for event in events:
        if not event.get("onsale_date"):
            raise ValueError(
                f"event {event['key']} has no onsale_date; source it or drop the "
                "event rather than guessing"
            )
    return events


def match_event(
    text: str, posted_at: dt.datetime, events: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Assign a unit to an event by keyword, then by nearest on-sale date.

    Keyword match wins. Where several events match, the one whose on-sale date
    is nearest the post wins. Returns None when nothing matches, which is
    correct and common: unassigned units still count toward E1, just not E3.
    """
    hits = []
    for event in events:
        for keyword in event.get("keywords", []):
            if re.search(re.escape(keyword), text, re.IGNORECASE):
                hits.append(event)
                break
    if not hits:
        return None

    def distance(event: Dict[str, Any]) -> float:
        return abs((posted_at - onsale_moment(event, posted_at.tzinfo)).total_seconds())

    return min(hits, key=distance)


def days_from_onsale(posted_at: dt.datetime, event: Dict[str, Any]) -> float:
    """Days between the on-sale anchor and the post. Negative before the sale."""
    delta = posted_at - onsale_moment(event, posted_at.tzinfo)
    return delta.total_seconds() / 86400.0


def normalise(
    raw: Dict[str, Any],
    source: str,
    salt: str,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Turn one adapter-shaped record into a unit record.

    `raw` must already carry: id, author_id, posted_at (ISO-8601), text.
    Optional: thread_title, url.
    """
    posted_at = parse_dt(raw["posted_at"])
    unit = {
        "unit_id": f"{source}-{raw['id']}",
        "source": source,
        "author_key": author_key(source, str(raw["author_id"]), salt),
        "posted_at": posted_at.isoformat(),
        "thread_title": raw.get("thread_title"),
        "text": raw["text"],
        "url": raw.get("url"),
        "event_key": None,
        "days_from_onsale": None,
    }

    if events:
        event = match_event(raw["text"], posted_at, events)
        if event is not None:
            unit["event_key"] = event["key"]
            unit["days_from_onsale"] = round(days_from_onsale(posted_at, event), 3)
    return unit


def dedupe(units: Iterable[Dict[str, Any]], window_hours: int = 24) -> List[Dict[str, Any]]:
    """Codebook section 1: drop repeat text from one author within the window."""
    seen: Dict[tuple, dt.datetime] = {}
    kept: List[Dict[str, Any]] = []
    for unit in sorted(units, key=lambda u: u["posted_at"]):
        key = (unit["author_key"], unit["text"].strip())
        posted_at = parse_dt(unit["posted_at"])
        previous = seen.get(key)
        if previous is not None:
            if (posted_at - previous).total_seconds() <= window_hours * 3600:
                continue
        seen[key] = posted_at
        kept.append(unit)
    return kept
