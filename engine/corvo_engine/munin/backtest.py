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


def _entry(event: Event, question: ClosedQuestion, resolution: Resolution, prediction, sources: int) -> dict:
    key = _key(question)
    common = {
        "event_id": event.event_id,
        "event_time": event.first_observed_at,
        "question_id": question.question_id,
        "question": question.text,
        "topic": question.topic,
        "asset": question.asset,
        "direction": question.direction,
        "horizon_hours": question.horizon_hours,
        "base_rate_key": list(key),
        "method": "taxa-base por tema, ativo, direção e horizonte (beta-binomial v1)",
        "n_prior_resolved_events": 0 if prediction is None else prediction.n,
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
) -> dict:
    """Run deterministic walk-forward forecasts; no network or synthetic data.

    Only Hugin-approved ``hot``/``buffer`` rows become events. A resolved
    outcome enters the baseline after its resolution close and only before a
    later event's publication time. The report is exploratory: this same local
    history is not an untouched calibration test set.
    """
    rows = list(price_rows)
    approved = [
        row for row in articles
        if isinstance(row, dict) and str(row.get("verdict", "")).lower() in {"hot", "buffer"}
    ]
    events = build_events(approved)
    symbols = {str(row.get("ativo", "")).strip() for row in rows if row.get("ativo")}
    model = BaseRateModel(min_n=min_n)
    entries: list[dict] = []
    pending: list[tuple[datetime, tuple[str, str, str], bool]] = []

    for event in events:
        event_time = _utc(event.first_observed_at)
        if event_time is None:
            continue
        ready = [item for item in pending if item[0] <= event_time]
        pending = [item for item in pending if item[0] > event_time]
        for _, key, outcome in ready:
            model.update(key, outcome)

        for question in questions_for_event(event, available_price_symbols=symbols):
            key = _key(question)
            prediction = model.predict(key)
            resolution = resolve_question(question, event.first_observed_at, rows)
            entries.append(_entry(event, question, resolution, prediction, len(event.source_ids)))
            end = _utc(resolution.end_at)
            if resolution.status == "resolved" and resolution.outcome is not None and end is not None:
                pending.append((end, key, resolution.outcome))

    brier_values = [
        (entry["probability"] - float(entry["resolution"]["outcome"])) ** 2
        for entry in entries
        if entry["record_type"] == "forecast" and entry["resolution"]["status"] == "resolved"
    ]
    by_resolution = Counter(entry["resolution"]["status"] for entry in entries)
    forecast_count = sum(entry["record_type"] == "forecast" for entry in entries)
    abstention_count = len(entries) - forecast_count
    run_id = _persist(output_path, entries) if output_path is not None else None
    return {
        "events": len(events),
        "questions": len(entries),
        "forecasts": forecast_count,
        "abstentions": abstention_count,
        "resolution_status": dict(sorted(by_resolution.items())),
        "resolved_forecast_outcomes": len(brier_values),
        "brier": round(sum(brier_values) / len(brier_values), 6) if brier_values else None,
        "calibration_claim": "not assessed; local outcomes are exploratory, not a sealed temporal holdout",
        "run_id": run_id,
        "entries": entries,
    }
