import pytest

from corvo_engine.intake.gate import TOPICS
from corvo_engine.munin.baseline import METHOD, MIN_N, BaseRateModel, to_record
from corvo_engine.munin.impact import HYPOTHESES, candidates, question_for
from corvo_engine.munin.registry import RegistryError, validate_record

KEY = ("banco_central", "BTC", "24h")


def feed(model, yes, no, key=KEY):
    for _ in range(yes):
        model.update(key, True)
    for _ in range(no):
        model.update(key, False)


def test_abstains_without_enough_events():
    m = BaseRateModel()
    assert m.predict(KEY) is None  # nunca viu nada
    feed(m, 10, 19)  # 29 < 30
    assert m.predict(KEY) is None and m.n(KEY) == 29
    m.update(KEY, True)
    assert m.predict(KEY) is not None  # chegou a 30


def test_probability_follows_the_base_rate_with_light_shrinkage():
    m = BaseRateModel()
    feed(m, 12, 18)  # taxa-base observada: 40%
    p = m.predict(KEY)
    assert p.probability == pytest.approx((12 + 1) / (30 + 2), abs=1e-4)  # média da beta(13, 19)
    assert p.n == 30 and p.yes == 12


def test_interval_contains_the_probability_and_shrinks_with_more_data():
    small, big = BaseRateModel(), BaseRateModel()
    feed(small, 12, 18)
    feed(big, 120, 180)  # mesma taxa, 10x mais eventos
    ps, pb = small.predict(KEY), big.predict(KEY)
    for p in (ps, pb):
        assert 0.0 <= p.interval_low <= p.probability <= p.interval_high <= 1.0
    assert (pb.interval_high - pb.interval_low) < (ps.interval_high - ps.interval_low)  # mais dados, menos incerteza


def test_keys_are_independent():
    m = BaseRateModel()
    feed(m, 20, 10)
    other = ("energia", "PETROLEO", "24h")
    assert m.predict(other) is None and m.predict(KEY) is not None


def test_to_record_is_publishable_and_goes_through_the_same_validator_as_the_api():
    m = BaseRateModel()
    feed(m, 12, 18)
    rec = to_record(m.predict(KEY), "BTC sobe 1 desvio-padrão em 24 h?", sources=5, horizon="24h")
    assert validate_record(rec) is rec
    assert rec.method == METHOD and rec.status == "calibrando" and rec.evidences == 30 and rec.sources == 5
    with pytest.raises(RegistryError, match="evidências"):
        to_record(m.predict(KEY), "q?", sources=0, horizon="24h")  # sem fontes, não entra


def test_invalid_configuration_is_refused():
    with pytest.raises(ValueError):
        BaseRateModel(min_n=0)
    with pytest.raises(ValueError):
        BaseRateModel(prior_yes=0)


def test_min_n_matches_the_documented_rule():
    assert MIN_N == 30  # "nenhum peso muda com menos de 30 resolvidos" (docs/corvo/PREDITIVO.md)


# ---------- hipóteses de impacto ----------
def test_hypothesis_table_only_cites_real_gate_topics():
    assert set(HYPOTHESES) <= set(TOPICS), set(HYPOTHESES) - set(TOPICS)


def test_every_hypothesis_is_flagged_as_hypothesis_and_has_valid_fields():
    for hs in HYPOTHESES.values():
        for h in hs:
            assert h.hypothesis is True and h.direction in ("up", "down", "volatile") and h.horizon.endswith("h") and h.asset


def test_candidates_merge_topics_without_duplicates_and_ignore_unknown():
    got = candidates(["conflito_chave", "energia", "tema_que_nao_existe"])
    keys = [(h.asset, h.direction, h.horizon) for h in got]
    assert len(keys) == len(set(keys))
    assert ("PETROLEO", "up", "24h") in keys and ("PETROLEO", "volatile", "24h") in keys
    assert candidates(["tema_que_nao_existe"]) == []


def test_question_is_closed_and_has_a_horizon():
    h = HYPOTHESES["conflito_chave"][0]
    q = question_for("conflito_chave", h)
    assert "nas próximas 24h" in q and "desvio-padrão" in q and q.endswith("?")
