"""Freio de banco do CORVO: projeta quantas linhas por dia o portão ATUAL gravaria e falha se passar do limite seguro.

Uso (pasta engine):
    py benchmarks\\corvo_budget_check.py data\\corvo_corpus\\corpus.jsonl
    py benchmarks\\corvo_budget_check.py data\\corvo_corpus\\corpus.jsonl --json

Rode ANTES DE CADA COMMIT que mexa em `intake/gate.py`, no catálogo de feeds ou na coleta. Sai com código 1 se algum limite for violado.

Como estima (conservador, propositalmente pessimista):
  1. Volume por dia = itens únicos com `published_at` nas últimas 24 h do corpus (o histórico do 1º ciclo não conta como volume diário).
  2. Aceitos por dia = volume x fração aceita só pela RELEVÂNCIA do portão atual (ignora idade, duplicata e cota, que só reduzem).
  3. Linhas por dia = 2 x aceitos (registro + índice, como o Worker conta) + 144 x 3 (um ciclo a cada 10 min atualiza estatística da hora,
     orçamento e contador).
  4. Cenário 5x: volume 5 vezes maior (fonte nova, dia de notícia pesada), a parte fixa não escala.

Limites (Turso grátis = 10 milhões de escritas/mês; teto de projeto do Worker = 300 mil/dia):
  normal  <= 5.000 linhas/dia        5x  <= 25.000 linhas/dia        e a fração aceita <= 12% do que é lido
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.intake.gate import GateConfig, NewsItem, Pressure, score  # noqa: E402

LIMIT_NORMAL = 5_000
LIMIT_5X = 25_000
LIMIT_ACCEPT_RATE = 0.12
CYCLES_PER_DAY = 144  # um ciclo a cada 10 min
FIXED_ROWS_PER_CYCLE = 3
HARD_CAP = 300_000  # DAILY_WRITE_LIMIT do Worker


def _ts(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)


def project(rows: list[dict], cfg: GateConfig | None = None) -> dict:
    cfg = cfg or GateConfig()
    cut, hot = cfg.buffer_min[Pressure.NORMAL], cfg.hot_min[Pressure.NORMAL]
    uniq: dict[str, dict] = {}
    for r in rows:
        uniq.setdefault(r["url"], r)
    if not uniq:
        raise ValueError("corpus vazio")
    latest = max(_ts(r["published_at"]) for r in uniq.values())
    window = [r for r in uniq.values() if _ts(r["published_at"]) >= latest - timedelta(hours=24)]
    accepted = hot_n = 0
    for r in window:
        rel, _ = score(NewsItem(r["source_id"], r["url"], r["title"], 0, "", 0.75))
        if rel >= cut:
            accepted += 1
            hot_n += rel >= hot
    volume = len(window)
    rate = accepted / volume if volume else 0.0
    fixed = CYCLES_PER_DAY * FIXED_ROWS_PER_CYCLE
    rows_normal = 2 * accepted + fixed
    rows_5x = 2 * accepted * 5 + fixed
    checks = {
        "linhas_por_dia": (rows_normal, LIMIT_NORMAL, rows_normal <= LIMIT_NORMAL),
        "linhas_por_dia_5x": (rows_5x, LIMIT_5X, rows_5x <= LIMIT_5X),
        "fracao_aceita": (round(rate, 4), LIMIT_ACCEPT_RATE, rate <= LIMIT_ACCEPT_RATE),
        "abaixo_do_teto_do_worker": (rows_5x, HARD_CAP, rows_5x <= HARD_CAP),
    }
    return {
        "itens_unicos_no_corpus": len(uniq),
        "volume_24h": volume,
        "aceitos_24h": accepted,
        "hot_entre_aceitos": round(hot_n / accepted, 3) if accepted else None,
        "limites": {k: {"valor": v[0], "limite": v[1], "ok": v[2]} for k, v in checks.items()},
        "ok": all(v[2] for v in checks.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = [json.loads(x) for x in Path(args.corpus).read_text(encoding="utf-8").splitlines() if x.strip()]
    res = project(rows)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"corpus: {res['itens_unicos_no_corpus']} itens únicos | volume 24 h: {res['volume_24h']} | aceitos 24 h: {res['aceitos_24h']} "
              f"| HOT entre aceitos: {res['hot_entre_aceitos']}")
        for k, v in res["limites"].items():
            print(f"  [{'OK   ' if v['ok'] else 'ESTOURA'}] {k:26} {v['valor']}  (limite {v['limite']})")
        print("RESULTADO:", "dentro dos limites seguros" if res["ok"] else "FORA DOS LIMITES: NÃO FAÇA COMMIT desta mudança")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
