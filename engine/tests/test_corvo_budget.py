import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from benchmarks.corvo_budget_check import LIMIT_NORMAL, project

ENGINE = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def row(i, title, hours_ago=1):
    return {"url": f"https://x.com/{i}", "source_id": "s", "title": title, "published_at": (NOW - timedelta(hours=hours_ago)).isoformat()}


def corpus(n_noise, n_market):
    return [row(i, "Celebrity perfume launch") for i in range(n_noise)] + [row(1_000_000 + i, f"Fed announces rate cut as inflation cools {i}") for i in range(n_market)]


def test_normal_day_is_within_limits():
    res = project(corpus(900, 40))  # 4% aceito
    assert res["ok"] and res["aceitos_24h"] == 40
    assert res["limites"]["linhas_por_dia"]["valor"] == 2 * 40 + 144 * 3


def test_budget_projects_normal_economy_and_critical_for_24h_and_five_x():
    res = project(corpus(900, 40))
    scenarios = res["cenarios_pressao"]
    assert set(scenarios) == {"normal", "economy", "critical"}
    assert scenarios["normal"]["aceitos_24h"] >= scenarios["economy"]["aceitos_24h"] >= scenarios["critical"]["aceitos_24h"]
    assert all(s["ok"] and s["linhas_por_dia_5x"] <= 25_000 for s in scenarios.values())


def test_a_loosened_filter_that_accepts_everything_is_caught():
    res = project(corpus(0, 900))  # tudo vira aceito: o freio tem que pegar pela fração aceita
    assert not res["ok"]
    assert not res["limites"]["fracao_aceita"]["ok"]


def test_heavy_volume_trips_the_row_limits():
    res = project(corpus(21_000, 2_600))  # 11% aceito (ok na fração), mas 2.600 gravações/dia estouram o limite de linhas
    assert res["limites"]["fracao_aceita"]["ok"]
    assert not res["limites"]["linhas_por_dia"]["ok"]
    assert not res["limites"]["linhas_por_dia_5x"]["ok"]
    assert res["limites"]["linhas_por_dia"]["valor"] > LIMIT_NORMAL


def test_old_backfill_does_not_count_as_daily_volume():
    old = [row(20_000 + i, f"Fed announces rate cut {i}", hours_ago=72) for i in range(500)]
    res = project(corpus(900, 10) + old)
    assert res["volume_24h"] == 910  # o histórico de 3 dias atrás fica de fora


def test_cli_exit_code_follows_the_result(tmp_path):
    ok_f, bad_f = tmp_path / "ok.jsonl", tmp_path / "bad.jsonl"
    ok_f.write_text("\n".join(json.dumps(r) for r in corpus(900, 40)), encoding="utf-8")
    bad_f.write_text("\n".join(json.dumps(r) for r in corpus(0, 900)), encoding="utf-8")
    run = lambda f: subprocess.run([sys.executable, "benchmarks/corvo_budget_check.py", str(f)], cwd=ENGINE, capture_output=True, text=True, encoding="utf-8")
    assert run(ok_f).returncode == 0
    assert run(bad_f).returncode == 1
