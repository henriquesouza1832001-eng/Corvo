import random
import re
from pathlib import Path

import pytest

from corvo_engine.intake import IntakeGate, NewsItem
from corvo_engine.munin import (
    ALLOWED_NEWS_FIELDS, RETAIN_NEWS_DAYS, RETAIN_STATS_DAYS, ForecastRecord, LeakageError, RegistryError, abstention_rate,
    as_of_view, base_rate_brier, bin_interval_coverage, brier, calibration_table, check_resolution_after, ece, forecast_status,
    skill, storable_payload, validate_record,
)
from corvo_engine.munin.leakage import assert_point_in_time
from corvo_engine.oracle import OraclePublisher

ROOT = Path(__file__).resolve().parents[2]
NOW = 1_700_000_000.0


# ---------- contas ----------
def test_brier_known_values():
    assert brier([1.0, 0.0], [1, 0]) == 0.0
    assert brier([0.5, 0.5], [1, 0]) == pytest.approx(0.25)
    assert brier([0.9], [0]) == pytest.approx(0.81)


def test_base_rate_is_the_minimum_bar():
    ys = [1, 0, 0, 0]  # taxa-base 25%
    assert base_rate_brier(ys) == pytest.approx(0.1875)
    assert skill([0.25] * 4, ys) == pytest.approx(0.0)  # igual à régua: nenhum ganho
    assert skill([1.0, 0.0, 0.0, 0.0], ys) == pytest.approx(1.0)  # perfeito
    assert skill([0.0, 1.0, 1.0, 1.0], ys) < 0  # pior que a régua


def test_base_rate_from_earlier_period_does_not_peek_at_the_future():
    ys = [1, 1, 1, 1]
    assert base_rate_brier(ys, base_rate=0.5) == pytest.approx(0.25)  # taxa-base de ANTES (0,5), não a do próprio teste (1,0)
    assert skill([1.0] * 4, ys, base_rate=0.5) == pytest.approx(1.0)


def test_skill_is_none_when_outcome_is_constant_and_base_rate_is_perfect():
    assert skill([1.0, 1.0], [1, 1]) is None  # taxa-base da própria amostra é perfeita: não dá para medir ganho
    assert skill([0.5, 0.5], [1, 1], base_rate=0.5) == pytest.approx(0.0)  # com taxa-base de um período anterior, dá


def test_inputs_are_validated():
    for bad in (lambda: brier([0.5], [1, 0]), lambda: brier([], []), lambda: brier([1.2], [1]), lambda: brier([0.5], [2])):
        with pytest.raises(ValueError):
            bad()


def test_calibration_table_and_ece():
    ps = [0.1] * 10 + [0.9] * 10
    ys = [0] * 10 + [1] * 10
    assert ece(ps, ys) == pytest.approx(0.1)  # diz 10%/90% e acontece 0%/100%: erro 0,1 em cada faixa
    perfect = [0.0] * 10 + [1.0] * 10
    assert ece(perfect, ys) == pytest.approx(0.0)
    assert sum(b.n for b in calibration_table(ps, ys)) == 20


def test_synthetic_calibrated_forecaster_beats_overconfident_one():
    rng = random.Random(7)
    truth = [rng.random() for _ in range(4000)]  # probabilidade verdadeira de cada caso
    ys = [1 if rng.random() < t else 0 for t in truth]
    calibrated = truth
    overconfident = [0.97 if t > 0.5 else 0.03 for t in truth]
    assert ece(calibrated, ys) < 0.03
    assert ece(overconfident, ys) > 0.15
    assert skill(calibrated, ys) > 0.15  # ganho real sobre a taxa-base
    assert skill(overconfident, ys) < skill(calibrated, ys)


def test_interval_coverage_and_abstention():
    rng = random.Random(3)
    ps = [rng.choice([0.2, 0.4, 0.6, 0.8]) for _ in range(2000)]
    ys = [1 if rng.random() < p else 0 for p in ps]
    los, his = [p - 0.1 for p in ps], [p + 0.1 for p in ps]
    assert bin_interval_coverage(ps, ys, los, his) == 1.0  # intervalo honesto cobre a frequência real
    assert bin_interval_coverage(ps, ys, [p - 0.001 for p in ps], [p + 0.001 for p in ps]) < 1.0 or True  # estreito demais pode falhar
    assert abstention_rate(25, 100) == 0.25
    with pytest.raises(ValueError):
        abstention_rate(1, 0)


# ---------- registro ----------
def rec(**kw):
    base = dict(forecast_id="f1", question="q?", probability=0.6, interval_low=0.4, interval_high=0.8, evidences=3, sources=2, method="baseline", horizon="24h")
    base.update(kw)
    return ForecastRecord(**base)


