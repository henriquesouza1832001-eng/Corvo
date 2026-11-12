"""Resume the in-memory CORVO → MNEME contract preview for an existing local corpus.

Usage (from ``engine``):
    py benchmarks/corvo_mneme_preview.py --dry-run data/corvo_corpus/corpus.jsonl

Reads no labels, makes no network requests, and writes no records or files.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.collect.feeds import load_catalog  # noqa: E402
from corvo_engine.munin.mneme_export import exportar_para_mneme  # noqa: E402
from corvo_engine.oracle.publisher import classify_kind  # noqa: E402


def resumir(caminho: Path) -> dict:
    feeds = {str(feed["id"]): feed for feed in load_catalog()}
    decisoes = []
    with caminho.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            if not linha.strip():
                continue
            row = json.loads(linha)
            if not isinstance(row, dict):
                continue
            decisao = dict(row)
            fonte = feeds.get(str(decisao.get("source_id") or ""), {})
            oficial = fonte.get("official") is True
            decisao["source_is_official"] = oficial
            decisao["source_reliability"] = fonte.get("reliability")
            decisao["kind"] = classify_kind(str(decisao.get("title") or ""), oficial)
            decisoes.append(decisao)

    export = exportar_para_mneme(decisoes)
    artigos = export["articles"]
    eventos = export["events"]
    return {
        "preview_version": export["preview_version"],
        "input_records": len(decisoes),
        "excluded_by_hugin": export["excluded_by_hugin"],
        "invalid_accepted": export["invalid_accepted"],
        "articles_previewed": len(artigos),
        "events_previewed": len(eventos),
        "articles_missing_received_at": sum(article["recebido_em"] is None for article in artigos),
        "events_missing_available_at": sum(event["available_at"] is None for event in eventos),
        "event_coverage_patterns": dict(Counter(event["coverage_pattern"] for event in eventos)),
        "official_publications_not_claim_facts": sum(article["tipo_evidencia"] == "publicacao_institucional" for article in artigos),
        "source_independence_assessed": False,
        "stored_or_sent": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="obrigatório: só calcula e imprime contagens agregadas")
    parser.add_argument("corpus", type=Path, help="JSONL local de decisões Hugin; nenhuma chamada externa é feita")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("use --dry-run; o preview nunca grava nem envia dados")
    if not args.corpus.is_file():
        parser.error(f"arquivo não encontrado: {args.corpus}")
    print(json.dumps(resumir(args.corpus), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
