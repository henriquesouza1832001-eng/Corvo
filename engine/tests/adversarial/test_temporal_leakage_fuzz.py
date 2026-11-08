"""Vazamento temporal: PROPRIEDADE central = nenhuma informação posterior ao cutoff altera o que o motor calcula no cutoff.

Fuzz com semente fixa: gera sinais com timestamps embaralhados em torno do cutoff (publicado/coletado antes e depois) e linhas de
observação/pontos do Pulso futuros, e confere que a saída no cutoff é IDÊNTICA com e sem os dados do futuro. Campos cobertos aqui:
`timestamp` (publicação), `collected_at` (fetch), hora de observação (`signal_observations.hour`) e pontos do Pulso. Os demais
(`event_time`, `confirmed_at`, `resolved_at`...) são do replay do Codex (`tests/reliability/test_data_leakage.py`).
"""
import random
from datetime import datetime, timedelta, timezone

import pytest

from pulso_engine.baseline import seasonal_baseline
from pulso_engine.forecast_v2 import hour_deltas
from pulso_engine.forecast_v2_features import build_snapshot
from pulso_engine.intelligence.baseline_hierarchy import resolve_baseline
from pulso_engine.models import Signal
from pulso_engine.research.sentinel import detect_candidates

CUTOFF = datetime(2026, 10, 7, 21, 0, tzinfo=timezone.utc)
SEEDS = list(range(12))


def rand_signal(rnd, i, future):
    """`future`: True = publicado depois do corte OU coletado depois do corte (os dois vazamentos possíveis)."""
    if future:
        pub = CUTOFF + timedelta(minutes=rnd.randint(1, 600)) if rnd.random() < 0.5 else CUTOFF - timedelta(minutes=rnd.randint(1, 120))
        col = max(pub, CUTOFF) + timedelta(seconds=rnd.randint(1, 3600)) if pub <= CUTOFF else pub + timedelta(seconds=rnd.randint(0, 60))
    else:
        pub = CUTOFF - timedelta(minutes=rnd.randint(0, 180))
        col = min(CUTOFF, pub + timedelta(seconds=rnd.randint(0, 600)))
    return Signal(signal_id=str(i), source_id=f"s{rnd.randint(0, 9)}", source_class=rnd.choice(["NEWS_HIGH", "NEWS_REGIONAL", "SOCIAL", "OFFICIAL"]),
                  timestamp=pub, collected_at=col, title=f"Notícia {i} sobre alagamento no bairro {rnd.randint(0, 99)} {rnd.choice(['norte', 'sul', 'leste'])}",
                  category="WEATHER", hash=f"h{i}", state="MG")


def population(seed):
    rnd = random.Random(seed)
    past = [rand_signal(rnd, i, False) for i in range(rnd.randint(5, 60))]
    future = [rand_signal(rnd, 1000 + i, True) for i in range(rnd.randint(1, 60))]
    assert all(s.timestamp > CUTOFF or s.collected_at > CUTOFF for s in future)
    return past, future


def hist(per_hour=4, days=35, beyond_hours=0):
    rows, end = [], CUTOFF.replace(minute=0)
    for h in range(-beyond_hours, 24 * days):
        t = end - timedelta(hours=h)
        rows.append({"scope": "UF:MG", "category": "WEATHER", "source_class": "NEWS_HIGH", "hour": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "signals": per_hour,
                     "sources": 2, "duplicates": 0})
    return rows


def snap_content(sigs):
    s = build_snapshot(sigs, CUTOFF, "UF:MG", "WEATHER", hist(), "FLOOD")
    c = s.content()
    c.pop("excluded_future")  # o número excluído é DECLARADO e naturalmente muda; o resto do snapshot não pode mudar
    return c, s.excluded_future


@pytest.mark.parametrize("seed", SEEDS)
def test_snapshot_ignores_signals_published_or_collected_after_the_cutoff(seed):
    past, future = population(seed)
    a, ex_a = snap_content(past)
    b, ex_b = snap_content(past + future)
    assert a == b and ex_a == 0 and ex_b == len(future)  # idêntico; e o que foi barrado é contado, não escondido


@pytest.mark.parametrize("seed", SEEDS)
def test_sentinel_candidates_ignore_the_future_including_late_collection(seed):
    past, future = population(seed)
    rows = hist()
    strip = lambda cs: [(c.scope, c.category, c.score, c.signal_count, c.origin_count, c.source_type_count) for c in cs]  # noqa: E731
    assert strip(detect_candidates(past, rows, CUTOFF)) == strip(detect_candidates(past + future, rows, CUTOFF))


def test_baselines_ignore_observation_hours_at_or_after_the_cutoff():
    clean = hist()
    leaky = hist() + [{**r, "hour": (CUTOFF.replace(minute=0) + timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M:%SZ"), "signals": 500}
                      for k, r in enumerate(clean[:48])]  # linhas com hora >= a do corte, com valores absurdos
    for fn in (lambda r: seasonal_baseline(r, "UF:MG", "WEATHER", CUTOFF), lambda r: resolve_baseline(r, "UF:MG", "WEATHER", CUTOFF).base):
        a, b = fn(clean), fn(leaky)
        assert (a.mean, a.std, a.samples, a.basis) == (b.mean, b.std, b.samples, b.basis)


def test_pulse_points_after_the_forecast_instant_never_enter_the_v2_deltas():
    pts, t = [], CUTOFF - timedelta(days=5)
    while t <= CUTOFF:
        pts.append({"timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "score": 10})
        t += timedelta(minutes=10)
    future = [{"timestamp": (CUTOFF + timedelta(minutes=10 * k)).strftime("%Y-%m-%dT%H:%M:%SZ"), "score": 99} for k in range(1, 40)]
    assert hour_deltas(pts, CUTOFF) == hour_deltas(pts + future, CUTOFF)
    assert 89.0 not in hour_deltas(pts + future, CUTOFF)  # 99 - 10 nunca aparece


def test_a_signal_collected_after_the_cutoff_is_reported_not_silently_used():
    s = Signal(signal_id="x", source_id="a", source_class="NEWS_HIGH", timestamp=CUTOFF - timedelta(minutes=1), collected_at=CUTOFF + timedelta(minutes=5),
               title="Alagamento no centro", category="WEATHER", hash="x", state="MG")
    snap = build_snapshot([s], CUTOFF, "UF:MG", "WEATHER", hist())
    assert snap.excluded_future == 1 and snap.features["signals_15m"].state == "UNAVAILABLE"  # sem dado visível: ausência explícita, não zero
