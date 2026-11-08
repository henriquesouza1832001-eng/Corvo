"""MUNIN (memória) do CORVO: guarda, esquece, registra previsões, confere e calibra.

Tudo aqui é puro Python, determinístico e sem rede: são as REGRAS e as CONTAS que o resto do sistema precisa obedecer. Ainda não há
previsão publicada em produção; este pacote é a bancada de prova (testada com dados sintéticos) e o contrato do que "certo" significa.
Ver docs/corvo/HUGIN_MUNIN_TREINO.md.
"""
from .leakage import LeakageError, as_of_view, check_resolution_after
from .registry import ForecastRecord, RegistryError, forecast_status, validate_record
from .retention import RETAIN_HASH_HOURS, RETAIN_NEWS_DAYS, RETAIN_STATS_DAYS, ALLOWED_NEWS_FIELDS, storable_payload
from .scoring import abstention_rate, base_rate_brier, brier, bin_interval_coverage, calibration_table, ece, skill

__all__ = [
    "ALLOWED_NEWS_FIELDS", "ForecastRecord", "LeakageError", "RETAIN_HASH_HOURS", "RETAIN_NEWS_DAYS", "RETAIN_STATS_DAYS",
    "RegistryError", "abstention_rate", "as_of_view", "base_rate_brier", "bin_interval_coverage", "brier", "calibration_table",
    "check_resolution_after", "ece", "forecast_status", "skill", "storable_payload", "validate_record",
]
