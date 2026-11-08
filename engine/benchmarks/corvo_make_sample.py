"""Monta a amostra para rotulagem do portão do CORVO (estratificada, com semente fixa).

Uso (pasta engine):  py benchmarks\\corvo_make_sample.py data\\corvo_corpus\\filtro.jsonl --n 300 --seed 20261108

Dois estratos, pela decisão ATUAL do portão (só relevância, pelo título):
  - "aceito": todos (é onde mora a precisão do HOT);
  - "rejeitado": amostra aleatória (é onde mora o recall do keep; estimativa ponderada pelo peso `w` = tamanho do estrato / amostrados).
Saída: <corpus>.sample.jsonl com {idx, url, source_id, title, stratum, w}. O rótulo é feito SEM olhar a decisão (use o título só).
Divide em ajuste (70%) e avaliação LACRADA (30%) pela mesma semente: a divisão é gravada em `split`.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.intake.gate import GateConfig, NewsItem, Pressure, score  # noqa: E402


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
        row["split"] = "eval" if rng.random() < 0.3 else "fit"
    out = Path(args.corpus).with_suffix(".sample.jsonl")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"únicos {len(seen)} | aceitos {len(acc)} | rejeitados {len(rej)} | amostra {len(rows)} (rejeitados amostrados {len(pick_rej)}) -> {out}")
    print("split:", {s: sum(1 for r in rows if r['split'] == s) for s in ('fit', 'eval')})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
