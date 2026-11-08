"""Conservative deterministic event grouping for local Munin backtests.

This module proposes event identity from article metadata. It does not infer
market impact, and its similarity threshold is deliberately conservative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
import unicodedata
from typing import Iterable


_STOP_WORDS = frozenset(
    "a an and as at before by for from how in into near of on or over says say "
    "said the their to with after another amid this that its us uk".split()
)


@dataclass(frozen=True)
class Event:
    event_id: str
    title: str
    topics: tuple[str, ...]
    first_observed_at: str
    source_ids: tuple[str, ...]
    articles: tuple[dict, ...]
    confirmation: str


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tokens(title: object) -> frozenset[str]:
    text = unicodedata.normalize("NFKD", str(title or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return frozenset(token for token in re.findall(r"[a-z0-9]+", text) if token not in _STOP_WORDS)


def _topics(article: dict) -> frozenset[str]:
    values = article.get("topics")
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (tuple, list, set, frozenset)):
        values = [article.get("topic")] if article.get("topic") else []
    return frozenset(str(value) for value in values if value)


def title_similarity(left: object, right: object) -> float:
    """Jaccard overlap of normalized content words; empty titles never match."""
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _matches(left: dict, right: dict, max_gap_hours: float, min_similarity: float) -> bool:
    left_topics, right_topics = _topics(left), _topics(right)
    if not left_topics.intersection(right_topics):
        return False
    left_time = _parse_time(left.get("published_at"))
    right_time = _parse_time(right.get("published_at"))
    if left_time is None or right_time is None:
        return False
    if abs((left_time - right_time).total_seconds()) > max_gap_hours * 3600:
        return False
    return title_similarity(left.get("title"), right.get("title")) >= min_similarity


def build_events(
    articles: Iterable[dict],
    *,
    official_sources: Iterable[str] = (),
    max_gap_hours: float = 48,
    min_similarity: float = 0.30,
) -> list[Event]:
    """Group articles using complete-link matching to prevent chaining.

    Only records with a URL, source, title and parseable publication time can
    form events. An event is ``official`` only when its source is explicitly
    named in ``official_sources``; otherwise independent coverage is labeled
    ``multi_source`` or ``single_source``. Unknown provenance is never promoted.
    """
    if max_gap_hours < 0 or not 0 <= min_similarity <= 1:
        raise ValueError("invalid event matching limits")
    official = frozenset(str(source) for source in official_sources)
    prepared: list[dict] = []
    seen_urls: set[str] = set()
    for raw in articles:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        source = str(raw.get("source_id") or "").strip()
        title = str(raw.get("title") or "").strip()
        published = _parse_time(raw.get("published_at"))
        if not url or not source or not title or published is None or url in seen_urls:
            continue
        seen_urls.add(url)
        row = dict(raw)
        row["_published"] = published
        prepared.append(row)
    prepared.sort(key=lambda row: (row["_published"], row["url"]))

    groups: list[list[dict]] = []
    for article in prepared:
        matches = [
            group for group in groups
            if all(_matches(article, member, max_gap_hours, min_similarity) for member in group)
        ]
        if matches:
            # Deterministically join the earliest compatible group; complete-link
            # above prevents one broad headline from chaining unrelated events.
            matches[0].append(article)
        else:
            groups.append([article])

    events: list[Event] = []
    for group in groups:
        group.sort(key=lambda row: (row["_published"], row["url"]))
        first = group[0]
        sources = tuple(sorted({str(row["source_id"]) for row in group}))
        topics = tuple(sorted({topic for row in group for topic in _topics(row)}))
        confirmation = "official" if official.intersection(sources) else (
            "multi_source" if len(sources) > 1 else "single_source"
        )
        # The first article anchors identity, so adding later coverage does not
        # change a previously emitted event identifier.
        anchor = str(first["url"]).strip().casefold()
        event_id = "evt_" + hashlib.sha256(anchor.encode("utf-8")).hexdigest()[:20]
        clean_articles = tuple({k: v for k, v in row.items() if k != "_published"} for row in group)
        events.append(Event(
            event_id=event_id,
            title=str(first["title"]),
            topics=topics,
            first_observed_at=first["_published"].isoformat().replace("+00:00", "Z"),
            source_ids=sources,
            articles=clean_articles,
            confirmation=confirmation,
        ))
    return events
