"""Synthetic price fixtures for local Munin resolution tests only."""
from datetime import datetime, timedelta, timezone
import math

from corvo_engine.munin.questions import ClosedQuestion
from corvo_engine.munin.resolve import load_price_csv, resolve_question


T0 = datetime(2026, 11, 10, tzinfo=timezone.utc)


def question(asset="BTC", direction="up", hours=6):
    return ClosedQuestion(
        question_id="q_synthetic_1",
        event_id="evt_synthetic_1",
        topic="cripto",
        asset=asset,
        direction=direction,
        horizon_hours=hours,
        text="Synthetic test question?",
        instrument_available=True,
    )


def synthetic_prices(end_index=260):
    """Return synthetic BTC closes. This fixture is never used as product data."""
    rows = []
    price = 100.0
    for index in range(end_index + 1):
        if index:
            change = 0.001 if index % 2 else -0.0007
            if 251 <= index <= 256:
                change = 0.004
            price *= math.exp(change)
        stamp = T0 - timedelta(hours=250 - index)
        rows.append({
            "ativo": "BTC",
            "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
            "fechamento": str(price),
            "provenance": "synthetic",
        })
    return rows


def test_resolves_only_after_30_pre_event_horizon_returns_and_future_close():
    result = resolve_question(question(), T0.isoformat(), synthetic_prices())

    assert result.status == "resolved"
    assert result.outcome is True
    assert result.threshold is not None and result.abnormal_return > result.threshold
    assert result.start_at == T0.isoformat().replace("+00:00", "Z")
    assert result.end_at == (T0 + timedelta(hours=6)).isoformat().replace("+00:00", "Z")


def test_missing_price_and_missing_future_close_are_not_guessed():
    no_series = resolve_question(question(asset="SP500"), T0.isoformat(), synthetic_prices())
    no_future = resolve_question(question(), T0.isoformat(), synthetic_prices(end_index=253))

    assert no_series.status == "awaiting_price"
    assert no_series.outcome is None
    assert no_future.status == "awaiting_future_price"
    assert no_future.outcome is None


def test_fewer_than_30_prior_returns_abstains_from_resolution():
    short = synthetic_prices(end_index=200)
    result = resolve_question(question(), T0.isoformat(), short)

    assert result.status == "insufficient_history"
    assert result.outcome is None


def test_invalid_event_time_and_nonpositive_prices_are_rejected():
    bad = [dict(row, fechamento="0") for row in synthetic_prices()]
    invalid_time = resolve_question(question(), "not-a-time", synthetic_prices())
    invalid_price = resolve_question(question(), T0.isoformat(), bad)

    assert invalid_time.status == "invalid_event_time"
    assert invalid_price.status == "awaiting_price"


def test_known_fx_weekend_closure_cancels_but_crypto_is_not_calendar_cancelled():
    saturday = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    fx_question = question(asset="USDEUR", direction="volatile", hours=24)
    fx_rows = [{"ativo": "USDEUR", "timestamp_utc": "2026-11-13T16:00:00Z", "fechamento": "0.9", "provenance": "synthetic"}]
    cancelled = resolve_question(fx_question, saturday.isoformat(), fx_rows)
    crypto = resolve_question(question(), saturday.isoformat(), synthetic_prices())

    assert cancelled.status == "cancelled_market_closed"
    assert cancelled.outcome is None
    assert crypto.status != "cancelled_market_closed"


def test_load_price_csv_reads_only_existing_local_rows(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("ativo,timestamp_utc,fechamento\nBTC,2026-11-10T00:00:00Z,100\n", encoding="utf-8")

    assert load_price_csv(path) == [{
        "ativo": "BTC", "timestamp_utc": "2026-11-10T00:00:00Z", "fechamento": "100"
    }]
