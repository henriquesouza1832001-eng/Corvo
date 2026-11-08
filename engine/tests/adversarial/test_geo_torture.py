"""Geo torture: V1 e V2 sobre o MESMO corpus de 164 casos. Mede, não promove: o Geo V2 continua OFF até o gate separado aprovar."""
import pytest

from corvo_engine import flags
from corvo_engine.processing import geo_v2
from corvo_engine.processing.geo import locate
from corvo_engine.processing.geo_gate import promotion_gate
from tests.adversarial.geo_torture import CITY, NONE, STATE, cases, metrics


def v1(text):
    p = locate(text)
    return (p.uf, p.city) if p else None


def v2(text):
    r = geo_v2.resolve(text, None)
    return (r.uf, r.city) if r else None


M1, M2 = metrics(v1), metrics(v2)


def test_corpus_has_enough_adversarial_cases_in_every_family():
    cs = cases()
    assert len(cs) >= 150 and {c["precision"] for c in cs} == {CITY, STATE, NONE}
    groups = {c["group"] for c in cs}
    assert {"homonimo", "palavra-comum", "clube", "rio", "estado", "bairro", "aeroporto", "estadio", "barragem", "rodovia", "exterior",
            "regiao-metropolitana", "homonimo-ambiguo", "bairro-ambiguo", "sigla-uf", "alias"} <= groups
    assert sum(c["precision"] == NONE for c in cs) >= 60  # negativos suficientes para falsa precisão


def test_v1_baseline_false_precision_must_not_get_worse():
    assert M1["n"] == 164 and M1["false_precision_rate"] <= 0.0244 and M1["wrong_or_invented_state"] <= 8


def test_context_variations_do_not_change_the_answer_for_unambiguous_cases():
    """Prefixo/sufixo ('URGENTE:', 'veja imagens'...) não pode mudar o resultado do V1 num caso claro."""
    for base in ("sp-city", "campinas", "airport-gru"):
        answers = {v1(c["text"]) for c in cases() if c["base"] == base}
        assert len(answers) == 1, f"{base}: {answers}"


def test_measured_false_precision_of_v2_is_recorded():
    """O V2 NÃO é melhor que o V1 em falsa precisão neste corpus (medido: palavra comum e bairro ambíguo): fica registrado e reprovado no gate."""
    assert M2["false_precision_rate"] >= M1["false_precision_rate"]
    assert {"vitoria-word", "bairro-ambiguo"} & {i.split("#")[0] for i in M2["false_precision_ids"]}


def test_promotion_gate_is_separate_and_geo_v2_stays_off_until_it_passes():
    g = promotion_gate(M1, M2)
    assert g["external_blockers"]
    if g["passed"]:
        pytest.fail("o gate passou: atualizar docs/maturity e revisar com humano ANTES de mudar o padrão da flag (continua OFF por esta campanha)")
    assert g["reasons"] and flags.FLAGS["GEO_V2"][0] is False and flags.FLAGS["GEO_V2"][1] == "OFF"


def test_gate_rules_catch_each_failure_mode():
    ok = {"n": 200, "false_precision_rate": 0.0, "false_precision_rate_of_reported": 0.0, "city_correct": 60, "wrong_or_invented_state": 0,
          "by_group": {"homonimo": {"n": 10, "false_precision": 0}}}
    base = {"n": 200, "false_precision_rate": 0.02, "false_precision_rate_of_reported": 0.05, "city_correct": 50, "wrong_or_invented_state": 1, "by_group": {}}
    assert promotion_gate(base, ok)["passed"]
    assert any("corpus pequeno" in r for r in promotion_gate(base, {**ok, "n": 50})["reasons"])
    assert any("false_precision" in r for r in promotion_gate(base, {**ok, "false_precision_rate": 0.03})["reasons"])
    assert any("ganho" in r for r in promotion_gate(base, {**ok, "city_correct": 50})["reasons"])
    assert any("grupos" in r for r in promotion_gate(base, {**ok, "by_group": {"bairro": {"n": 10, "false_precision": 3}}})["reasons"])
    assert any("estado" in r for r in promotion_gate(base, {**ok, "wrong_or_invented_state": 5})["reasons"])
