"""Uso: py -m corvo_engine.oracle itens.jsonl   (uma notícia por linha; "-" lê da entrada padrão)

Cada linha: {"source_id","url","title","published_at" (ISO ou epoch),"text","source_reliability"}.
Uso avançado e testes: publica notícias de um arquivo. A coleta normal é `python -m corvo_engine.collect`.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

from ..intake import NewsItem
from .publisher import HttpTransport, OraclePublisher


def _epoch(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    lines = sys.stdin if argv[0] == "-" else open(argv[0], encoding="utf-8")
    items = []
    for ln in lines:
        if not ln.strip():
            continue
        d = json.loads(ln)
        items.append(NewsItem(d["source_id"], d["url"], d["title"], _epoch(d["published_at"]), d.get("text", ""), float(d.get("source_reliability", 0.5))))
    print(json.dumps(OraclePublisher(HttpTransport()).run(items), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
