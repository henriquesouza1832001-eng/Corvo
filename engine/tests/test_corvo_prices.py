import csv
import json
from datetime import datetime, timezone

from corvo_engine.collect import prices

NOW = datetime(2026, 11, 8, 12, 30, tzinfo=timezone.utc)


def _kline(open_ms: int, close: str) -> list:
    return [open_ms, "1", "2", "0.5", close, "10", open_ms + 3_599_999, "0", 1, "0", "0", "0"]


def _ms(h: int) -> int:
    return int(datetime(2026, 11, 8, h, tzinfo=timezone.utc).timestamp() * 1000)


def fake(url: str) -> bytes:
    if "binance" in url:
        return json.dumps([_kline(_ms(10), "100.5"), _kline(_ms(11), "101.0"), _kline(_ms(12), "102.0")]).encode()  # a das 12h ainda está aberta
    return json.dumps({"rates": {"2026-11-06": {"BRL": 5.5, "EUR": 0.9, "XXX": 1.0}, "2026-11-09": {"BRL": 9.9}}}).encode()


def test_crypto_ignora_vela_aberta_e_usa_instante_de_fechamento():
    rows = prices.crypto_rows("BTC", fake("binance"), NOW)
    assert [r[1] for r in rows] == ["2026-11-08T11:00:00Z", "2026-11-08T12:00:00Z"]
    assert rows[0][2] == 100.5


def test_cambio_so_com_ativos_conhecidos_e_sem_dia_futuro():
    rows = prices.fx_rows(fake("frankfurter"), NOW)
    assert {r[0] for r in rows} == {"USDBRL", "USDEUR"}
    assert all(r[1] == "2026-11-06T16:00:00Z" for r in rows)


def test_coleta_e_idempotente_e_ordenada(tmp_path):
    out = tmp_path / "precos.csv"
    r1 = prices.collect(out, fetcher=fake, now=NOW)
    r2 = prices.collect(out, fetcher=fake, now=NOW)
    assert r1["novas"] > 0 and r2["novas"] == 0 and not r1["erros"]
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == r1["linhas"]
    keys = [(r["ativo"], r["timestamp_utc"]) for r in rows]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)


def test_falha_de_uma_fonte_nao_derruba_as_outras(tmp_path):
    def flaky(url: str) -> bytes:
        if "SOLUSDT" in url:
            raise OSError("fora do ar")
        return fake(url)

    res = prices.collect(tmp_path / "p.csv", fetcher=flaky, now=NOW)
    assert res["erros"] == {"SOL": "OSError"} and "BTC" in res["ativos"] and "USDBRL" in res["ativos"]
