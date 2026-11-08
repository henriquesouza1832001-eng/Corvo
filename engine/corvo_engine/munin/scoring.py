"""Contas de Munin: quanto uma previsão probabilística vale. Sem dependências; tudo recebe listas simples.

`ps` = probabilidades previstas (0-1), `ys` = resultados (0 ou 1). Previsão sem resultado ainda não entra aqui.
A régua mínima de qualquer previsão é a TAXA-BASE (prever sempre a frequência histórica): quem não a bate não vale nada.
"""
from __future__ import annotations

from dataclasses import dataclass


def _check(ps, ys) -> None:
    if len(ps) != len(ys):
        raise ValueError("ps e ys precisam ter o mesmo tamanho")
    if not ps:
        raise ValueError("sem previsões resolvidas")
    if any(not 0.0 <= p <= 1.0 for p in ps):
        raise ValueError("probabilidade fora de [0, 1]")
    if any(y not in (0, 1) for y in ys):
        raise ValueError("resultado precisa ser 0 ou 1")


def brier(ps: list[float], ys: list[int]) -> float:
    """Erro quadrático médio da probabilidade (0 = perfeito, 0,25 = sempre dizer 50%)."""
    _check(ps, ys)
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def base_rate_brier(ys: list[int], base_rate: float | None = None) -> float:
    """Brier de quem prevê sempre a taxa-base. Passe `base_rate` de um período ANTERIOR para não olhar o futuro."""
    if not ys:
        raise ValueError("sem resultados")
    r = sum(ys) / len(ys) if base_rate is None else base_rate
    return sum((r - y) ** 2 for y in ys) / len(ys)


def skill(ps: list[float], ys: list[int], base_rate: float | None = None) -> float | None:
    """Ganho sobre a taxa-base: 1 - Brier/Brier_base. <= 0 = inútil. None se a taxa-base já é perfeita (resultado constante)."""
    b0 = base_rate_brier(ys, base_rate)
    if b0 == 0:
        return None
    return 1.0 - brier(ps, ys) / b0


@dataclass(frozen=True)
class Bin:
    lo: float
    hi: float
    n: int
    mean_p: float
    freq: float


def calibration_table(ps: list[float], ys: list[int], bins: int = 10) -> list[Bin]:
    """Faixas de confiança declarada contra frequência real ("quando digo 70%, acontece 70%?")."""
    _check(ps, ys)
    out: list[Bin] = []
    for k in range(bins):
        lo, hi = k / bins, (k + 1) / bins
        idx = [i for i, p in enumerate(ps) if (lo <= p < hi) or (k == bins - 1 and p == 1.0)]
        if idx:
            out.append(Bin(lo, hi, len(idx), sum(ps[i] for i in idx) / len(idx), sum(ys[i] for i in idx) / len(idx)))
    return out


def ece(ps: list[float], ys: list[int], bins: int = 10) -> float:
    """Erro de calibração esperado: média ponderada de |confiança - frequência| por faixa (0 = calibrado)."""
    n = len(ps)
    return sum(b.n / n * abs(b.mean_p - b.freq) for b in calibration_table(ps, ys, bins))


def bin_interval_coverage(ps: list[float], ys: list[int], los: list[float], his: list[float], bins: int = 5) -> float:
    """Fração das faixas em que a frequência real cai dentro do intervalo de incerteza médio declarado (incerteza honesta)."""
    _check(ps, ys)
    hit, total = 0, 0
    for k in range(bins):
        lo_b, hi_b = k / bins, (k + 1) / bins
        idx = [i for i, p in enumerate(ps) if (lo_b <= p < hi_b) or (k == bins - 1 and p == 1.0)]
        if len(idx) < 5:  # faixa com pouca amostra não julga nada
            continue
        freq = sum(ys[i] for i in idx) / len(idx)
        mlo, mhi = sum(los[i] for i in idx) / len(idx), sum(his[i] for i in idx) / len(idx)
        total += 1
        hit += mlo <= freq <= mhi
    return hit / total if total else float("nan")


def abstention_rate(n_abstained: int, n_total: int) -> float:
    """Fração de casos em que o CORVO disse "não sei" (INSUFFICIENT_DATA). Dizer "não sei" é resposta válida."""
    if n_total <= 0:
        raise ValueError("n_total precisa ser positivo")
    return n_abstained / n_total
