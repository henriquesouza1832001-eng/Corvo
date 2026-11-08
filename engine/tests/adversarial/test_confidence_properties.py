"""Propriedades da Confiança V2 (aleatórias com semente fixa) e perda gradual de cobertura."""
import random
from datetime import datetime, timedelta, timezone

import pytest

from pulso_engine.intelligence.coverage import by_family, coverage_ratio, degrade, factor, view_state
from pulso_engine.models import Signal
from pulso_engine.scoring.confidence_v2 import confidence_v2
from pulso_engine.source_freshness import SourceReading, assess

NOW = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
WORDS = ("rua avenida ponte viaduto praça bairro escola mercado posto terminal rodovia túnel obra galeria represa córrego favela condomínio "
         "hospital aeroporto estação").split()


def sig(i, cls="NEWS_REGIONAL", title=None, source=None, text=None, minutes=5):
    ts = NOW - timedelta(minutes=minutes)
    ttl = title or f"{WORDS[i % 20]} {WORDS[(i * 7 + 3) % 20]} {WORDS[(i * 11 + 5) % 20]} tem problema número {i} segundo moradores locais"
    return Signal(signal_id=str(i), source_id=source or f"s{i}", source_class=cls, timestamp=ts, collected_at=ts, title=ttl, text=text,
                  category="WEATHER", hash=f"h{i}", state="MG")


def conf(signals, **kw):
    return confidence_v2(signals, **kw)[0]


def test_more_independent_origins_never_lowers_confidence():
    rnd = random.Random(11)
    for _ in range(25):
        n = rnd.randint(1, 8)
        base = [sig(i, rnd.choice(["NEWS_HIGH", "NEWS_REGIONAL"])) for i in range(n)]
        assert conf(base + [sig(100 + n, "NEWS_REGIONAL")]) >= conf(base)


def test_adding_copies_never_raises_confidence():
    rnd = random.Random(12)
    for _ in range(25):
        base = [sig(i, rnd.choice(["NEWS_HIGH", "NEWS_REGIONAL", "OFFICIAL"])) for i in range(rnd.randint(2, 6))]
        copies = [sig(200 + k, "NEWS_REGIONAL", title=base[0].title, source=f"copia{k}") for k in range(rnd.randint(1, 40))]
        assert conf(base + copies) <= conf(base)


def test_volume_alone_cannot_dominate():
    one_origin = [sig(i, "NEWS_REGIONAL", title="Mesma matéria da agência replicada", source=f"p{i}") for i in range(500)]
    few_independent = [sig(i, c) for i, c in enumerate(["NEWS_HIGH", "NEWS_REGIONAL", "OFFICIAL"])]
    assert conf(one_origin) < conf(few_independent)


def test_contradiction_stale_and_social_only_reduce_confidence():
    base = [sig(i, c) for i, c in enumerate(["NEWS_HIGH", "NEWS_REGIONAL", "NEWS_REGIONAL"])]
    assert conf(base, contradiction=1.0) < conf(base, contradiction=0.0)
    assert conf(base, coverage=0.4) < conf(base, coverage=1.0)
    assert conf(base, spam_ratio=0.8) < conf(base, spam_ratio=0.0)
    posts = [sig(i, "SOCIAL") for i in range(60)]
    assert conf(posts) <= 40


def test_official_denial_is_not_confirmation():
    claims = [sig(i, "NEWS_REGIONAL", title=f"Barragem rompe {WORDS[i]} e moradores fogem número {i}") for i in range(4)]
    denial = sig(50, "OFFICIAL", title="Defesa Civil nega rompimento de barragem", text="Não há rompimento; situação normal.", source="dc")
    confirm = sig(51, "OFFICIAL", title="Defesa Civil confirma rompimento de barragem e evacua moradores", source="dc")
    assert conf(claims + [confirm], contradiction=0.0) > conf(claims + [denial], contradiction=0.0)  # a negativa não soma os 25 pontos oficiais
    assert conf(claims + [denial]) < conf(claims + [confirm])  # e ainda é contradição registrada


def test_breakdown_always_sums_to_score_across_random_inputs():
    rnd = random.Random(13)
    for _ in range(40):
        sigs = [sig(i, rnd.choice(["NEWS_HIGH", "NEWS_REGIONAL", "SOCIAL", "OFFICIAL"])) for i in range(rnd.randint(1, 12))]
        score, bd = confidence_v2(sigs, contradiction=rnd.random(), spam_ratio=rnd.random() * 0.5, coverage=rnd.choice([None, 1.0, 0.6, 0.2, 0.0]))
        assert 0 <= score <= 100 and sum(b["points"] for b in bd) == score


