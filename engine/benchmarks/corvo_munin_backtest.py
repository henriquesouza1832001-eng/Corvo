"""Run a local, walk-forward CORVO Munin proof panel in dry-run mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.munin.backtest import run_backtest
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
    result = run_backtest(articles, prices, output_path=args.registry)

    print("CORVO MUNIN · PROVA LOCAL · DRY-RUN")
    print(f"Eventos: {result['events']} | perguntas: {result['questions']}")
    print(f"Previsões: {result['forecasts']} | abstenções: {result['abstentions']}")
    print(f"Resoluções: {json.dumps(result['resolution_status'], ensure_ascii=False, sort_keys=True)}")
    print(f"Resultados de previsões resolvidos: {result['resolved_forecast_outcomes']}")
    print(f"Brier: {result['brier'] if result['brier'] is not None else 'N/A (sem previsões resolvidas)'}")
    print(f"Calibração: {result['calibration_claim']}")
    print(f"Registro local: {args.registry} | run_id={result['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
