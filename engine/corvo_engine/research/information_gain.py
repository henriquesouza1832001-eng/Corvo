"""Ganho de informação: "qual observação FALTANTE mais reduziria nossa incerteza sobre esta investigação?" (determinístico, explicável).

Não é uma probabilidade nem um modelo treinado: é uma ORDENAÇÃO por heurística declarada. Cada ação pontua `peso x lacuna` onde a lacuna
(0-1) mede o quanto aquela dimensão da evidência ainda está em aberto; ações sem lacuna não aparecem. Nenhuma ação fabrica certeza ou
consulta nada sozinha: o Sentinela só SUGERE o que investigar (fonte oficial, sensor físico, segunda origem, geolocalização, contradição).
Sem LLM.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..intelligence.signatures import load_signatures
from ..models import Signal
from .provenance import provenance
from .validator import Validation

# peso de cada dimensão (hipóteses de partida, a serem medidas por ablation; registradas em `WEIGHTS` para auditoria)
WEIGHTS = {"RESOLVE_CONTRADICTION": 1.0, "CHECK_OFFICIAL_SOURCE": 0.9, "CHECK_PHYSICAL_SENSOR": 0.8, "FIND_INDEPENDENT_ORIGIN": 0.7, "RESOLVE_GEOLOCATION": 0.5}
PHYSICAL_TYPES = frozenset({"rainfall", "radar", "river_level", "traffic", "energy_utility", "seismic", "fire_detection", "airport", "internet_monitor", "cameras"})


@dataclass(frozen=True)
class Gain:
    action: str
    target: str
    gain: float  # 0-1 (ordenação; não é probabilidade)
    reason: str


def information_gain(category: str, signals: list[Signal], validation: Validation | None = None, event_type: str | None = None,
                     missing_sensors: list[str] | None = None, top: int = 5) -> list[Gain]:
    """`missing_sensors`: tipos de sensor esperados e AUSENTES/PARADOS (de `forecast_v2_features.sensor_coverage`)."""
    prov = provenance(signals)
    gains: list[Gain] = []
    if validation and validation.contradictions:
        who = "negativa oficial" if any(c.get("official_side") for c in validation.contradictions) else "versões incompatíveis"
        gains.append(Gain("RESOLVE_CONTRADICTION", "fonte oficial", WEIGHTS["RESOLVE_CONTRADICTION"], f"{len(validation.contradictions)} contradição(ões) ({who}): "
                                                                                                    "buscar a versão oficial atualizada"))
    official = bool(validation and validation.official_confirmation)
    if not official:
        sig = load_signatures().get(event_type or "", {})
        wanted = [t for t in ("civil_defense", "official") if t in sig.get("confirming", ())] or ["official"]
        gains.append(Gain("CHECK_OFFICIAL_SOURCE", "/".join(wanted), round(WEIGHTS["CHECK_OFFICIAL_SOURCE"] * 1.0, 3), "sem confirmação oficial ainda"))
    missing = [m for m in (missing_sensors or []) if m in PHYSICAL_TYPES]
    if missing:
        n_exp = max(1, len(missing))
        gains.append(Gain("CHECK_PHYSICAL_SENSOR", missing[0], round(WEIGHTS["CHECK_PHYSICAL_SENSOR"] * min(1.0, 0.5 + 0.1 * n_exp), 3),
                          "sensores físicos esperados ausentes/parados: " + ", ".join(sorted(missing)[:4])))
    indep = prov["independent_origin_count"]
    if indep < 2:
        gains.append(Gain("FIND_INDEPENDENT_ORIGIN", "imprensa/órgão local", round(WEIGHTS["FIND_INDEPENDENT_ORIGIN"] * (1.0 if indep == 0 else 0.7), 3),
                          f"{indep} origem(ns) independente(s) não social(is): cópias e posts não confirmam"))
    states = {s.state for s in signals if s.state}
    weak_geo = [s for s in signals if (s.geo_confidence or 0) < 55]
    if len(states) > 1 or (signals and len(weak_geo) / len(signals) > 0.5):
        gains.append(Gain("RESOLVE_GEOLOCATION", "gazetteer/fonte oficial", round(WEIGHTS["RESOLVE_GEOLOCATION"] * (1.0 if len(states) > 1 else 0.6), 3),
                          "localização ambígua (" + ("estados diferentes" if len(states) > 1 else "baixa confiança geográfica") + ")"))
    return sorted(gains, key=lambda g: (-g.gain, g.action))[:top]
