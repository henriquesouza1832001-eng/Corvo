"""Synthetic fixtures for deterministic Munin event grouping."""
from corvo_engine.munin.events import build_events, title_similarity
from corvo_engine.munin.mneme_export import exportar_para_mneme


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


def test_export_mneme_preserva_pit_e_nao_confunde_publicacao_oficial_com_fato():
    momento = "2026-11-01T12:00:00Z"
    titulo = "Central bank raises rates after inflation report"
    decisoes = [
        {"source_id": "central-bank", "source_is_official": True, "source_reliability": 0.9, "url": "https://bank.test/rate",
         "title": titulo, "published_at": momento, "cycle_at": "2026-11-01T12:05:00Z", "kind": "fato", "verdict": "hot",
         "reason": "relevant", "relevance": 0.98, "topics": ["banco_central"]},
        {"source_id": "market-desk", "source_is_official": False, "source_reliability": 0.7, "url": "https://desk.test/rate",
         "title": titulo, "published_at": "2026-11-01T12:01:00Z", "cycle_at": "2026-11-01T12:10:00Z", "kind": "reportagem", "verdict": "buffer",
         "reason": "batch_later", "relevance": 0.72, "topics": ["banco_central"]},
        {"source_id": "market-desk", "url": "https://desk.test/noise", "title": "Sports result", "published_at": momento,
         "cycle_at": "2026-11-01T12:10:00Z", "verdict": "drop", "reason": "irrelevant", "topics": []},
    ]

    export = exportar_para_mneme(decisoes)

    assert export["preview_version"] == "corvo-mneme-preview-v0"
    assert len(export["articles"]) == 2
    official = export["articles"][0]
    assert official["tipo_evidencia"] == "publicacao_institucional"
    assert official["estado_alegacao"] == "nao_confirmada_independentemente"
    assert official["confiabilidade_fonte_inicial"] == 0.9
    assert official["recebido_em"] == "2026-11-01T12:05:00Z"
    assert official["suspeito"] is None and official["verificacao_injecao"] == "pendente_no_destino"
    assert official["texto_externo_nao_confiavel"] is True
    assert len(export["events"]) == 1
    event = export["events"][0]
    assert event["available_at"] == "2026-11-01T12:10:00Z"
    assert event["source_independence"] == "unverified"
    assert event["state"] == "candidate"


def test_export_mneme_nao_inventa_hora_de_chegada_ausente():
    export = exportar_para_mneme([{
        "source_id": "market-desk", "source_is_official": False, "url": "https://desk.test/item",
        "title": "Exchange halts trading after outage", "published_at": "2026-11-01T12:00:00Z",
        "verdict": "hot", "reason": "relevant", "relevance": 0.95, "topics": ["mercado"],
    }])

    assert len(export["articles"]) == 1
    assert export["articles"][0]["recebido_em"] is None
    assert len(export["events"]) == 1
    assert export["events"][0]["available_at"] is None
    assert export["events"][0]["observation_time_basis"] == "missing_cycle_at"


def test_export_mneme_nao_assume_fuso_para_timestamp_sem_timezone():
    export = exportar_para_mneme([{
        "source_id": "market-desk", "url": "https://desk.test/item", "title": "Exchange halts trading after outage",
        "published_at": "2026-11-01T12:00:00", "cycle_at": "2026-11-01T12:02:00", "verdict": "hot",
        "reason": "relevant", "relevance": 0.95, "topics": ["mercado"],
    }])

    assert export["articles"][0]["publicado_em"] is None
    assert export["articles"][0]["recebido_em"] is None
    assert export["events"] == []


def test_export_mneme_deduplica_url_canonica():
    base = {"source_id": "market-desk", "url": "https://desk.test/item", "title": "Exchange halts trading after outage",
            "published_at": "2026-11-01T12:00:00Z", "cycle_at": "2026-11-01T12:02:00Z", "verdict": "hot",
            "reason": "relevant", "relevance": 0.95, "topics": "mercado"}
    duplicada = {**base, "url": "https://desk.test/item?utm_campaign=copy"}

    export = exportar_para_mneme([base, duplicada])

    assert len(export["articles"]) == 1
    assert len(export["events"]) == 1
