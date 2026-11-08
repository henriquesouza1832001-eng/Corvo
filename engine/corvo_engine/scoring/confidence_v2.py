"""Confiança V2 (0-100), explicável, com `publisher != origin`: cem portais copiando a mesma matéria são UMA origem.

Parte dos sinais do evento (não só de `EventStats`): agrupa republicações por semelhança de título (mesma lógica do
validador do Sentinela), conta origens independentes e tipos de sensor, soma confirmação oficial e consistências e subtrai
contradição, cópias e spam. Devolve score E lista de pontos (soma = score). Social isolado nunca passa de 40. Severidade é
OUTRA coisa e não entra aqui. Atrás da flag `CONFIDENCE_V2`; o V1 (`confidence.py`) não é alterado.
"""
from __future__ import annotations

from ..models import SOCIAL_CLASSES, Signal
from ..intelligence.coverage import factor as coverage_factor
from ..research.validator import _origins, find_contradictions, is_denial, official_denials

SOCIAL_ONLY_CAP = 40
BASE = 10


def confidence_v2(signals: list[Signal], contradiction: float | None = None, spam_ratio: float = 0.0, coverage: float | None = None) -> tuple[int, list[dict]]:
    if not signals:
        return 0, []
    groups = _origins(signals)
    social_groups = sum(1 for g in groups if all(s.source_class in SOCIAL_CLASSES for s in g))
    origins = len(groups) - social_groups  # ORIGENS NÃO sociais (publishers != origens; rede social é sensor, não confirmação)
    # Tipos de sensor e confirmação oficial contam as ORIGENS (o sinal mais antigo de cada grupo; empate favorece o oficial), não as cópias:
    # uma cópia publicada por outra CLASSE de fonte não é um novo sensor.
    reps = [min(g, key=lambda x: (x.timestamp, x.source_class != "OFFICIAL")) for g in groups]
    classes = {s.source_class for s in reps}
    if contradiction is None:  # contradição detectada pelos próprios sinais (pares de afirmações incompatíveis + negativa oficial)
        contradiction = min(1.0, (len(find_contradictions(signals)) + len(official_denials(signals))) / 2)
    official = any(s.source_class == "OFFICIAL" and not is_denial(s) for s in reps)  # negativa oficial NÃO é confirmação
    copies = len(signals) - len(groups)
    states = {s.state for s in signals if s.state}
    geo_consistent = len(states) <= 1
    items = [
        ("base", "Base", float(BASE)),
        ("origins", "Origens independentes (cópias não contam)", float(min(30, 10 * max(0, origins - 1)))),
        ("social", "Origens em rede social (sensor, não confirmação)", float(min(6, 2 * social_groups))),
        ("sensors", "Tipos de sensor diferentes", float(min(20, 7 * max(0, len(classes) - 1)))),
        ("official", "Confirmação oficial", 25.0 if official else 0.0),
        ("geo", "Consistência geográfica", 10.0 if geo_consistent else 3.0),
        ("temporal", "Consistência temporal", 5.0 if len(signals) > 1 else 2.5),
        ("contradiction", "Contradições registradas", -30.0 * max(0.0, min(1.0, contradiction))),
        ("copies", "Republicações", -20.0 * (copies / len(signals))),
        ("spam", "Spam/bots", -20.0 * max(0.0, min(1.0, spam_ratio))),
    ]
    raw = max(0.0, min(100.0, sum(v for _, _, v in items)))
    # Cobertura de sensores (frescor): sensor offline/parado/vazio é visão perdida, não "calmaria". Reduz a confiança de forma monótona.
    cov_loss = raw * (1 - coverage_factor(coverage))
    if cov_loss:
        items.append(("coverage", "Cobertura de sensores degradada", -cov_loss))
        raw -= cov_loss
    cap = SOCIAL_ONLY_CAP if classes and classes <= SOCIAL_CLASSES else 100
    total = round(min(raw, cap))
    breakdown = [{"key": k, "label": label, "points": round(v)} for k, label, v in items if round(v) != 0]
    if total < round(raw):
        breakdown.append({"key": "social_cap", "label": "Só rede social: teto de confiança", "points": total - round(raw)})
    # arredondamentos individuais podem diferir em 1-2 pontos da soma: o último item absorve a diferença, a soma = score
    diff = total - sum(b["points"] for b in breakdown)
    if diff and breakdown:
        breakdown[-1] = {**breakdown[-1], "points": breakdown[-1]["points"] + diff}
    return total, breakdown
