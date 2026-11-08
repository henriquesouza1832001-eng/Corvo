"""Registro de previsões: o que uma previsão PRECISA ter para existir. Espelha as regras da API (apps/worker/src/routes/corvo.ts).

Regras do produto: toda previsão tem probabilidade, intervalo de incerteza, evidências E método; sem método ou sem evidência, não entra;
a probabilidade fica dentro do intervalo. Até 100 previsões resolvidas, tudo é EXPERIMENTAL.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN_RESOLVED_FOR_TRUST = 100
MAX_ECE_FOR_TRUST = 0.05
STATUSES = ("aberta", "calibrando", "resolvida")


class RegistryError(ValueError):
    """Previsão recusada: o motivo está na mensagem."""


@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    question: str
    probability: float
    interval_low: float
    interval_high: float
    evidences: int
    sources: int
    method: str
    horizon: str
    status: str = "calibrando"


def validate_record(r: ForecastRecord) -> ForecastRecord:
    """Levanta `RegistryError` se a previsão não puder ser publicada. Devolve o próprio registro se estiver ok."""
    if not r.forecast_id.strip() or not r.question.strip():
        raise RegistryError("identificador e pergunta são obrigatórios")
    if not r.method.strip():
        raise RegistryError("previsão sem método não entra")
    if r.evidences < 1 or r.sources < 1:
        raise RegistryError("previsão sem evidências não entra")
    for name, v in (("probabilidade", r.probability), ("limite inferior", r.interval_low), ("limite superior", r.interval_high)):
        if not 0.0 <= v <= 1.0:
            raise RegistryError(f"{name} fora de [0, 1]")
    if not r.interval_low <= r.probability <= r.interval_high:
        raise RegistryError("a probabilidade precisa estar dentro do intervalo de incerteza")
    if r.status not in STATUSES:
        raise RegistryError(f"estado inválido: {r.status}")
    return r


def forecast_status(n_resolved: int, ece_value: float | None) -> str:
    """EXPERIMENTAL até 100 resolvidas; depois CALIBRANDO até o erro de calibração ficar ≤ 0,05; então CONFIAVEL."""
    if n_resolved < MIN_RESOLVED_FOR_TRUST:
        return "EXPERIMENTAL"
    if ece_value is None or ece_value > MAX_ECE_FOR_TRUST:
        return "CALIBRANDO"
    return "CONFIAVEL"
