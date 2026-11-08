"""Critérios de PROMOÇÃO do Geo V2 (separados de qualquer melhora de corpus): o gate decide, não a impressão de que melhorou.

Entrada: métricas de `tests/adversarial/geo_torture.metrics` para V1 e V2 (mesmo corpus). Saída: aprovado/reprovado com TODOS os motivos.
Mesmo aprovado em corpus sintético, a promoção exige também (BLOCKED_EXTERNAL) revisão humana dos rótulos e amostra histórica real.
Princípio: estado correto é melhor do que cidade inventada.
"""
from __future__ import annotations

MAX_FALSE_PRECISION_ALL = 0.01  # cidade errada/inventada sobre TODOS os casos
MAX_FALSE_PRECISION_OF_REPORTED = 0.05  # e sobre as cidades que ele de fato informou
MIN_CITY_GAIN = 0.10  # acertos de cidade pelo menos 10% acima do V1
MAX_GROUP_FALSE_PRECISION = 0.10  # nenhum grupo (homônimo, palavra comum, bairro...) pode passar disto
MIN_CASES = 150


def promotion_gate(v1: dict, v2: dict) -> dict:
    reasons: list[str] = []
    if v2["n"] < MIN_CASES:
        reasons.append(f"corpus pequeno ({v2['n']} < {MIN_CASES} casos)")
    if v2["false_precision_rate"] > min(MAX_FALSE_PRECISION_ALL, v1["false_precision_rate"]):
        reasons.append(f"false_precision {v2['false_precision_rate']:.3f} > min({MAX_FALSE_PRECISION_ALL}, V1 {v1['false_precision_rate']:.3f})")
    if v2["false_precision_rate_of_reported"] > MAX_FALSE_PRECISION_OF_REPORTED:
        reasons.append(f"false_precision das cidades informadas {v2['false_precision_rate_of_reported']:.3f} > {MAX_FALSE_PRECISION_OF_REPORTED}")
    if v1["city_correct"] and v2["city_correct"] < v1["city_correct"] * (1 + MIN_CITY_GAIN):
        reasons.append(f"ganho de cidades corretas insuficiente ({v1['city_correct']} -> {v2['city_correct']}, exigido +{MIN_CITY_GAIN:.0%})")
    if v2["wrong_or_invented_state"] > v1["wrong_or_invented_state"]:
        reasons.append("estado errado/inventado pior que o V1")
    bad = sorted(g for g, x in v2["by_group"].items() if x["n"] and x["false_precision"] / x["n"] > MAX_GROUP_FALSE_PRECISION)
    if bad:
        reasons.append("grupos acima do teto de falsa precisão: " + ", ".join(bad))
    return {"passed": not reasons, "reasons": reasons, "external_blockers": ["revisão humana dos rótulos do corpus", "amostra histórica real (>= 500 manchetes)"]}
