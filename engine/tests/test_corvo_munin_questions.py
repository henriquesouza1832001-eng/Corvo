"""Synthetic fixtures for closed Munin questions and explicit resolution rules."""
from types import SimpleNamespace

import pytest

from corvo_engine.munin.questions import (
    MIN_VOLATILITY_RETURNS,
    PRICE_RULE_VERSION,
    _horizon_hours,
    questions_for_event,
)


def test_questions_are_closed_deterministic_and_describe_the_resolution_rule():
    event = SimpleNamespace(event_id="evt_synthetic_1", topics=("cripto",))
    first = questions_for_event(event, available_price_symbols={"BTC", "ETH"})
    second = questions_for_event(event, available_price_symbols={"BTC", "ETH"})

    assert first == second
    assert len(first) == 2
    assert {q.asset for q in first} == {"BTC", "ETH"}
    assert all(q.instrument_available for q in first)
    assert all(q.rule_version == PRICE_RULE_VERSION for q in first)
    assert all(q.min_prior_returns == MIN_VOLATILITY_RETURNS == 30 for q in first)
    assert all("crypto trades continuously" in q.annulment_rule for q in first)
    assert all("30 prior same-horizon returns" in q.resolution_rule for q in first)
    assert all("retorno anormal logarítmico" in q.text and "6h" in q.text and "30 retornos de 6h" in q.text for q in first)
    assert all("anteriores ao instante em que o evento ficou disponível" in q.text for q in first)
    assert all("anteriores à publicação" not in q.text for q in first)
    assert all(q.direction == "down" and q.question_id.startswith("q_") for q in first)


def test_questions_do_not_guess_fx_pair_or_claim_missing_asset_price():
    event = SimpleNamespace(event_id="evt_synthetic_2", topics=("banco_central", "dados_macro"))
    questions = questions_for_event(event, available_price_symbols={"USDBRL", "USDEUR", "BTC"})

    usd = next(q for q in questions if q.asset == "USD")
    assert usd.instrument_available is False  # USD is not silently mapped to a particular FX pair.
    assert any(q.asset == "OURO" and not q.instrument_available for q in questions)
    assert "calendar unknown" in usd.annulment_rule
    assert len({(q.asset, q.direction, q.horizon_hours) for q in questions}) == len(questions)


def test_missing_event_identity_or_topics_produces_no_questions():
    assert questions_for_event(SimpleNamespace(event_id="", topics=("cripto",))) == []
    assert questions_for_event(SimpleNamespace(event_id="evt_synthetic_3", topics=())) == []


def test_horizon_parser_refuses_ambiguous_units():
    assert _horizon_hours("24h") == 24
    with pytest.raises(ValueError, match="unsupported horizon"):
        _horizon_hours("1d")
