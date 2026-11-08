"""Revisão do portão do CORVO sobre um corpus coletado (ferramenta de trabalho, sem rede).

Uso (na pasta engine):
    py benchmarks\\corvo_review.py data\\corvo_corpus\\corpus.jsonl            # lista as notícias ACEITAS e o resumo
    py benchmarks\\corvo_review.py data\\corvo_corpus\\corpus.jsonl --rejected  # também lista as REJEITADAS (para achar o que o filtro perde)
    py benchmarks\\corvo_review.py data\\corvo_corpus\\corpus.jsonl --source cnbc --rejected

O corpus é o .jsonl gerado por `py -m corvo_engine.collect --dry-run --dump ...`. A relevância é recalculada com o portão ATUAL, só pelo
título (o corpus não guarda o resumo): serve para ver o efeito de uma mudança de léxico sem recoletar. Cada item é contado uma vez (URL).
ATENÇÃO: mede só a RELEVÂNCIA. Ignora idade, duplicatas e cota, por isso aceita mais que o portão real (que também descarta o velho e o repetido).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corvo_engine.intake.gate import GateConfig, NewsItem, Pressure, score  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--rejected", action="store_true", help="lista também as rejeitadas")
    ap.add_argument("--source", help="limita a uma fonte (source_id)")
    ap.add_argument("--limit", type=int, default=400)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = GateConfig()
    cut, hot = cfg.buffer_min[Pressure.NORMAL], cfg.hot_min[Pressure.NORMAL]
    seen: set[str] = set()
    accepted, rejected = [], []
    for line in Path(args.corpus).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["url"] in seen or (args.source and r["source_id"] != args.source):
            continue
        seen.add(r["url"])
        rel, topics = score(NewsItem(r["source_id"], r["url"], r["title"], 0, "", 0.75))
        (accepted if rel >= cut else rejected).append((rel, topics, r["source_id"], r["title"]))

    by_topic = Counter(t for _, ts, _, _ in accepted for t in ts)
    print(f"itens únicos {len(seen)} | aceitos {len(accepted)} ({len(accepted) / max(1, len(seen)):.1%}) | HOT {sum(1 for a in accepted if a[0] >= hot)} | rejeitados {len(rejected)}")
    print("temas dos aceitos:", dict(by_topic.most_common()))
    print("\n=== ACEITAS")
    for rel, ts, src, title in sorted(accepted, reverse=True)[: args.limit]:
        print(f"{rel:.2f} {','.join(ts)[:26]:26} {src[:13]:13} | {title[:100]}")
    if args.rejected:
        print("\n=== REJEITADAS (procure aqui o que mexe em mercado e ficou de fora)")
        for rel, _, src, title in rejected[: args.limit]:
            print(f"{rel:.2f} {src[:13]:13} | {title[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
