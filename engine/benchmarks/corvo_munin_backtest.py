"""Run a local, walk-forward CORVO Munin proof panel in dry-run mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.munin.backtest import run_backtest
from corvo_engine.collect.feeds import load_catalog
from corvo_engine.munin.resolve import load_price_csv


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{number}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Local CORVO Munin backtest; no network access")
    parser.add_argument("--dry-run", action="store_true", help="required safety switch; writes only the local JSONL registry")
    parser.add_argument("--corpus", type=Path, default=root / "data/corvo_corpus/corpus.jsonl")
    parser.add_argument("--prices", type=Path, default=root / "data/corvo_corpus/precos.csv")
    parser.add_argument("--registry", type=Path, default=root / "data/corvo_corpus/previsoes.jsonl")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("--dry-run is required; this tool has no production mode")
    articles = load_jsonl(args.corpus)
    prices = load_price_csv(args.prices)
    official_sources = {feed["id"] for feed in load_catalog() if feed.get("official")}
    result = run_backtest(articles, prices, output_path=args.registry, official_sources=official_sources)

    print("CORVO MUNIN · PROVA LOCAL · DRY-RUN")
    print(f"Eventos: {result['events']} | perguntas: {result['questions']}")
    print(f"Eventos omitidos sem cycle_at: {result['events_skipped_missing_cycle_at']}")
    print(f"Previsões: {result['forecasts']} | abstenções: {result['abstentions']}")
    print(f"Resoluções: {json.dumps(result['resolution_status'], ensure_ascii=False, sort_keys=True)}")
    print(f"Resultados de previsões resolvidos: {result['resolved_forecast_outcomes']}")
    metric = lambda key: result[key] if result[key] is not None else "N/A (sem previsões resolvidas)"
    print(f"Brier: {metric('brier')}")
    print(f"Brier taxa-base: {metric('brier_taxa_base')}")
    print(f"Skill vs taxa-base: {metric('skill_vs_taxa_base')}")
    print(f"ECE: {metric('ece')}")
    print(f"Abertas até n=30 por chave: {json.dumps(result['open_to_min_n'], ensure_ascii=False, sort_keys=True)}")
    print(f"Calibração: {result['calibration_claim']}")
    print(f"Registro local: {args.registry} | run_id={result['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
