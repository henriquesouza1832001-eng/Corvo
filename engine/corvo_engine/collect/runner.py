"""Um ciclo de coleta: feeds -> (já vistos saem) -> portão -> publicação.

Uso:  py -m corvo_engine.collect --once --dry-run     (mostra o que o portão faria, sem enviar nada)
      py -m corvo_engine.collect --dry-run --quiet --dump data/corvo_corpus/corpus.jsonl --interval 600   (laço de treino: sem --once, repete)
      py -m corvo_engine.collect --interval 600       (a cada 10 min; precisa de CORVO_API_URL e CORVO_INGEST_TOKEN)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ..intake import IntakeGate, NewsItem
from ..intake.store import SeenStore, url_key
from ..oracle import HttpTransport, OraclePublisher
from .feeds import fetch_feed, load_catalog


def run_cycle(
    feeds: list[dict],
    publisher: OraclePublisher,
    store: SeenStore,
    fetcher: Callable[[dict], list[NewsItem]] = fetch_feed,
    workers: int = 6,
) -> dict:
    items: list[NewsItem] = []
    errors: dict[str, str] = {}

    def one(feed: dict):
        try:
            fetched = fetcher(feed)
            if not isinstance(fetched, list) or any(not isinstance(item, NewsItem) for item in fetched):
                raise TypeError("fetcher must return a list of NewsItem records")
            return feed["id"], fetched, None
        except Exception as exc:  # noqa: BLE001 - uma fonte fora do ar nunca derruba o ciclo
            return feed["id"], [], f"{type(exc).__name__}: {str(exc)[:120]}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fid, got, err in pool.map(one, feeds):
            if err:
                errors[fid] = err
            items.extend(got)

    fresh = [i for i in items if not store.has(url_key(i.url))]  # já tratado em ciclo anterior: nem conta como "recebida"
    official = frozenset(f["id"] for f in feeds if f.get("official"))
    result = publisher.run(fresh, official)
    store.add_many([url_key(i.url) for i in fresh])  # só marca como visto depois de o lote seguir com sucesso
    return {"feeds": len(feeds), "feeds_failed": errors, "fetched": len(items), "new": len(fresh), **result}


class _DryTransport:
    """Não envia nada: devolve pressão normal e (se não for silencioso) mostra o lote que iria ao painel."""

    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        if path.endswith("/pressure"):
            return {"pressure": "normal"}
        news = (body or {}).get("news", [])
        for n in ([] if self.quiet else news[:15]):
            print(f"  {n['verdict'].upper():6} {n['relevance']:.2f} [{(n['region'] or '-'):<14}] {n['source_id']:<14} {n['title'][:90]}")
        return {"ok": True, "dry_run": True}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Coleta global de notícias do CORVO")
    ap.add_argument("--once", action="store_true", help="roda um ciclo e sai")
    ap.add_argument("--dry-run", action="store_true", help="não envia ao painel; mostra o que o portão decidiu")
    ap.add_argument("--interval", type=int, default=600, help="segundos entre ciclos (mínimo 300)")
    ap.add_argument("--quiet", action="store_true", help="no --dry-run, não imprime os itens (só o resumo do ciclo)")
    ap.add_argument("--dump", help="arquivo .jsonl local onde gravar a decisão de cada item (inclusive descartes), para auditoria e ajuste")
    ap.add_argument("--state", default=os.environ.get("CORVO_STATE", "corvo_seen.sqlite"), help="arquivo SQLite da memória de vistos")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # títulos têm acento e emoji; o console do Windows não é UTF-8
    feeds = load_catalog()
    state = args.state
    if args.dry_run and state == "corvo_seen.sqlite":
        state = "corvo_seen_dry.sqlite"  # o teste a seco nunca mistura a memória de vistos com a do envio real
    store = SeenStore(state)
    publisher = OraclePublisher(_DryTransport(args.quiet) if args.dry_run else HttpTransport())
    interval = max(300, args.interval)  # educado com as fontes: nunca mais de uma leitura a cada 5 min por feed
    while True:
        t0 = time.time()
        summary = run_cycle(feeds, publisher, store)
        print(json.dumps(summary, ensure_ascii=False, default=str))
        if args.dump:
            with open(args.dump, "a", encoding="utf-8") as fh:
                stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                for d in publisher.last_decisions:
                    fh.write(json.dumps({"cycle_at": stamp, **d}, ensure_ascii=False) + "\n")
        if args.once:
            return 0
        time.sleep(max(1, interval - (time.time() - t0)))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
