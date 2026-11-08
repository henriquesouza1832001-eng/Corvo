"""Avaliação do Sentinela por REPLAY: roda o detector a cada tick de 5 min vendo só o que já existia (sem espiar o futuro) e mede
investigações abertas, falsas por dia, motivo da abertura, diversidade, origens independentes e expectedness.

Serve a corpora de hard negatives (nenhuma investigação esperada) e de positivos (investigação esperada ANTES do T0). Resultados
de corpus sintético provam mecânica e propriedades (HARNESS_VERIFIED); não são desempenho em produção.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..intelligence.context_engine import ContextCalendar
from ..models import Signal
from .sentinel import Investigation, SentinelConfig, advance, detect_candidates

NEGATIVE, POSITIVE, CONTRADICTION = "negative", "positive", "contradiction"


@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str  # NEGATIVE: nenhuma investigação; POSITIVE: investigação antes de `t0`; CONTRADICTION: investigar é aceitável, nunca CONFIRMED
    signals: list[Signal]
    obs_rows: list[dict]
    start: datetime
    end: datetime
    t0: datetime | None = None  # grande notícia (positivos)
    calendar: ContextCalendar | None = None
    note: str = ""
    tick_min: int = 5
    extra: dict = field(default_factory=dict)


def visible(signals: list[Signal], at: datetime) -> list[Signal]:
    """Só o que já existia E já tinha sido coletado no instante `at`."""
    return [s for s in signals if s.timestamp <= at and s.collected_at <= at]


def replay(sc: Scenario, cfg: SentinelConfig = SentinelConfig()) -> dict:
    active: list[Investigation] = []
    opened: dict[str, dict] = {}
    at = sc.start
    ticks = 0
    while at <= sc.end:
        cands = detect_candidates(visible(sc.signals, at), sc.obs_rows, at, cfg, calendar=sc.calendar)
        by_key = {(c.scope, c.category): c for c in cands}
        for inv in advance(active, cands, at, cfg):
            known = {i.investigation_id: i for i in active}
            active = [i for i in active if i.investigation_id != inv.investigation_id] + [inv]
            if inv.investigation_id not in opened and inv.investigation_id not in known:
                c = by_key.get((inv.scope, inv.category))
                opened[inv.investigation_id] = {
                    "scope": inv.scope, "category": inv.category, "opened_at": at, "reasons": list(inv.reasons),
                    "expectedness": c.expectedness if c else None, "origins": c.origin_count if c else None,
                    "independent_origins": c.independent_origins if c else None, "source_types": c.source_type_count if c else None,
                    "context": list(c.context) if c else [], "anomaly": c.score if c else None}
        ticks += 1
        at += timedelta(minutes=sc.tick_min)
    hours = max(1e-9, (sc.end - sc.start).total_seconds() / 3600 + sc.tick_min / 60)
    invs = list(opened.values())
    reason_kinds = Counter(r.split(" ")[0] for i in invs for r in i["reasons"])
    first_before_t0 = [i for i in invs if sc.t0 and i["opened_at"] <= sc.t0]
    lead = None
    if sc.kind == POSITIVE and sc.t0 and invs:
        earliest = min(i["opened_at"] for i in invs)
        lead = round((sc.t0 - earliest).total_seconds() / 60, 1) if earliest <= sc.t0 else None
    return {"scenario": sc.name, "kind": sc.kind, "ticks": ticks, "hours": round(hours, 2), "investigations": invs, "opened": len(invs),
            "per_day": round(len(invs) / hours * 24, 2), "reasons": dict(reason_kinds),
            "false_investigations": len(invs) if sc.kind == NEGATIVE else 0,
            "false_per_day": round(len(invs) / hours * 24, 2) if sc.kind == NEGATIVE else 0.0,
            "useful_investigations": len(first_before_t0) if sc.kind == POSITIVE else 0, "lead_time_min": lead}


def summarize(results: list[dict]) -> dict:
    neg = [r for r in results if r["kind"] == NEGATIVE]
    pos = [r for r in results if r["kind"] == POSITIVE]
    return {"negatives": len(neg), "false_investigations": sum(r["false_investigations"] for r in neg),
            "negatives_clean": sum(1 for r in neg if r["opened"] == 0),
            "false_per_day_max": max((r["false_per_day"] for r in neg), default=0.0),
            "positives": len(pos), "positives_detected_before_t0": sum(1 for r in pos if r["lead_time_min"] is not None),
            "lead_time_min_median": sorted(r["lead_time_min"] for r in pos if r["lead_time_min"] is not None)[len([1 for r in pos if r["lead_time_min"] is not None]) // 2]
            if any(r["lead_time_min"] is not None for r in pos) else None}
