"""Baseline hierárquico: a MELHOR base disponível, com o fallback sempre visível.

Ordem (do mais específico ao mais geral):
 1. `dow_hour`        escopo x categoria x hora x dia da semana (>= 3 amostras comparáveis)
 2. `hour`            escopo x categoria x hora (>= 5)
 3. `all_hours`       escopo x categoria, todas as horas dos últimos 7 dias (>= 24 horas com dado)
 4. `national_scaled` BR x categoria (níveis 1-3 do Brasil) ESCALADO pela fatia histórica do estado (soma do estado / soma do Brasil)
 5. INSUFFICIENT      nada confiável: o sistema não afirma o que é "normal"
O nível MUNICÍPIO não existe: `signal_observations` só guarda BR e UF (decisão de custo do banco). Isto fica declarado em `levels_unavailable`
e nunca é simulado com o estado. Cada resultado carrega escopo usado, nível, tamanho da amostra, hora e dia da semana (efetivo, com
feriado), base de sazonalidade e uma CONFIABILIDADE 0-1. Nada de fallback silencioso.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..baseline import BR_TZ, INSUFFICIENT, MIN_DATA_HOURS, SeasonalBaseline, _mean_std, seasonal_hourly
from .context_engine import contextual_baseline, effective_weekday

LEVELS = ("dow_hour", "hour", "all_hours", "national_scaled")
MIN_ALL_HOURS = 24
RECENT_DAYS = 7
RELIABILITY_BASE = {"dow_hour": 1.0, "hour": 0.7, "all_hours": 0.4, "national_scaled": 0.3}
SAMPLES_FOR_FULL = {"dow_hour": 4, "hour": 7, "all_hours": 168, "national_scaled": 168}  # amostras para a confiabilidade cheia do nível (1 semana de dias/horas)


@dataclass(frozen=True)
class ResolvedBaseline:
    base: SeasonalBaseline  # mesma superfície mean/std/valid que `anomaly` usa; `basis` = nível
    scope_used: str
    level: str  # um de LEVELS ou "insufficient"
    sample_size: int
    hour: int  # hora local de Brasília
    weekday: int  # dia da semana efetivo (feriado = 6)
    seasonality: str  # "weekday_hour" | "hour_only" | "none"
    reliability: float  # 0-1: nível x amostra
    scale: float  # 1.0, ou a fatia do estado no Brasil (national_scaled)
    levels_unavailable: tuple[str, ...] = ("city",)

    @property
    def valid(self) -> bool:
        return self.base.valid

    def describe(self) -> dict:
        return {"scope_used": self.scope_used, "fallback_level": self.level, "sample_size": self.sample_size, "hour": self.hour, "weekday": self.weekday,
                "seasonality": self.seasonality, "reliability": self.reliability, "scale": self.scale, "levels_unavailable": list(self.levels_unavailable)}


def _reliability(level: str, n: int) -> float:
    return round(RELIABILITY_BASE.get(level, 0.0) * min(1.0, n / SAMPLES_FOR_FULL.get(level, 1)), 3)


def _recent_all_hours(rows: list[dict], scope: str, category: str, at: datetime) -> tuple[float, float, tuple[int, ...]] | None:
    series = seasonal_hourly(rows, scope, category, at, lookback_h=RECENT_DAYS * 24)
    vals = [v for v in series.values()]
    if sum(1 for v in vals if v > 0) < MIN_ALL_HOURS or len(vals) < MIN_ALL_HOURS:
        return None
    mean, std = _mean_std(vals)
    return mean, std, tuple(vals)


def _share(rows: list[dict], scope: str, category: str, at: datetime) -> float | None:
    """Fatia histórica do estado na categoria: soma(UF) / soma(BR) nas últimas 4 semanas. None sem BR ou sem UF."""
    uf = sum(v for v in seasonal_hourly(rows, scope, category, at).values())
    br = sum(v for v in seasonal_hourly(rows, "BR", category, at).values())
    return round(uf / br, 4) if uf > 0 and br > 0 else None


def resolve_baseline(rows: list[dict], scope: str, category: str, at: datetime, holidays: dict[date, str] | None = None) -> ResolvedBaseline:
    local = at.astimezone(BR_TZ)
    wd = effective_weekday(at, holidays or {})
    meta = dict(hour=local.hour, weekday=wd)

    def tier(sc: str) -> tuple[SeasonalBaseline, str] | None:
        b = contextual_baseline(rows, sc, category, at, holidays or {})
        return (b, b.basis) if b.valid else None

    hit = tier(scope)
    if hit:
        b, level = hit
        return ResolvedBaseline(b, scope, level, b.samples, seasonality="weekday_hour" if level == "dow_hour" else "hour_only",
                                reliability=_reliability(level, b.samples), scale=1.0, **meta)
    flat = _recent_all_hours(rows, scope, category, at)
    if flat:
        mean, std, vals = flat
        b = SeasonalBaseline(mean, std, len(vals), "all_hours", sum(1 for v in vals if v > 0), vals)
        return ResolvedBaseline(b, scope, "all_hours", len(vals), seasonality="none", reliability=_reliability("all_hours", len(vals)), scale=1.0, **meta)
    if scope != "BR":
        share = _share(rows, scope, category, at)
        nat = contextual_baseline(rows, "BR", category, at, holidays or {})
        if share and nat.valid:
            vals = tuple(round(v * share) for v in nat.values)
            b = SeasonalBaseline(nat.mean * share, nat.std * share, nat.samples, "national_scaled", nat.data_hours, vals)
            return ResolvedBaseline(b, "BR", "national_scaled", nat.samples, seasonality="weekday_hour" if nat.basis == "dow_hour" else "hour_only",
                                    reliability=_reliability("national_scaled", nat.samples), scale=share, **meta)
    return ResolvedBaseline(INSUFFICIENT, scope, "insufficient", 0, seasonality="none", reliability=0.0, scale=1.0, **meta)


def ladder_gaps() -> tuple[str, ...]:
    """Níveis desejados pelo desenho que ainda não existem (para o relatório de maturidade)."""
    return ("city",)


__all__ = ["LEVELS", "ResolvedBaseline", "resolve_baseline", "ladder_gaps", "MIN_DATA_HOURS", "timedelta"]
