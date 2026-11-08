"""RT-003: corpus de hard negatives do Sentinela + positivos. Métricas por cenário e propriedades gerais."""
import dataclasses

import pytest

from corvo_engine.research.sentinel import SentinelConfig
from corvo_engine.research.sentinel_eval import replay, summarize
from tests.adversarial import corpus as C

_CACHE: dict = {}


def cached_replay(sc):
    """O replay é a parte cara: cada cenário (determinístico) roda uma vez por sessão de teste."""
    key = (sc.name, sc.calendar is None)
    if key not in _CACHE:
        _CACHE[key] = replay(sc)
    return _CACHE[key]


@pytest.mark.parametrize("make", C.NEGATIVES, ids=lambda f: f.__name__)
def test_hard_negative_opens_nothing(make):
    sc = make()
    r = cached_replay(sc)
    assert r["opened"] == 0, f"{sc.name}: {[(i['reasons'], i['expectedness']) for i in r['investigations']]}"
    assert r["false_per_day"] == 0.0


@pytest.mark.parametrize("make", C.positives() and [lambda s=s: s for s in C.positives()] + [C.football_with_real_incident], ids=lambda f: f().name)
def test_positive_scenarios_open_before_t0_with_an_explanation(make):
    r = cached_replay(make())
    assert r["useful_investigations"] >= 1 and r["lead_time_min"] is not None and r["lead_time_min"] >= 0
    first = min(r["investigations"], key=lambda i: i["opened_at"])
    assert first["reasons"], "toda abertura precisa de motivo explicável"


@pytest.mark.parametrize("make", C.CONTRADICTIONS, ids=lambda f: f.__name__)
def test_contradiction_scenarios_never_become_confirmed(make):
    from corvo_engine.research.validator import validate
    from corvo_engine.research.sentinel import Investigation
    sc = make()
    inv = Investigation("inv-x", "UF:MG", sc.signals[0].category, "NEW", sc.end, sc.end, 0.5, 0.5, 0, False)
    v = validate(inv, sc.signals)
    assert v.suggested_status == "DISPUTED" and v.claim_state == "DISPUTED"  # nunca CONFIRMED; a divergência fica registrada
    assert v.contradictions and not v.official_confirmation  # negativa oficial não é confirmação


def test_context_is_what_prevents_the_scheduled_event_false_positive():
    """Sem o calendário, o jogo/feriado programado vira falso positivo: o contexto é necessário, não decorativo."""
    for make in (C.football, C.concert, C.scheduled_event, C.holiday):
        sc = make()
        assert cached_replay(sc)["opened"] == 0
        assert cached_replay(dataclasses.replace(sc, calendar=None))["opened"] >= 1, f"{sc.name}: o cenário nem seria um falso positivo sem contexto"


def test_single_origin_and_social_only_volume_cannot_open_alone():
    """Cascata de uma origem e enxurrada só social são abertas pela anomalia SE o gate de evidência for removido: ele é necessário."""
    from corvo_engine.research.sentinel import detect_candidates, should_investigate
    for make in (C.news_burst, C.social_burst, C.viral_repost, C.duplicate_storm, C.old_news_resurface):
        sc = make()
        cands = [c for c in detect_candidates([s for s in sc.signals if s.timestamp <= sc.end], sc.obs_rows, sc.end) if c.score >= 0.65]
        assert cands, f"{sc.name}: sem anomalia bruta, o cenário não testa o gate"
        assert all(not should_investigate(c)[0] for c in cands)
        assert any(should_investigate(c, SentinelConfig(min_anomaly_origins=0))[0] or c.independent_origins < 1 for c in cands)


def test_investigation_reasons_are_explainable_and_expectedness_is_reported():
    r = cached_replay(C.positives()[0])
    for i in r["investigations"]:
        assert i["expectedness"] in ("UNEXPECTED", "EXPECTED", "UNKNOWN") and i["origins"] is not None and i["reasons"]


def test_summary_metrics_of_the_whole_corpus():
    results = [cached_replay(m()) for m in C.NEGATIVES] + [cached_replay(p) for p in C.positives()] + [cached_replay(C.football_with_real_incident())]
    s = summarize(results)
    assert s["negatives"] == 15 and s["false_investigations"] == 0 and s["negatives_clean"] == 15 and s["false_per_day_max"] == 0.0
    assert s["positives"] == 4 and s["positives_detected_before_t0"] == 4
