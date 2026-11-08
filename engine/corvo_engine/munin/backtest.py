"""Local walk-forward chain from approved articles to forecast proof records."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .baseline import BaseRateModel, to_record
from .events import Event, build_events
from .questions import ClosedQuestion, questions_for_event
from .resolve import Resolution, resolve_question
from .scoring import ece


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _key(question: ClosedQuestion) -> tuple[str, str, str]:
    # The direction is part of the binary question, so it belongs in the
    # baseline key even though the baseline module has three generic fields.
    return question.topic, f"{question.asset}:{question.direction}", f"{question.horizon_hours}h"


def _entry(
    event: Event,
    question: ClosedQuestion,
    resolution: Resolution,
    prediction,
    sources: int,
    prior_n: int,
    min_n: int,
) -> dict:
    key = _key(question)
    common = {
        "event_id": event.event_id,
        "event_time": event.available_at,
        "observation_time_basis": event.observation_time_basis,
        "source_ids": list(event.source_ids),
        "source_count": len(event.source_ids),
        "confirmation": event.confirmation,
        "question_id": question.question_id,
        "question": question.text,
        "topic": question.topic,
        "asset": question.asset,
        "direction": question.direction,
        "horizon_hours": question.horizon_hours,
        "base_rate_key": list(key),
        "resolution_rule": question.resolution_rule,
        "annulment_rule": question.annulment_rule,
        "method": "taxa-base por tema, ativo, direção e horizonte (beta-binomial v1)",
        "n_prior_resolved_events": prior_n,
        "remaining_to_min_n": max(0, min_n - prior_n),
        "resolution": {
            "status": resolution.status,
            "outcome": resolution.outcome,
            "observed_return": resolution.observed_return,
            "abnormal_return": resolution.abnormal_return,
            "threshold": resolution.threshold,
            "start_at": resolution.start_at,
            "end_at": resolution.end_at,
            "reason": resolution.reason,
        },
    }
    if prediction is None:
        return {"record_type": "abstention", **common, "status": "abstained_n_lt_30", "probability": None, "reason": "n<30 independent resolved events"}
    record = to_record(prediction, question.text, sources=sources, horizon=f"{question.horizon_hours}h", forecast_id=question.question_id)
    return {
        "record_type": "forecast",
        **common,
        "status": record.status,
        "probability": record.probability,
        "interval_low": record.interval_low,
        "interval_high": record.interval_high,
        "evidences": record.evidences,
        "sources": record.sources,
        "reason": None,
    }


def _persist(path: str | Path, entries: list[dict]) -> str | None:
    if not entries:
        return None
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    run_id = "run_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_runs: set[str] = set()
    if target.exists():
        with target.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    old = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if old.get("run_id"):
                    existing_runs.add(str(old["run_id"]))
    if run_id not in existing_runs:
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            for entry in entries:
                handle.write(json.dumps({"run_id": run_id, **entry}, ensure_ascii=False, sort_keys=True) + "\n")
    return run_id


def run_backtest(
    articles: Iterable[dict],
    price_rows: Iterable[dict],
    *,
    output_path: str | Path | None = None,
    min_n: int = 30,
    official_sources: Iterable[str] = (),
) -> dict:
    """Run deterministic walk-forward forecasts; no network or synthetic data.

    Only Hugin-approved ``hot``/``buffer`` rows become events. A resolved
    outcome enters the baseline after its resolution close and only before a
    later event's availability time. The report is exploratory: this same local
    history is not an untouched calibration test set.
    """
    rows = list(price_rows)
    approved = [
        row for row in articles
        if isinstance(row, dict) and str(row.get("verdict", "")).lower() in {"hot", "buffer"}
    ]
    events = build_events(approved, official_sources=official_sources)
    symbols = {str(row.get("ativo", "")).strip() for row in rows if row.get("ativo")}
    model = BaseRateModel(min_n=min_n)
    entries: list[dict] = []
    pending: list[tuple[datetime, datetime, tuple[str, str, str], bool]] = []
    last_independent_window_end: dict[tuple[str, str, str], datetime] = {}
    overlapping_outcomes_excluded = 0
    skipped_without_cycle_at = sum(event.available_at is None for event in events)

    for event in events:
        event_time = _utc(event.available_at)
        if event_time is None:
            continue
        ready = sorted(
            (item for item in pending if item[1] <= event_time),
            key=lambda item: (item[0], item[1], item[2]),
        )
        pending = [item for item in pending if item[1] > event_time]
        for start, end, key, outcome in ready:
            previous_end = last_independent_window_end.get(key)
            if previous_end is not None and start < previous_end:
                overlapping_outcomes_excluded += 1
                continue
            model.update(key, outcome)
            last_independent_window_end[key] = end

        for question in questions_for_event(event, available_price_symbols=symbols):
            key = _key(question)
            prediction = model.predict(key)
            resolution = resolve_question(question, event.available_at, rows)
            prior_n = model.n(key)
            entries.append(_entry(event, question, resolution, prediction, len(event.source_ids), prior_n, min_n))
            end = _utc(resolution.end_at)
            start = _utc(resolution.start_at)
            if resolution.status == "resolved" and resolution.outcome is not None and start is not None and end is not None and end > start:
                pending.append((start, end, key, resolution.outcome))

    scored_entries = [
        entry
        for entry in entries
        if entry["record_type"] == "forecast" and entry["resolution"]["status"] == "resolved"
    ]
    ps = [float(entry["probability"]) for entry in scored_entries]
    ys = [int(entry["resolution"]["outcome"]) for entry in scored_entries]
    brier_values = [(p - y) ** 2 for p, y in zip(ps, ys)]
    brier_score = sum(brier_values) / len(brier_values) if brier_values else None
    # The only forecaster in this chain is the empirical base rate itself, so
    # its proper-score reference is the same point-in-time probability. Skill
    # against this reference is therefore zero, not an invented model gain.
    base_brier = brier_score
    base_skill = 0.0 if brier_score is not None and brier_score > 0 else None
    calibration_error = ece(ps, ys) if ps else None
    by_resolution = Counter(entry["resolution"]["status"] for entry in entries)
    forecast_count = sum(entry["record_type"] == "forecast" for entry in entries)
    abstention_count = len(entries) - forecast_count
    open_groups: dict[tuple[str, ...], list[dict]] = {}
    for entry in entries:
        if entry["record_type"] == "abstention":
            open_groups.setdefault(tuple(entry["base_rate_key"]), []).append(entry)
    open_to_min_n = {
        "|".join(key): {
            "open_questions": len(group),
            "resolved_events_seen": max(item["n_prior_resolved_events"] for item in group),
            "additional_events_needed": min(item["remaining_to_min_n"] for item in group),
        }
        for key, group in sorted(open_groups.items())
    }
    run_id = _persist(output_path, entries) if output_path is not None else None
    return {
        "events": len(events),
        "events_skipped_missing_cycle_at": skipped_without_cycle_at,
        "overlapping_outcomes_excluded": overlapping_outcomes_excluded,
        "questions": len(entries),
        "forecasts": forecast_count,
        "abstentions": abstention_count,
        "resolution_status": dict(sorted(by_resolution.items())),
        "resolved_forecast_outcomes": len(brier_values),
        "brier": round(brier_score, 6) if brier_score is not None else None,
        "brier_taxa_base": round(base_brier, 6) if base_brier is not None else None,
        "skill_vs_taxa_base": round(base_skill, 6) if base_skill is not None else None,
        "ece": round(calibration_error, 6) if calibration_error is not None else None,
        "open_to_min_n": open_to_min_n,
        "calibration_claim": "not assessed; local outcomes are exploratory, not a sealed temporal holdout",
        "run_id": run_id,
        "entries": entries,
    }
