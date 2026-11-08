"""Valor de sensor: avaliação INCREMENTAL por família/fonte. SOMENTE MEDE: nunca remove nem desliga fonte (decisão humana).

Por família: observações/dia, sinais únicos/dia, eventos para os quais contribuiu, confirmações independentes, contribuição a falsos
positivos, razão de duplicatas, disponibilidade, frescor e ganho marginal de informação. O ganho marginal é medido por LEAVE-ONE-OUT:
"se esta família não existisse, quantos eventos perderiam a corroboração mínima (>= `min_origins` origens)? e quem foi o PRIMEIRO a falar?".
Entradas são registros simples (a plataforma os agrega por dia); amostra pequena devolve `INSUFFICIENT_DATA` em vez de uma nota.
"""
from __future__ import annotations

from collections import defaultdict

MIN_EVENTS = 20
MIN_DAYS = 3


def _ratio(a: float, b: float) -> float | None:
    return round(a / b, 4) if b else None


def family_report(daily: list[dict]) -> dict[str, dict]:
    """`daily`: {family, day, observations, unique_signals, duplicates, events_contributed, independent_confirmations, false_positive_events,
    available_checks, ok_checks, fresh_checks}. Agrega por família."""
    by: dict[str, list[dict]] = defaultdict(list)
    for d in daily:
        by[d["family"]].append(d)
    out = {}
    for fam, rows in sorted(by.items()):
        days = len({r["day"] for r in rows})
        s = lambda k: sum(r.get(k, 0) for r in rows)  # noqa: E731
        rep = {"days": days, "observations_per_day": _ratio(s("observations"), days), "unique_signals_per_day": _ratio(s("unique_signals"), days),
               "events_contributed": s("events_contributed"), "independent_confirmations": s("independent_confirmations"),
               "false_positive_contribution": _ratio(s("false_positive_events"), s("events_contributed")),
               "duplicate_ratio": _ratio(s("duplicates"), s("observations")), "availability": _ratio(s("ok_checks"), s("available_checks")),
               "freshness": _ratio(s("fresh_checks"), s("available_checks"))}
        rep["status"] = "OK" if days >= MIN_DAYS else "INSUFFICIENT_DATA"
        out[fam] = rep
    return out


def marginal_information_gain(events: list[dict], min_origins: int = 2) -> dict[str, dict]:
    """`events`: {event_id, origins: {family: n_origins}, first_seen: {family: minutos antes do T0 (maior = mais cedo)}, outcome: 'TRUE'|'FALSE'|None}.
    Para cada família: eventos que perderiam a corroboração sem ela, eventos em que foi a PRIMEIRA, e (se houver desfecho) falsos positivos
    que só existiram graças a ela. `INSUFFICIENT_DATA` abaixo de MIN_EVENTS."""
    fams = sorted({f for e in events for f in e["origins"]})
    out = {}
    for f in fams:
        mine = [e for e in events if f in e["origins"]]
        lost = [e for e in mine if sum(n for g, n in e["origins"].items() if g != f) < min_origins <= sum(e["origins"].values())]
        first = [e for e in mine if e.get("first_seen") and max(e["first_seen"], key=e["first_seen"].get) == f]
        fp_only = [e for e in lost if e.get("outcome") == "FALSE"]
        out[f] = {"events": len(mine), "needed_for_corroboration": len(lost), "marginal_gain": _ratio(len(lost), len(mine)),
                  "first_to_report": len(first), "first_ratio": _ratio(len(first), len(mine)), "false_positive_dependence": len(fp_only),
                  "status": "OK" if len(events) >= MIN_EVENTS else "INSUFFICIENT_DATA"}
    return out


def verdict_hint(report: dict, gain: dict) -> str:
    """Rótulo descritivo (NUNCA ação automática): o que os números sugerem a um humano."""
    if report.get("status") != "OK" or gain.get("status") != "OK":
        return "INSUFFICIENT_DATA"
    if (gain.get("marginal_gain") or 0) == 0 and (gain.get("first_ratio") or 0) == 0 and (report.get("duplicate_ratio") or 0) > 0.5:
        return "LOW_MARGINAL_VALUE_REVIEW"
    return "KEEP_MEASURING"