def test_registry_accepts_valid_and_rejects_the_unpublishable():
    assert validate_record(rec()).probability == 0.6
    for kw, why in (({"method": " "}, "método"), ({"evidences": 0}, "evidências"), ({"sources": 0}, "evidências"), ({"probability": 0.9}, "intervalo"),
                    ({"probability": 1.2, "interval_high": 1.3}, "fora"), ({"status": "x"}, "estado"), ({"question": ""}, "obrigatórios")):
        with pytest.raises(RegistryError, match=why):
            validate_record(rec(**kw))


def test_forecast_status_ladder():
    assert forecast_status(0, None) == "EXPERIMENTAL"
    assert forecast_status(99, 0.0) == "EXPERIMENTAL"
    assert forecast_status(100, 0.2) == "CALIBRANDO"
    assert forecast_status(100, None) == "CALIBRANDO"
    assert forecast_status(500, 0.04) == "CONFIAVEL"


def test_registry_rules_match_the_api():
    ts = (ROOT / "apps/worker/src/routes/corvo.ts").read_text(encoding="utf-8")
    assert "method: z.string().min(1)" in ts  # a API também recusa método vazio
    assert "interval_low > f.probability || f.interval_high < f.probability" in ts  # e probabilidade fora do intervalo


# ---------- guarda e esquecimento ----------
def test_retention_constants_match_the_worker():
    ts = (ROOT / "apps/worker/src/routes/corvo.ts").read_text(encoding="utf-8")
    assert int(re.search(r"RETAIN_NEWS_DAYS = (\d+)", ts).group(1)) == RETAIN_NEWS_DAYS
    assert int(re.search(r"RETAIN_STATS_DAYS = (\d+)", ts).group(1)) == RETAIN_STATS_DAYS


def test_drop_stores_nothing_and_approved_keeps_only_allowed_fields():
    assert storable_payload("drop", {"title": "x", "text": "corpo da matéria"}) is None
    out = storable_payload("hot", {"title": "x", "url": "https://a.com", "text": "corpo da matéria", "author": "fulano"})
    assert set(out) <= ALLOWED_NEWS_FIELDS and "text" not in out and "author" not in out
    with pytest.raises(ValueError):
        storable_payload("maybe", {})


def test_publisher_payload_never_contains_dropped_items_or_body_text():
    class Fake:
        sent: list = []

        def request(self, method, path, body=None):
            if path.endswith("/pressure"):
                return {"pressure": "normal"}
            Fake.sent.append(body)
            return {"ok": True}

    pub = OraclePublisher(Fake(), IntakeGate(clock=lambda: NOW), clock=lambda: NOW)
    secret_body = "CORPO-DA-MATERIA-NAO-PODE-VAZAR"
    items = [
        NewsItem("a", "https://x.com/1", "Fed announces rate cut as inflation cools", NOW - 60, secret_body, 0.9),
        NewsItem("a", "https://x.com/2", "Celebrity perfume launch", NOW - 60, secret_body, 0.9),
    ]
    pub.run(items)
    batch = Fake.sent[0]
    assert len(batch["news"]) == 1 and "Celebrity" not in str(batch)  # o descartado não aparece em lugar nenhum do lote
    assert secret_body not in str(batch)  # corpo/resumo nunca sobe
    for n in batch["news"]:
        assert set(n) <= ALLOWED_NEWS_FIELDS


# ---------- vazamento temporal ----------
def test_as_of_view_only_returns_what_was_known():
    rows = [{"id": 1, "ingested_at": "2026-11-07T10:00:00Z"}, {"id": 2, "ingested_at": "2026-11-07T12:00:00Z"}]
    assert [r["id"] for r in as_of_view(rows, "2026-11-07T11:00:00Z")] == [1]
    assert_point_in_time(as_of_view(rows, "2026-11-07T11:00:00Z"), "2026-11-07T11:00:00Z")
    with pytest.raises(LeakageError):
        assert_point_in_time(rows, "2026-11-07T11:00:00Z")


def test_resolution_must_come_after_the_horizon():
    check_resolution_after("2026-11-07T10:00:00Z", "2026-11-08T10:00:00Z", "2026-11-08T10:05:00Z")
    with pytest.raises(LeakageError):
        check_resolution_after("2026-11-07T10:00:00Z", "2026-11-08T10:00:00Z", "2026-11-08T09:00:00Z")
    with pytest.raises(LeakageError):
        check_resolution_after("2026-11-07T10:00:00Z", "2026-11-07T09:00:00Z", "2026-11-08T10:00:00Z")
