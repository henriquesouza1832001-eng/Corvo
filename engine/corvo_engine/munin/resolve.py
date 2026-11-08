"""Resolve closed Munin questions from explicitly local price observations."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import statistics
from pathlib import Path
from typing import Iterable

from .questions import ClosedQuestion

_CONTINUOUS_ASSETS = frozenset({"BTC", "ETH", "SOL", "BNB", "XRP"})
_FX_ASSETS = frozenset({"USDBRL", "USDEUR", "USDJPY", "USDGBP", "USDCNY"})


@dataclass(frozen=True)
class Resolution:
    question_id: str
    status: str
    outcome: bool | None = None
    observed_return: float | None = None
    abnormal_return: float | None = None
    threshold: float | None = None
    start_at: str | None = None
    end_at: str | None = None
    reason: str | None = None


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def load_price_csv(path: str | Path) -> list[dict]:
    """Read local ``ativo,timestamp_utc,fechamento`` rows; never fetch prices."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _clean_prices(rows: Iterable[dict], asset: str) -> list[tuple[datetime, float]]:
    by_time: dict[datetime, float] = {}
    for row in rows:
        if str(row.get("ativo", "")).strip() != asset:
            continue
        stamp = _time(row.get("timestamp_utc"))
        try:
            close = float(row.get("fechamento"))
        except (TypeError, ValueError):
            continue
        if stamp is not None and math.isfinite(close) and close > 0:
            by_time[stamp] = close
    return sorted(by_time.items())


def _last_at_or_before(rows: list[tuple[datetime, float]], target: datetime, max_gap: timedelta):
    for stamp, close in reversed(rows):
        if stamp <= target:
            return (stamp, close) if target - stamp <= max_gap else None
    return None


def _first_at_or_after(rows: list[tuple[datetime, float]], target: datetime, max_gap: timedelta):
    for stamp, close in rows:
        if stamp >= target:
            return (stamp, close) if stamp - target <= max_gap else None
    return None


def _fx_closed(stamp: datetime) -> bool:
    """Approximate FX weekend closure: Fri 22:00 UTC through Sun 22:00 UTC."""
    return stamp.weekday() == 5 or (stamp.weekday() == 4 and stamp.hour >= 22) or (stamp.weekday() == 6 and stamp.hour < 22)


def _window_has_market_close(asset: str, start: datetime, end: datetime) -> bool:
    if asset in _CONTINUOUS_ASSETS:
        return False
    if asset not in _FX_ASSETS:
        return False  # Unknown calendars are not guessed.
    cursor = start
    while cursor <= end:
        if _fx_closed(cursor):
            return True
        cursor += timedelta(hours=1)
    return False


def resolve_question(question: ClosedQuestion, event_time: str, rows: Iterable[dict]) -> Resolution:
    """Resolve only when local history and a post-horizon close are both present.

    The threshold is the sample standard deviation of the previous 30 returns
    sampled at the same horizon, all ending no later than event publication.
    The outcome is the horizon log return crossing the direction's one-sigma
    boundary. Prices are never synthesized or extrapolated.
    """
    t0 = _time(event_time)
    if t0 is None:
        return Resolution(question.question_id, "invalid_event_time", reason="event time is missing or invalid")
    prices = _clean_prices(rows, question.asset)
    if not prices:
        return Resolution(question.question_id, "awaiting_price", reason=f"no local price series for {question.asset}")

    horizon = timedelta(hours=question.horizon_hours)
    if _window_has_market_close(question.asset, t0, t0 + horizon):
        return Resolution(
            question.question_id,
            "cancelled_market_closed",
            reason="the forecast window intersects the instrument's known market closure",
        )

    gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(prices, prices[1:])]
    positive_gaps = [gap for gap in gaps if gap > 0]
    if not positive_gaps:
        return Resolution(question.question_id, "insufficient_history", reason="fewer than two valid closes")
    step = statistics.median(positive_gaps)
    max_gap = timedelta(seconds=max(step * 1.5, 3600))
    anchors: list[tuple[datetime, float]] = []
    for k in range(31, 0, -1):
        sample = _last_at_or_before(prices, t0 - horizon * k, max_gap)
        if sample is None:
            return Resolution(question.question_id, "insufficient_history", reason="missing one of 31 pre-event horizon anchors")
        anchors.append(sample)
    prior_returns = [math.log(b[1] / a[1]) for a, b in zip(anchors, anchors[1:])]
    if len({sample[0] for sample in anchors}) != 31 or len(prior_returns) != 30:
        return Resolution(question.question_id, "insufficient_history", reason="fewer than 30 distinct prior horizon returns")
    expected_return = statistics.mean(prior_returns)
    sigma = statistics.stdev(prior_returns)
    if not math.isfinite(sigma) or sigma <= 0:
        return Resolution(question.question_id, "insufficient_history", reason="pre-event volatility is not measurable")

    start = _first_at_or_after(prices, t0, max_gap)
    end = _first_at_or_after(prices, t0 + horizon, max_gap)
    if start is None:
        return Resolution(question.question_id, "insufficient_history", reason="no close at event start")
    if end is None:
        return Resolution(
            question.question_id,
            "awaiting_future_price",
            start_at=start[0].isoformat().replace("+00:00", "Z"),
            reason="the horizon has no local closing price yet",
        )
    observed = math.log(end[1] / start[1])
    threshold = question.sigma_threshold * sigma
    abnormal = observed - expected_return
    outcome = {
        "up": abnormal > threshold,
        "down": abnormal < -threshold,
        "volatile": abs(abnormal) > threshold,
    }.get(question.direction)
    if outcome is None:
        return Resolution(question.question_id, "invalid_question", reason="unknown direction")
    return Resolution(
        question.question_id,
        "resolved",
        outcome=outcome,
        observed_return=observed,
        abnormal_return=abnormal,
        threshold=threshold,
        start_at=start[0].isoformat().replace("+00:00", "Z"),
        end_at=end[0].isoformat().replace("+00:00", "Z"),
    )
