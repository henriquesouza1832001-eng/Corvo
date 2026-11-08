"""Harness de comparação de previsores: sem vazamento, sem nota quando falta amostra, abstenção nunca vira acerto."""
import random
from datetime import datetime, timedelta, timezone

from pulso_engine.forecast_eval import MIN_SAMPLES, beats_references, evaluate, order_models, with_reference_predictors

T0 = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
BRT = timezone(timedelta(hours=-3))


def make(n, rate_by_hour=lambda h: 0.2, seed=5):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        ts = T0 + timedelta(hours=i)
        p_true = rate_by_hour(ts.astimezone(BRT).hour)
        o = int(rnd.random() < p_true)
        clip = lambda p: min(0.95, max(0.02, p))  # noqa: E731
        out.append({"ts": ts, "outcome": o, "lead_minutes": 30 if o else None,
                    "predictions": {"V1": 0.5, "V2_RAW": clip(p_true), "V2_CALIBRATED": None if i % 5 == 0 else clip(p_true), "ANOMALY_ONLY": 0.3}})
    return out


CYCLE = lambda h: 0.7 if 15 <= h <= 20 else 0.05  # noqa: E731


def test_insufficient_data_returns_no_grade():
    r = evaluate(with_reference_predictors(make(50)))
    assert r["status"] == "INSUFFICIENT_DATA" and r["models"] == {} and "N>=" in r["reason"]
    zero_pos = [{**s, "outcome": 0} for s in make(300)]
    assert evaluate(with_reference_predictors(zero_pos))["status"] == "INSUFFICIENT_DATA"  # a produção de hoje: 20 resolvidas, 0 positivos


def test_reference_predictors_use_only_the_past():
    s = make(300)
    base = {x["ts"]: x["predictions"] for x in with_reference_predictors(s)}
    cut = T0 + timedelta(hours=200)
    flipped = [dict(x, outcome=1 - x["outcome"]) if x["ts"] >= cut else x for x in s]  # muda SÓ o futuro
    other = {x["ts"]: x["predictions"] for x in with_reference_predictors(flipped)}
    for ts in base:
        if ts <= cut:  # a previsão em t só vê desfechos ANTERIORES a t: mudar t e depois não a afeta
            assert base[ts]["BASE_RATE"] == other[ts]["BASE_RATE"] and base[ts]["SEASONAL"] == other[ts]["SEASONAL"]


def test_seasonal_beats_base_rate_with_a_daily_cycle_and_report_has_all_metrics():
    r = evaluate(with_reference_predictors(make(1500, CYCLE)), days=1500 / 24)
    assert r["status"] == "OK" and r["N"] == 1500
    m = r["models"]
    assert m["SEASONAL"]["brier"] < m["BASE_RATE"]["brier"] and m["V2_RAW"]["brier"] < m["V1"]["brier"]
    for k in ("brier", "brier_skill", "log_loss", "ece", "precision", "recall", "fpr", "false_alerts_per_day", "lead_time", "coverage", "abstention_rate"):
        assert k in m["V2_RAW"]
    assert order_models(r)[0] in ("V2_RAW", "V2_CALIBRATED")


def test_abstention_is_neither_a_prediction_nor_a_hit():
    r = evaluate(with_reference_predictors(make(1500, lambda h: 0.3)))
    c = r["models"]["V2_CALIBRATED"]
    assert c["abstention_rate"] == 0.2 and c["coverage"] == 0.8 and c["N"] == 1200
    assert r["models"]["V2_RAW"]["coverage"] == 1.0


def test_model_that_does_not_beat_both_references_is_not_called_better():
    r = evaluate(with_reference_predictors(make(1500, CYCLE)))
    assert beats_references(r, "V1") is False  # 0,5 constante não vence taxa-base/sazonal
    assert beats_references(r, "NOPE") is None  # faltou dado: None, nunca "sim" por omissão
    assert beats_references(evaluate(with_reference_predictors(make(20))), "V2_RAW") is None


def test_model_with_only_abstentions_is_flagged_per_model():
    s = with_reference_predictors(make(MIN_SAMPLES + 150, lambda h: 0.3))
    for x in s:
        x["predictions"]["V2_CALIBRATED"] = None
    r = evaluate(s)
    assert r["status"] == "OK" and r["models"]["V2_CALIBRATED"]["status"] == "INSUFFICIENT_DATA"
