"""Ajudante de rotulagem do portão do CORVO. Mostra títulos SEM a decisão do portão e grava os rótulos com segurança.

Uso (pasta engine; <amostra> = o .sample.jsonl gerado por corvo_make_sample.py):
    py benchmarks\\corvo_label.py status <amostra>
    py benchmarks\\corvo_label.py show   <amostra> --from 0 --count 40
    py benchmarks\\corvo_label.py apply  <amostra> --from 0 --codes KMDKKMD...    # um código por item, na ordem de idx a partir de --from

Códigos: K = keep (efeito plausível em preço) · M = marginal · D = drop (sem efeito). Use "-" para PULAR um item. Rubrica completa em
docs/corvo/HUGIN_MUNIN_TREINO.md (seção 3.5). Rotule pelo CONTEÚDO, nunca pelo que o portão faria. Os rótulos vão para <amostra sem .sample>.labels.jsonl
e levam junto o estrato, o peso e o lado (ajuste ou lacrado) para a medição ponderada. Reaplicar sobre o mesmo item sobrescreve o rótulo.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CODES = {"K": "keep", "M": "marginal", "D": "drop"}


def paths(sample: str) -> tuple[Path, Path]:
    s = Path(sample)
    return s, s.with_name(s.name.replace(".sample.jsonl", "") + ".labels.jsonl")


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "show", "apply"])
    ap.add_argument("sample")
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--codes", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sample_p, labels_p = paths(args.sample)
    sample = load(sample_p)
    labels = {r["url"]: r for r in load(labels_p)}
    by_idx = {r["idx"]: r for r in sample}

    if args.cmd == "status":
        done = [r for r in sample if r["url"] in labels]
        for sp in ("fit", "eval"):
            tot = [r for r in sample if r["split"] == sp]
            got = [r for r in tot if r["url"] in labels]
            print(f"{sp:5} rotulados {len(got):4}/{len(tot):4}")
        from collections import Counter
        print("rótulos:", dict(Counter(labels[r["url"]]["label"] for r in done)))
        nxt = next((r["idx"] for r in sample if r["url"] not in labels), None)
        print(f"total {len(done)}/{len(sample)} | próximo idx sem rótulo: {nxt}")
        return 0

    if args.cmd == "show":
        for i in range(args.start, min(args.start + args.count, len(sample))):
            r = by_idx[i]
            mark = labels[r["url"]]["label"][0].upper() if r["url"] in labels else " "
            print(f"{i:4} [{mark}] {r['source_id'][:13]:13} | {r['title'][:140]}")
        return 0

    codes = args.codes.strip()
    if not codes:
        print("faltou --codes")
        return 2
    if args.start + len(codes) > len(sample):
        print(f"códigos demais: {len(codes)} a partir de {args.start}, mas a amostra tem {len(sample)} itens")
        return 2
    bad = [c for c in codes if c not in CODES and c != "-"]
    if bad:
        print(f"código inválido: {bad}. Use K, M, D ou - para pular")
        return 2
    n = 0
    for off, c in enumerate(codes):
        if c == "-":
            continue
        r = by_idx[args.start + off]
        labels[r["url"]] = {"url": r["url"], "source_id": r["source_id"], "title": r["title"], "label": CODES[c],
                            "stratum": r["stratum"], "w": r["w"], "split": r["split"]}
        n += 1
    labels_p.write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in labels.values()) + "\n", encoding="utf-8")
    print(f"{n} rótulo(s) gravados em {labels_p} (total {len(labels)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
