from datetime import date, datetime, timedelta, timezone

from corvo_engine.anomaly import window_anomaly
from corvo_engine.baseline import BR_TZ
from corvo_engine.intelligence.baseline_hierarchy import ladder_gaps, resolve_baseline

AT = datetime(2026, 10, 7, 21, 0, tzinfo=timezone.utc)  # quarta 18:00 em Brasília


def rows(scope, fn, days, category="TRAFFIC"):
    out, end = [], AT.replace(minute=0)
    for h in range(1, 24 * days):
        t = end - timedelta(hours=h)
        n = fn(t.astimezone(BR_TZ))
        if n:
            out.append({"scope": scope, "category": category, "source_class": "NEWS_HIGH", "hour": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "signals": n,
                        "sources": 2, "duplicates": 0})
    return out


def test_best_level_wins_and_carries_metadata():
    r = resolve_baseline(rows("UF:MG", lambda l: 6, 35), "UF:MG", "TRAFFIC", AT)
    d = r.describe()
    assert r.valid and d["fallback_level"] == "dow_hour" and d["scope_used"] == "UF:MG" and d["seasonality"] == "weekday_hour"
    assert d["sample_size"] >= 3 and d["hour"] == 18 and d["weekday"] == 2 and 0 < d["reliability"] <= 1 and d["levels_unavailable"] == ["city"]


def test_fallback_to_hour_then_all_hours_and_reliability_decreases():
    dow = resolve_baseline(rows("UF:MG", lambda l: 6, 35), "UF:MG", "TRAFFIC", AT)
    hour = resolve_baseline(rows("UF:MG", lambda l: 6, 8), "UF:MG", "TRAFFIC", AT)  # 7 dias: poucas quartas, mas >= 5 dias da mesma hora
    assert hour.level == "hour" and hour.reliability < dow.reliability
    flat = resolve_baseline(rows("UF:MG", lambda l: 6, 3), "UF:MG", "TRAFFIC", AT)  # 2 dias: < 5 amostras da mesma hora, mas >= 24 horas com dado
    assert flat.level == "all_hours" and flat.seasonality == "none" and flat.reliability < hour.reliability


def test_national_fallback_is_scaled_by_state_share_and_declared():
    br = rows("BR", lambda l: 100, 35)
    mg = [r for r in rows("UF:MG", lambda l: 10, 35) if r["hour"][11:13] != "21"]  # estado sem a hora comparável: cai para o nacional escalado
    mg = [r for r in mg if int(r["hour"][8:10]) % 2 == 0][:20]  # e com histórico próprio ESPARSO (< 24 horas)
    r = resolve_baseline(br + mg, "UF:MG", "TRAFFIC", AT)
    assert r.level == "national_scaled" and r.scope_used == "BR" and 0 < r.scale < 1
    assert abs(r.base.mean - 100 * r.scale) < 1e-6 and r.reliability <= 0.3  # nunca esconde que não é do estado


def test_nothing_reliable_means_insufficient_and_no_anomaly():
    r = resolve_baseline([], "UF:MG", "TRAFFIC", AT)
    assert not r.valid and r.level == "insufficient" and r.reliability == 0.0
    assert window_anomaly(50, 15, r.base)["status"] == "BASELINE INSUFICIENTE"
    few = [r for r in rows("UF:MG", lambda l: 6, 2)][:20]
    assert not resolve_baseline(few, "UF:MG", "TRAFFIC", AT).valid  # 20 horas com dado: abaixo do mínimo de qualquer nível


def test_holiday_counts_as_sunday_in_every_level():
    hol = {date(2026, 10, 7): "feriado"}
    fn = lambda l: 25 if l.weekday() == 6 else 5  # noqa: E731
    plain = resolve_baseline(rows("UF:MG", fn, 35), "UF:MG", "TRAFFIC", AT)
    ctx = resolve_baseline(rows("UF:MG", fn, 35), "UF:MG", "TRAFFIC", AT, hol)
    assert plain.base.mean < 10 < ctx.base.mean and ctx.weekday == 6 and plain.weekday == 2


def test_city_level_is_declared_unavailable_not_simulated():
    assert ladder_gaps() == ("city",)
    assert "city" in resolve_baseline([], "UF:MG", "TRAFFIC", AT).levels_unavailable
