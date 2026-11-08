"""Mede o portão do CORVO contra os rótulos humanos, por conjunto (ajuste e LACRADO), com ponderação dos estratos.

Uso (pasta engine):
    py benchmarks\\corvo_gate_eval.py data\\corvo_corpus\\corpus.labels.jsonl              # os dois conjuntos
    py benchmarks\\corvo_gate_eval.py data\\corvo_corpus\\corpus.labels.jsonl --split eval # só o lacrado (use UMA vez por rodada de ajuste)
    py benchmarks\\corvo_gate_eval.py data\\corvo_corpus\\corpus.labels.jsonl --json       # saída para o relatório

O veredito é recalculado com o portão ATUAL (`score()` do título + cortes da pressão normal). Mede só RELEVÂNCIA (ignora idade, duplicata e
cota). Cada rótulo carrega o peso `w` do seu estrato (aceito = 1; rejeitado = rejeitados/amostrados), que corrige a amostragem desigual:
sem ele, o recall e a taxa de keep descartado ficariam errados.

Métricas (todas ponderadas):
  precisao_hot        fração do HOT que é keep                  (meta >= 0,85)
  recall_keep         fração dos keep que ficaram HOT ou BUFFER (meta >= 0,90)
  keep_descartado     1 - recall_keep (o PIOR erro)
  drop_gravado        fração do gravado que é drop              (o que polui o banco)
  keep_entre_gravadas fração do gravado que é keep              (meta >= 0,85)
  hot_entre_aceitos   fração do gravado que é HOT               (meta <= 0,25)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.intake.gate import GateConfig, NewsItem, Pressure, score  # noqa: E402

LABELS = ("keep", "marginal", "drop")
VERDICTS = ("hot", "buffer", "drop")


def verdict_of(title: str, source_id: str = "x", cfg: GateConfig | None = None) -> str:
    cfg = cfg or GateConfig()
    rel, _ = score(NewsItem(source_id, "https://x/", title, 0, "", 0.75))
    if rel < cfg.buffer_min[Pressure.NORMAL]:
        return "drop"
    return "hot" if rel >= cfg.hot_min[Pressure.NORMAL] else "buffer"


def measure(rows: list[dict], cfg: GateConfig | None = None) -> dict:
    m = {(l, v): 0.0 for l in LABELS for v in VERDICTS}
    n = {(l, v): 0 for l in LABELS for v in VERDICTS}
    for r in rows:
        v = verdict_of(r["title"], r.get("source_id", "x"), cfg)
        m[(r["label"], v)] += float(r.get("w", 1.0))
        n[(r["label"], v)] += 1

    def s(label=None, verdict=None):
        return sum(w for (l, vv), w in m.items() if (label is None or l == label) and (verdict is None or vv == verdict))

    def ratio(a, b):
        return a / b if b else None

    stored = s(verdict="hot") + s(verdict="buffer")
    keep_total = s(label="keep")
    keep_stored = s("keep", "hot") + s("keep", "buffer")
    return {
        "n": len(rows),
        "n_keep": sum(1 for r in rows if r["label"] == "keep"),
        "matriz_ponderada": {l: {v: round(m[(l, v)], 2) for v in VERDICTS} for l in LABELS},
        "matriz_contagem": {l: {v: n[(l, v)] for v in VERDICTS} for l in LABELS},
        "precisao_hot": ratio(s("keep", "hot"), s(verdict="hot")),
        "recall_keep": ratio(keep_stored, keep_total),
        "keep_descartado": None if not keep_total else 1 - keep_stored / keep_total,
        "drop_gravado": ratio(s("drop", "hot") + s("drop", "buffer"), stored),
        "keep_entre_gravadas": ratio(keep_stored, stored),
        "hot_entre_aceitos": ratio(s(verdict="hot"), stored),
    }


def fmt(x) -> str:
    return "n/d" if x is None else f"{x:.3f}"


def show(name: str, r: dict) -> None:
    print(f"\n=== {name}  (itens {r['n']}, keep {r['n_keep']})")
    if r["n_keep"] < 30:
        print("   AVISO: menos de 30 keep neste conjunto; recall e precisão ficam instáveis. Rotule mais.")
    print("   matriz ponderada        hot  buffer    drop")
    for l in LABELS:
        mm = r["matriz_ponderada"][l]
        print(f"   {l:9}           {mm['hot']:7.1f} {mm['buffer']:7.1f} {mm['drop']:7.1f}")
    for k, meta in (("precisao_hot", ">= 0,85"), ("recall_keep", ">= 0,90"), ("keep_descartado", "o pior erro"), ("drop_gravado", "polui o banco"),
                    ("keep_entre_gravadas", ">= 0,85"), ("hot_entre_aceitos", "<= 0,25")):
        print(f"   {k:20} {fmt(r[k]):>7}   ({meta})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--split", choices=["fit", "eval", "both"], default="both")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = [json.loads(x) for x in Path(args.labels).read_text(encoding="utf-8").splitlines() if x.strip()]
    out = {}
    for sp in (("fit", "eval") if args.split == "both" else (args.split,)):
        out[sp] = measure([r for r in rows if r.get("split") == sp])
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for sp, r in out.items():
            show("AJUSTE" if sp == "fit" else "AVALIAÇÃO LACRADA", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
