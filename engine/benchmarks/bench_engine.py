"""Benchmark das etapas do motor (NÃO roda no CI normal). Mede tempo, vazão e memória de pico por etapa e tamanho (100 a 100 mil).

    cd engine && py -m benchmarks.bench_engine --sizes 100,1000,10000 --budget 20 --out bench.json

Regras: sem otimização prematura (só mede); o ambiente é identificado no resultado (Python, SO, CPUs) porque número sem ambiente não vale;
etapa que estoura o orçamento de tempo num tamanho NÃO é rodada nos maiores (`SKIPPED_BUDGET`: é um dado, não um erro); p50/p95/p99 só
quando há repetições suficientes (pequenos tamanhos). Dados sintéticos determinísticos.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timedelta, timezone

from corvo_engine.models import Signal
from corvo_engine.processing.clustering import cluster_signals
from corvo_engine.research.history import build_observations
from corvo_engine.research.provenance import provenance
from corvo_engine.research.sentinel import detect_candidates
from corvo_engine.source_freshness import SourceReading, assess

NOW = datetime(2026, 10, 7, 21, 0, tzinfo=timezone.utc)
WORDS = ("rua avenida ponte viaduto praça bairro escola mercado posto terminal rodovia túnel obra galeria represa córrego favela condomínio hospital "
         "aeroporto estação prefeitura bombeiros moradores motoristas comerciantes alagamento acidente interdição apagão protesto incêndio deslizamento").split()
CLASSES = ["NEWS_HIGH", "NEWS_REGIONAL", "NEWS_REGIONAL", "SOCIAL", "OFFICIAL"]


def make_signals(n: int, seed_dup: int = 0) -> list[Signal]:
    out = []
    for i in range(n):
        ts = NOW - timedelta(minutes=(i * 7) % 240)
        title = " ".join(WORDS[(i * k + k) % len(WORDS)] for k in (3, 5, 7, 11)) + f" caso {i}"
        out.append(Signal(signal_id=str(i), source_id=f"fonte{i % 300}", source_class=CLASSES[i % 5], timestamp=ts, collected_at=ts, title=title,
                          category=("WEATHER", "TRAFFIC", "INFRASTRUCTURE")[i % 3], hash=f"h{i}", state=("MG", "SP", "RJ", "BA")[i % 4]))
    return out


def history_rows(days: int = 35) -> list[dict]:
    rows, end = [], NOW.replace(minute=0)
    for scope in ("BR", "UF:MG", "UF:SP", "UF:RJ", "UF:BA"):
        for cat in ("WEATHER", "TRAFFIC", "INFRASTRUCTURE"):
            for h in range(1, 24 * days):
                rows.append({"scope": scope, "category": cat, "source_class": "NEWS_HIGH", "hour": (end - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "signals": 5, "sources": 3, "duplicates": 0})
    return rows


def stages(sigs: list[Signal], rows: list[dict]) -> dict:
    return {
        "provenance": lambda: provenance(sigs),
        "clustering_v1": lambda: cluster_signals(sigs),
        "observations": lambda: build_observations(sigs, {}, NOW + timedelta(hours=1)),
        "sentinel_detect": lambda: detect_candidates(sigs, rows, NOW),
        "freshness_assess": lambda: [assess({"source_class": "NEWS_HIGH"}, SourceReading(s.source_id, "ONLINE", True, (s.hash,), (s.timestamp,)), NOW) for s in sigs],
    }


def measure(fn, repeats: int, with_memory: bool) -> dict:
    times = []
    peak = None
    for k in range(repeats):
        if with_memory and k == 0:
            tracemalloc.start()
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
        if with_memory and k == 0:
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
    out = {"runs": repeats, "seconds_min": round(min(times), 4), "seconds_median": round(statistics.median(times), 4), "peak_memory_mb": round(peak / 1e6, 1) if peak else None}
    if repeats >= 5:
        qs = sorted(times)
        pick = lambda q: qs[min(len(qs) - 1, int(q * len(qs)))]  # noqa: E731
        out.update({"p50": round(pick(0.5), 4), "p95": round(pick(0.95), 4), "p99": round(pick(0.99), 4)})
    return out


def run(sizes: list[int], budget_s: float) -> dict:
    rows = history_rows()
    skipped: set[str] = set()
    result: dict = {"environment": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count(),
                                    "processor": platform.processor()}, "budget_seconds_per_stage": budget_s, "sizes": {}}
    for n in sizes:
        sigs = make_signals(n)
        per = {}
        for name, fn in stages(sigs, rows).items():
            if name in skipped:
                per[name] = {"status": "SKIPPED_BUDGET"}
                continue
            repeats = 7 if n <= 1000 else 1
            m = measure(fn, repeats, with_memory=n <= 10000)
            m["throughput_per_s"] = round(n / m["seconds_median"], 1) if m["seconds_median"] else None
            m["status"] = "OK"
            per[name] = m
            if m["seconds_median"] > budget_s / 5:  # o próximo tamanho (10x) provavelmente estoura: não rodar
                skipped.add(name)
        result["sizes"][str(n)] = per
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="100,1000,10000")
    ap.add_argument("--budget", type=float, default=20.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run([int(x) for x in a.sizes.split(",")], a.budget)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
