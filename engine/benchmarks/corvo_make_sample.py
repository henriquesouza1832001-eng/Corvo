"""Monta a amostra para rotulagem do portão do CORVO (estratificada, com semente fixa).

Uso (pasta engine):  py benchmarks\\corvo_make_sample.py data\\corvo_corpus\\corpus.jsonl --n 300 --seed 20261108

Dois estratos, pela decisão ATUAL do portão (só relevância, pelo título):
  - "aceito": todos (é onde mora a precisão do HOT);
  - "rejeitado": amostra aleatória (é onde mora o recall do keep; estimativa ponderada pelo peso `w` = tamanho do estrato / amostrados).
Saída: <corpus>.sample.jsonl com {idx, url, source_id, title, stratum, w, split}. O rótulo é feito SEM olhar a decisão (título só).

LACRE ESTÁVEL: a divisão ajuste (70%) / avaliação lacrada (30%) é função do HASH da URL com a semente, não da posição. Assim, gerar a
amostra de novo com um corpus maior NUNCA troca um item já rotulado de lado (sem contaminar o conjunto lacrado).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.intake.gate import GateConfig, NewsItem, Pressure, score  # noqa: E402


def split_of(url: str, seed: int) -> str:
    """'eval' (lacrado, ~30%) ou 'fit' (ajuste, ~70%), estável para a mesma URL e semente."""
    h = int(hashlib.sha1(f"{seed}:{url}".encode()).hexdigest()[:8], 16)
    return "eval" if h % 100 < 30 else "fit"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261108)
    args = ap.parse_args()
    cut = GateConfig().buffer_min[Pressure.NORMAL]
    seen, acc, rej = set(), [], []
    for line in Path(args.corpus).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        rel, _ = score(NewsItem(r["source_id"], r["url"], r["title"], 0, "", 0.75))
        (acc if rel >= cut else rej).append({"url": r["url"], "source_id": r["source_id"], "title": r["title"]})
    rng = random.Random(args.seed)
    k_rej = max(0, args.n - len(acc))
    pick_rej = rng.sample(rej, min(k_rej, len(rej)))
    rows = [dict(x, stratum="aceito", w=1.0) for x in acc] + [dict(x, stratum="rejeitado", w=round(len(rej) / max(1, len(pick_rej)), 4)) for x in pick_rej]
    rng.shuffle(rows)  # a ordem de leitura não revela o estrato
    for i, row in enumerate(rows):
        row["idx"] = i
        row["split"] = split_of(row["url"], args.seed)
    out = Path(args.corpus).with_suffix(".sample.jsonl")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"únicos {len(seen)} | aceitos {len(acc)} | rejeitados {len(rej)} | amostra {len(rows)} (rejeitados amostrados {len(pick_rej)}) -> {out}")
    print("split:", {s: sum(1 for r in rows if r['split'] == s) for s in ('fit', 'eval')})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
