"""Cobertura/ausência: consome o contrato de frescor da plataforma (`source_freshness`) e o propaga para confiança, anomalia,
Sentinela e previsão. Regras que nunca se quebram: UNKNOWN != 0, STALE != atual, EMPTY != normal, QUIET é neutro.

`coverage_ratio` = fontes FRESH / fontes que DEVERIAM falar (todas menos as QUIET). UNKNOWN (transporte falhou) e STALE contam como
cobertura PERDIDA; EMPTY também (feed sem itens válidos não é "sem ocorrências"). O fator aplicado à confiança é a raiz da razão:
suave, monótono e zero quando não há nenhum sensor vivo (100% -> 1,00; 80% -> 0,89; 60% -> 0,77; 40% -> 0,63; 20% -> 0,45; 0% -> 0).
"""
from __future__ import annotations

import math

FRESH, STALE, EMPTY, QUIET, UNKNOWN = "FRESH", "STALE", "EMPTY", "QUIET", "UNKNOWN"
LOW_COVERAGE = 0.5  # abaixo disto a visão do mundo é declarada DEGRADADA
CRITICAL_COVERAGE = 0.2  # abaixo disto não se prevê nem se afirma normalidade


def coverage_ratio(assessments: list[dict], source_ids: set[str] | None = None) -> float | None:
    """None quando não há nenhuma fonte esperada (todas QUIET ou lista vazia): cobertura NÃO se aplica, não é 0 nem 1."""
    rows = [a for a in assessments if source_ids is None or a["source_id"] in source_ids]
    expected = [a for a in rows if a["freshness"]["state"] != QUIET]
    if not expected:
        return None
    return round(sum(1 for a in expected if a["freshness"]["state"] == FRESH) / len(expected), 4)


def factor(ratio: float | None) -> float:
    """Multiplicador (0-1) da confiança. None = cobertura desconhecida: não degrada (nem finge que está tudo bem: o chamador registra)."""
    if ratio is None:
        return 1.0
    return round(math.sqrt(max(0.0, min(1.0, ratio))), 4)


def degrade(confidence: float, ratio: float | None) -> float:
    return round(confidence * factor(ratio), 2)


def view_state(ratio: float | None) -> str:
    """COMPLETE | PARTIAL | DEGRADED | CRITICAL | NOT_APPLICABLE: como o sistema deve rotular a PRÓPRIA visão do mundo."""
    if ratio is None:
        return "NOT_APPLICABLE"
    return "CRITICAL" if ratio < CRITICAL_COVERAGE else "DEGRADED" if ratio < LOW_COVERAGE else "PARTIAL" if ratio < 0.9 else "COMPLETE"


def by_family(assessments: list[dict], families: dict[str, str]) -> dict[str, dict]:
    """Razão e estado da visão por família (classe de fonte): para o painel e para o `engine-status`."""
    out = {}
    for fam in sorted(set(families.values())):
        ids = {sid for sid, f in families.items() if f == fam}
        r = coverage_ratio(assessments, ids)
        out[fam] = {"ratio": r, "state": view_state(r), "sources": len([a for a in assessments if a["source_id"] in ids])}
    return out
