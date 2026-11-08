"""Synthetic fixtures for deterministic Munin event grouping."""
from corvo_engine.munin.events import build_events, title_similarity


def article(source, title, url, published, topics=("conflito_chave",)):
    return {
        "source_id": source,
        "title": title,
        "url": url,
        "published_at": published,
        "cycle_at": published,
        "topics": list(topics),
    }


def test_independent_coverage_forms_one_event_and_uses_latest_arrival():
    rows = [
        article("wire-a", "Houthis say 25 killed in Yemen air strikes", "https://a.test/1", "2026-11-01T12:00:00Z"),
        article("wire-b", "Yemen: Houthis report 25 killed in air strike", "https://b.test/2", "2026-11-01T13:00:00Z"),
    ]
    events = build_events(rows)

    assert len(events) == 1
    assert events[0].source_ids == ("wire-a", "wire-b")
    assert events[0].confirmation == "multi_source"
    assert events[0].available_at == "2026-11-01T13:00:00Z"
    assert events[0].event_id.startswith("evt_")


def test_event_match_requires_shared_topic_and_time_window():
    base = article("wire-a", "Bank raises interest rate after inflation", "https://a.test/1", "2026-11-01T12:00:00Z", ("banco_central",))
    unrelated_topic = article("wire-b", "Bank raises interest rate after inflation", "https://b.test/2", "2026-11-01T13:00:00Z", ("empresas",))
    too_late = article("wire-c", "Bank raises interest rate after inflation", "https://c.test/3", "2026-11-04T13:00:00Z", ("banco_central",))

    assert len(build_events([base, unrelated_topic, too_late])) == 3


def test_event_availability_waits_for_all_clustered_articles_to_arrive():
    first = article("wire-a", "Bank raises rates after inflation report", "https://a.test/1", "2026-11-01T12:00:00Z")
    second = article("wire-b", "Bank raises rates after inflation report", "https://b.test/2", "2026-11-01T13:00:00Z")
    first["cycle_at"] = "2026-11-01T14:00:00Z"
    second["cycle_at"] = "2026-11-01T16:00:00Z"

    event = build_events([first, second])[0]

    assert event.available_at == "2026-11-01T16:00:00Z"
    assert event.observation_time_basis == "cycle_at"
    assert event.source_ids == ("wire-a", "wire-b")


def test_events_are_ordered_by_available_time_and_missing_cycle_time_is_not_guessed():
    earlier_published = article("a", "Central bank raises policy rate", "https://a.test/1", "2026-11-01T12:00:00Z", ("banco_central",))
    later_published = article("b", "Earthquake closes oil terminal", "https://b.test/2", "2026-11-01T13:00:00Z", ("energia",))
    earlier_published["cycle_at"] = "2026-11-01T18:00:00Z"
    later_published["cycle_at"] = "2026-11-01T14:00:00Z"
    missing = article("c", "Exchange halts trading", "https://c.test/3", "2026-11-01T15:00:00Z", ("mercado",))
    missing.pop("cycle_at")

    events = build_events([earlier_published, later_published, missing])

    assert [event.title for event in events] == [later_published["title"], earlier_published["title"], missing["title"]]
    assert events[2].available_at is None
    assert events[2].observation_time_basis == "missing_cycle_at"


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


def test_default_fit_threshold_accepts_boundary_pair_but_stricter_threshold_does_not():
    a = article("a", "Market shock alpha beta", "https://a.test", "2026-11-01T12:00:00Z", ("mercado",))
    b = article("b", "Market shock gamma delta epsilon zeta", "https://b.test", "2026-11-01T13:00:00Z", ("mercado",))

    assert title_similarity(a["title"], b["title"]) == 0.25
    assert len(build_events([a, b])) == 1
    assert len(build_events([a, b], min_similarity=0.30)) == 2


def test_invalid_time_and_empty_titles_are_not_grouped():
    invalid = article("a", "Some market event", "https://a.test", "not-a-time", ("mercado",))
    missing = article("b", "Some market event", "https://b.test", "2026-11-01T12:00:00Z", ("mercado",))
    empty = article("c", "", "https://c.test", "2026-11-01T12:00:00Z", ("mercado",))

    events = build_events([invalid, missing, empty])
    assert len(events) == 1
    assert events[0].source_ids == ("b",)
