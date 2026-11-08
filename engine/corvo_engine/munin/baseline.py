"""Previsão pela TAXA-BASE (v1): a régua mínima de qualquer previsão do CORVO.

Para cada chave (tema, ativo, direção da pergunta, horizonte), guarda quantas vezes a resposta foi "sim" e "não". A probabilidade é a média de uma distribuição beta com prior fraco (1, 1): p = (sim + 1) / (sim + não + 2). O intervalo de incerteza usa aproximação normal da posterior Beta para formar um intervalo central aproximado de 80%; não são quantis Beta exatos e encolhe com mais dados.
Com menos de `min_n` casos o modelo SE ABSTÉM ("dados insuficientes"): dizer "não sei" é resposta válida.

Conte EVENTOS, nunca notícias: seis matérias sobre o mesmo fato são uma amostra só (ver docs/corvo/PREDITIVO.md, seção 4.1). Janelas de preço sobrepostas na mesma chave não contam como observações independentes.
Só passe disto para um modelo com características se ele BATER esta régua no conjunto lacrado, dividido no tempo.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .registry import ForecastRecord, validate_record

METHOD = "taxa-base por tema, ativo e horizonte (beta-binomial v1)"
Z80 = 1.2816  # approximate central 80% normal quantile
MIN_N = 30


@dataclass(frozen=True)
class Prediction:
    key: tuple[str, str, str]
    probability: float
    interval_low: float
    interval_high: float
    n: int
    yes: int


class BaseRateModel:
    """Contagens de sim/não por chave. Sem estado escondido: o que entrou é o que a previsão usa."""

    def __init__(self, min_n: int = MIN_N, prior_yes: float = 1.0, prior_no: float = 1.0) -> None:
        if min_n < 1 or prior_yes <= 0 or prior_no <= 0:
            raise ValueError("min_n >= 1 e priors positivos")
        self.min_n, self.prior_yes, self.prior_no = min_n, prior_yes, prior_no
        self._counts: dict[tuple[str, str, str], list[int]] = {}

    def update(self, key: tuple[str, str, str], hit: bool) -> None:
        """Registra o resultado de UM evento resolvido (nunca de uma notícia repetida)."""
        c = self._counts.setdefault(key, [0, 0])
        c[0 if hit else 1] += 1

    def n(self, key: tuple[str, str, str]) -> int:
        c = self._counts.get(key)
        return 0 if c is None else c[0] + c[1]

    def predict(self, key: tuple[str, str, str]) -> Prediction | None:
        """None = dados insuficientes; caso contrário, probabilidade com intervalo central Beta aproximado por normal (80%)."""
        c = self._counts.get(key, [0, 0])
        n = c[0] + c[1]
        if n < self.min_n:
            return None
        a, b = c[0] + self.prior_yes, c[1] + self.prior_no
        mean = a / (a + b)
        sd = sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
        lo, hi = max(0.0, mean - Z80 * sd), min(1.0, mean + Z80 * sd)
        return Prediction(key, round(mean, 4), round(lo, 4), round(hi, 4), n, c[0])


def to_record(pred: Prediction, question: str, sources: int, horizon: str, forecast_id: str | None = None) -> ForecastRecord:
    """Transforma a previsão no registro publicável. Passa pelo mesmo validador que a API: sem método ou evidência, não existe."""
    rec = ForecastRecord(
        forecast_id=forecast_id or "-".join(pred.key),
        question=question,
        probability=pred.probability,
        interval_low=pred.interval_low,
        interval_high=pred.interval_high,
        evidences=pred.n,
        sources=sources,
        method=METHOD,
        horizon=horizon,
        status="calibrando",
    )
    return validate_record(rec)
