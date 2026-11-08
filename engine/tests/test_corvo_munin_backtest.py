"""Synthetic prices are explicitly marked synthetic and used only by these tests."""
from datetime import datetime, timedelta, timezone
import math

from corvo_engine.munin.backtest import run_backtest


def synthetic_fixture(event_count=31):
    first_event = datetime(2026, 6, 1, tzinfo=timezone.utc)
    events = []
    for index in range(event_count):
        stamp = first_event + timedelta(hours=72 * index)
        events.append({
            "source_id": "synthetic-wire",
            "title": f"Crypto incident token{index}",
            "url": f"https://synthetic.test/{index}",
            "published_at": stamp.isoformat().replace("+00:00", "Z"),
            "topics": ["cripto"],
            "verdict": "hot",
        })

    start = first_event - timedelta(hours=300)
    end = first_event + timedelta(hours=72 * (event_count - 1) + 8)
    hours = int((end - start).total_seconds() // 3600)
    price = 100.0
    prices = []
    for index in range(hours + 1):
        if index:
            price *= math.exp(0.0005 if index % 3 == 0 else -0.0002)
        stamp = start + timedelta(hours=index)
        prices.append({
            "ativo": "BTC",
            "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
            "fechamento": str(price),
            "provenance": "synthetic",
        })
    return events, prices


def test_end_to_end_walk_forward_abstains_until_30_resolved_events_and_registry_is_idempotent(tmp_path):
    events, prices = synthetic_fixture()
    registry = tmp_path / "previsoes.jsonl"

    result = run_backtest(events, prices, output_path=registry)
    first_lines = registry.read_text(encoding="utf-8").splitlines()
    repeated = run_backtest(events, prices, output_path=registry)
    second_lines = registry.read_text(encoding="utf-8").splitlines()

    assert result["events"] == 31
    assert result["forecasts"] == 1  # ETH has no synthetic series and never forecasts.
    assert result["abstentions"] == 61
    assert result["resolved_forecast_outcomes"] == 1
    assert result["brier"] is not None
    assert result["brier_taxa_base"] == result["brier"]
    assert result["skill_vs_taxa_base"] == 0.0
    assert result["ece"] is not None
    assert result["calibration_claim"].startswith("not assessed")
    final_btc = [entry for entry in result["entries"] if entry["asset"] == "BTC"][-1]
    assert final_btc["record_type"] == "forecast" and final_btc["n_prior_resolved_events"] == 30
    first_btc = next(entry for entry in result["entries"] if entry["asset"] == "BTC")
    assert first_btc["remaining_to_min_n"] == 30
    assert repeated["run_id"] == result["run_id"]
    assert len(first_lines) == len(second_lines) == 62


def test_no_prices_produces_only_abstentions_and_no_fake_brier():
    events, _ = synthetic_fixture(event_count=1)
    result = run_backtest(events, [], min_n=1)

    assert result["forecasts"] == 0
    assert result["abstentions"] == 2
    assert result["resolution_status"] == {"awaiting_price": 2}
    assert result["brier"] is None
    assert result["brier_taxa_base"] is None and result["skill_vs_taxa_base"] is None and result["ece"] is None
    assert len(result["open_to_min_n"]) == 2
    assert all(value["additional_events_needed"] == 1 for value in result["open_to_min_n"].values())


def test_local_registry_preserves_explicit_official_confirmation():
    events, _ = synthetic_fixture(event_count=1)
    events[0]["source_id"] = "official-wire"
    events[0]["url"] = "https://official.test/event"
    result = run_backtest(events, [], official_sources={"official-wire"})

    assert result["entries"][0]["confirmation"] == "official"
    assert result["entries"][0]["source_ids"] == ["official-wire"]
    assert "crypto trades continuously" in result["entries"][0]["annulment_rule"]
