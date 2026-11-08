"""Coleta de PREÇOS de referência para conferir as previsões do Munin (só leitura de dado público, local, sem chave).

Fontes (fichas em docs/sources/SOURCES.md):
- Cripto: velas de 1 h do espelho público de dados de mercado da Binance (`data-api.binance.vision`, sem conta nem chave).
- Câmbio: taxas de referência diárias do BCE, servidas pela Frankfurter (`api.frankfurter.dev`).

Saída: CSV `ativo,timestamp_utc,fechamento`, sem repetição, em ordem de tempo. `timestamp_utc` é o instante em que o preço PASSOU A
SER CONHECIDO (fechamento da vela; câmbio diário às 16:00 UTC, depois da divulgação do BCE), para não vazar o futuro.
Rodar de novo só acrescenta o que falta (idempotente); a primeira rodada traz o histórico recente de uma vez.
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

BINANCE = "https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1h&limit={limit}"
FRANKFURTER = "https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols={symbols}"
CRYPTO = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT", "XRP": "XRPUSDT"}
FX = ("EUR", "BRL", "JPY", "GBP", "CNY")  # USD contra cada uma: ativo "USDBRL" etc.
HEADER = ["ativo", "timestamp_utc", "fechamento"]
USER_AGENT = "corvo-prices/1.0 (coleta de dados publicos; sem credenciais)"

Fetcher = Callable[[str], bytes]


def http_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (URLs fixas acima)
        return resp.read(5_000_000)


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def crypto_rows(asset: str, raw: bytes, now: datetime) -> list[tuple[str, str, float]]:
    """Velas FECHADAS de 1 h -> (ativo, instante do fechamento, preço de fechamento). A vela em andamento é ignorada."""
    out = []
    for k in json.loads(raw):
        close_time = datetime.fromtimestamp((int(k[6]) + 1) / 1000, tz=timezone.utc)  # 1 ms depois do fim da vela
        if close_time > now:
            continue
        price = float(k[4])
        if price > 0:
            out.append((asset, _iso(close_time), price))
    return out


def fx_rows(raw: bytes, now: datetime) -> list[tuple[str, str, float]]:
    """Taxas diárias do BCE -> um ponto por dia às 16:00 UTC (já divulgadas); dia futuro ou sem taxa é ignorado."""
    out = []
    for day, rates in json.loads(raw).get("rates", {}).items():
        t = datetime.fromisoformat(day).replace(hour=16, tzinfo=timezone.utc)
        if t > now:
            continue
        for ccy, value in rates.items():
            if ccy in FX and float(value) > 0:
                out.append((f"USD{ccy}", _iso(t), float(value)))
    return out


def read_existing(path: Path) -> dict[tuple[str, str], float]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {(r["ativo"], r["timestamp_utc"]): float(r["fechamento"]) for r in csv.DictReader(f)}


def write_all(path: Path, data: dict[tuple[str, str], float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for (asset, ts), price in sorted(data.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            w.writerow([asset, ts, repr(price)])
    tmp.replace(path)


def collect(out: Path, fetcher: Fetcher = http_fetch, now: datetime | None = None, crypto_candles: int = 1000, fx_days: int = 60) -> dict:
    """Busca tudo, junta ao que já existe e grava. Falha de uma fonte NÃO derruba as outras (devolve o erro por ativo)."""
    now = now or datetime.now(timezone.utc)
    data = read_existing(out)
    before = len(data)
    errors: dict[str, str] = {}
    for asset, symbol in CRYPTO.items():
        try:
            for a, ts, p in crypto_rows(asset, fetcher(BINANCE.format(symbol=symbol, limit=crypto_candles)), now):
                data[(a, ts)] = p
        except Exception as exc:  # noqa: BLE001 (isola a falha por ativo)
            errors[asset] = type(exc).__name__
    try:
        start = (now - timedelta(days=fx_days)).date().isoformat()
        for a, ts, p in fx_rows(fetcher(FRANKFURTER.format(start=start, end=now.date().isoformat(), symbols=",".join(FX))), now):
            data[(a, ts)] = p
    except Exception as exc:  # noqa: BLE001
        errors["FX"] = type(exc).__name__
    write_all(out, data)
    return {"linhas": len(data), "novas": len(data) - before, "ativos": sorted({a for a, _ in data}), "erros": errors}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Coleta preços de referência para o Munin conferir previsões (local).")
    ap.add_argument("--out", type=Path, default=Path("data/corvo_corpus/precos.csv"))
    ap.add_argument("--candles", type=int, default=1000, help="velas de 1 h por cripto (máx. 1000 = cerca de 41 dias)")
    ap.add_argument("--fx-days", type=int, default=60)
    args = ap.parse_args(argv)
    res = collect(args.out, crypto_candles=min(max(args.candles, 1), 1000), fx_days=max(args.fx_days, 1))
    print(json.dumps(res, ensure_ascii=False))
    return 0 if not res["erros"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
