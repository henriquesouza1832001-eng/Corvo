"""Comparação de previsores em ordem temporal (walk-forward): BASE RATE x SEASONAL x ANOMALY ONLY x V1 x V2 RAW x V2 CALIBRATED.

Cada amostra: `{ts, outcome (0/1), predictions: {nome: probabilidade | None}, lead_minutes?}`; `None` = o modelo se absteve (abstenção NUNCA
entra como probabilidade nem como acerto). Os previsores de referência (taxa-base e sazonal por hora) são gerados aqui usando SÓ desfechos
ANTERIORES à amostra (sem vazamento). Sem amostra suficiente o relatório diz `INSUFFICIENT_DATA` e NÃO devolve nota: com 20 previsões
resolvidas e 0 positivos (produção em 2026-10-03) nada disto é conclusão. Nada aqui treina, ajusta limiar ou promove.
Usa `validation.metrics` (de outro dono) somente para leitura.
"""
from __future__ import annotations

from .baseline import BR_TZ
from .validation.metrics import base_rate_reference, brier, calibration_error, classification, lead_time_summary, log_loss

MIN_SAMPLES = 100
MIN_POSITIVES = 10
MIN_NEGATIVES = 10
CUTOFF = 0.5
MODELS = ("BASE_RATE", "SEASONAL", "ANOMALY_ONLY", "V1", "V2_RAW", "V2_CALIBRATED")
LAPLACE = 1.0
MIN_SAME_HOUR = 5


def with_reference_predictors(samples: list[dict]) -> list[dict]:
    """Acrescenta BASE_RATE e SEASONAL (taxa do mesmo horário local) calculadas SÓ com amostras anteriores no tempo."""
    out: list[dict] = []
    ordered = sorted(samples, key=lambda x: x["ts"])
    rate = lambda xs: (sum(p["outcome"] for p in xs) + LAPLACE) / (len(xs) + 2 * LAPLACE)  # noqa: E731
    for i, s in enumerate(ordered):
        past = [p for p in ordered[:i] if p["ts"] < s["ts"]]
        hour = s["ts"].astimezone(BR_TZ).hour
        same = [p for p in past if p["ts"].astimezone(BR_TZ).hour == hour]
        preds = {**s.get("predictions", {}), "BASE_RATE": rate(past), "SEASONAL": rate(same) if len(same) >= MIN_SAME_HOUR else rate(past)}
        out.append({**s, "predictions": preds})
    return out


def _rows(samples: list[dict], model: str) -> tuple[list[tuple[float, int]], int, int]:
    pairs, abstained, absent = [], 0, 0
    for s in samples:
        if model not in s.get("predictions", {}):
            absent += 1
        elif s["predictions"][model] is None:
            abstained += 1
        else:
            pairs.append((float(s["predictions"][model]), int(s["outcome"])))
    return pairs, abstained, absent


def evaluate(samples: list[dict], models: tuple[str, ...] = MODELS, days: float | None = None) -> dict:
    """Relatório por modelo. `days` (opcional) = duração da janela, para falsos alertas por dia."""
    n = len(samples)
    pos = sum(s["outcome"] for s in samples)
    base = {"N": n, "positives": pos, "negatives": n - pos}
    if n < MIN_SAMPLES or pos < MIN_POSITIVES or n - pos < MIN_NEGATIVES:
        return {**base, "status": "INSUFFICIENT_DATA", "reason": f"exige N>={MIN_SAMPLES}, positivos>={MIN_POSITIVES}, negativos>={MIN_NEGATIVES}", "models": {}}
    ref = base_rate_reference([s["outcome"] for s in samples])
    report = {}
    for m in models:
        pairs, abstained, absent = _rows(samples, m)
        if absent == n:
            continue
        mp = sum(o for _, o in pairs)
        if len(pairs) < MIN_SAMPLES or mp < MIN_POSITIVES or len(pairs) - mp < MIN_NEGATIVES:
            report[m] = {"status": "INSUFFICIENT_DATA", "N": len(pairs), "abstained": abstained, "coverage": round(len(pairs) / n, 4)}
            continue
        b = brier(pairs)
        fp_alerts = sum(1 for p, o in pairs if p >= CUTOFF and o == 0)
        leads = [s.get("lead_minutes") for s in samples if s.get("predictions", {}).get(m) is not None and s["predictions"][m] >= CUTOFF and s["outcome"] == 1]
        report[m] = {"status": "OK", "N": len(pairs), "positives": mp, "negatives": len(pairs) - mp, "brier": b,
                     "brier_skill": round(1 - b / ref, 4) if ref else None, "log_loss": log_loss(pairs), "ece": calibration_error(pairs),
                     **classification(pairs, CUTOFF), "false_alerts_per_day": round(fp_alerts / days, 3) if days else None,
                     "lead_time": lead_time_summary(leads), "coverage": round(len(pairs) / n, 4), "abstention_rate": round(abstained / n, 4)}
    return {**base, "status": "OK", "brier_reference": ref, "models": report}


def order_models(report: dict) -> list[str]:
    """Modelos com status OK por Brier crescente (menor é melhor). Só descreve; não escolhe nem promove nada."""
    ok = {m: r["brier"] for m, r in report.get("models", {}).items() if r.get("status") == "OK"}
    return sorted(ok, key=lambda m: (ok[m], m))


def beats_references(report: dict, model: str) -> bool | None:
    """True só se o modelo vence BASE_RATE E SEASONAL em Brier; None se faltar dado (nunca um "sim" por omissão)."""
    r = report.get("models", {})
    if any(r.get(k, {}).get("status") != "OK" for k in (model, "BASE_RATE", "SEASONAL")):
        return None
    return r[model]["brier"] < min(r["BASE_RATE"]["brier"], r["SEASONAL"]["brier"])