# ---------------------------------------------------------------- perda gradual de cobertura
def assessments(alive, total=10):
    out = []
    for i in range(total):
        ok = i < alive
        r = SourceReading(f"s{i}", "ONLINE" if ok else "OFFLINE", True, (f"h{i}",) if ok else (), (NOW - timedelta(minutes=5),) if ok else ())
        out.append(assess({"source_class": "NEWS_HIGH"}, r, NOW))
    return out


@pytest.mark.parametrize("alive,ratio", [(10, 1.0), (8, 0.8), (6, 0.6), (4, 0.4), (2, 0.2), (0, 0.0)])
def test_gradual_sensor_loss_degrades_confidence_monotonically(alive, ratio):
    assert coverage_ratio(assessments(alive)) == ratio
    base = [sig(i, c) for i, c in enumerate(["NEWS_HIGH", "NEWS_REGIONAL", "OFFICIAL", "NEWS_REGIONAL"])]
    s = conf(base, coverage=coverage_ratio(assessments(alive)))
    full = conf(base, coverage=1.0)
    assert s <= full and (alive == 10) == (s == full)
    if alive == 0:
        assert s == 0  # nenhum sensor vivo: nenhuma confiança, nunca "calmaria"


def test_confidence_decreases_step_by_step_with_sensor_loss():
    base = [sig(i, c) for i, c in enumerate(["NEWS_HIGH", "NEWS_REGIONAL", "OFFICIAL", "NEWS_REGIONAL"])]
    series = [conf(base, coverage=coverage_ratio(assessments(a))) for a in (10, 8, 6, 4, 2, 0)]
    assert series == sorted(series, reverse=True) and series[0] > series[-1]


def test_unknown_stale_and_empty_are_lost_coverage_quiet_is_neutral():
    mix = [assess({"source_class": "NEWS_HIGH"}, SourceReading("a", "ONLINE", True, ("x",), (NOW - timedelta(minutes=5),)), NOW),
           assess({"source_class": "NEWS_HIGH"}, SourceReading("b", "ONLINE", True, ("y",), (NOW - timedelta(days=3),)), NOW),  # STALE
           assess({"source_class": "NEWS_HIGH"}, SourceReading("c", "DEGRADED", True, (), ()), NOW),  # EMPTY
           assess({"source_class": "NEWS_HIGH"}, SourceReading("d", "OFFLINE", True, (), ()), NOW),  # UNKNOWN
           assess({"source_class": "OFFICIAL", "quiet_ok": True}, SourceReading("e", "ONLINE", True, (), ()), NOW)]  # QUIET
    assert coverage_ratio(mix) == 0.25  # 1 FRESH de 4 esperadas; QUIET fora da conta
    assert coverage_ratio([mix[4]]) is None  # só fontes quietas: cobertura não se aplica (não é 0 nem 1)
    assert factor(None) == 1.0 and degrade(80, 0.25) == 40.0
    assert [view_state(r) for r in (None, 1.0, 0.7, 0.3, 0.1)] == ["NOT_APPLICABLE", "COMPLETE", "PARTIAL", "DEGRADED", "CRITICAL"]
    fam = by_family(mix, {"a": "NEWS", "b": "NEWS", "c": "NEWS", "d": "NEWS", "e": "OFFICIAL"})
    assert fam["NEWS"]["ratio"] == 0.25 and fam["OFFICIAL"]["state"] == "NOT_APPLICABLE"


def test_coverage_reaches_anomaly_and_sentinel():
    from pulso_engine.baseline import SeasonalBaseline
    from pulso_engine.intelligence.anomaly_v2 import anomaly_v2
    from pulso_engine.research.sentinel import Candidate, should_investigate

    base = SeasonalBaseline(16.8, 4.0, 14, "dow_hour", 14, (14, 18, 17, 15, 19, 17, 16, 18, 17, 16, 15, 17, 18, 16))
    full, partial = anomaly_v2(39, 15, base, 1.0), anomaly_v2(39, 15, base, 0.4)
    assert full["score"] == partial["score"] and partial["confidence"] < full["confidence"]  # score não é inventado; a confiança da medida cai
    assert partial["view"] == "DEGRADED" and full["view"] == "COMPLETE" and anomaly_v2(39, 15, base)["view"] == "NOT_APPLICABLE"
    c = Candidate("UF:MG", "WEATHER", 0.9, 5.0, "dow_hour", 12, 3, False, origin_count=6, independent_origins=5, coverage=0.3)
    go, reasons = should_investigate(c)
    assert go and reasons[-1] == "visão degradada: cobertura 30%"  # a explicação diz que a visão do mundo está degradada
    assert not any("degradada" in r for r in should_investigate(Candidate("UF:MG", "WEATHER", 0.9, 5.0, "dow_hour", 12, 3, False, origin_count=6, independent_origins=5, coverage=0.9))[1])
