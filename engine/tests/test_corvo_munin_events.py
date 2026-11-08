"""Synthetic fixtures for deterministic Munin event grouping."""
from corvo_engine.munin.events import build_events, title_similarity


def article(source, title, url, published, topics=("conflito_chave",)):
    return {
        "source_id": source,
        "title": title,
        "url": url,
        "published_at": published,
        "topics": list(topics),
    }


def test_independent_coverage_forms_one_event_and_keeps_earliest_publication():
    rows = [
        article("wire-a", "Houthis say 25 killed in Yemen air strikes", "https://a.test/1", "2026-11-01T12:00:00Z"),
        article("wire-b", "Yemen: Houthis report 25 killed in air strike", "https://b.test/2", "2026-11-01T13:00:00Z"),
    ]
    events = build_events(rows)

    assert len(events) == 1
    assert events[0].source_ids == ("wire-a", "wire-b")
    assert events[0].confirmation == "multi_source"
    assert events[0].first_observed_at == "2026-11-01T12:00:00Z"
    assert events[0].event_id.startswith("evt_")


def test_event_match_requires_shared_topic_and_time_window():
    base = article("wire-a", "Bank raises interest rate after inflation", "https://a.test/1", "2026-11-01T12:00:00Z", ("banco_central",))
    unrelated_topic = article("wire-b", "Bank raises interest rate after inflation", "https://b.test/2", "2026-11-01T13:00:00Z", ("empresas",))
    too_late = article("wire-c", "Bank raises interest rate after inflation", "https://c.test/3", "2026-11-04T13:00:00Z", ("banco_central",))

    assert len(build_events([base, unrelated_topic, too_late])) == 3


def test_duplicate_url_is_counted_once_and_official_requires_explicit_provenance():
    first = article("central-bank", "Policy rate increased", "https://bank.test/news", "2026-11-01T12:00:00Z", ("banco_central",))
    duplicate = dict(first)

    event = build_events([first, duplicate])[0]
    assert len(event.articles) == 1
    assert event.confirmation == "single_source"
    assert build_events([first], official_sources={"central-bank"})[0].confirmation == "official"


def test_complete_link_prevents_transitive_chaining():
    a = article("a", "Alpha beta gamma delta", "https://a.test", "2026-11-01T12:00:00Z", ("mercado",))
    b = article("b", "Alpha beta gamma epsilon", "https://b.test", "2026-11-01T12:30:00Z", ("mercado",))
    c = article("c", "Alpha beta epsilon zeta", "https://c.test", "2026-11-01T13:00:00Z", ("mercado",))

    assert title_similarity(a["title"], b["title"]) > title_similarity(a["title"], c["title"])
    events = build_events([a, b, c], min_similarity=0.40)
    assert sorted(len(event.articles) for event in events) == [1, 2]


def test_invalid_time_and_empty_titles_are_not_grouped():
    invalid = article("a", "Some market event", "https://a.test", "not-a-time", ("mercado",))
    missing = article("b", "Some market event", "https://b.test", "2026-11-01T12:00:00Z", ("mercado",))
    empty = article("c", "", "https://c.test", "2026-11-01T12:00:00Z", ("mercado",))

    events = build_events([invalid, missing, empty])
    assert len(events) == 1
    assert events[0].source_ids == ("b",)
