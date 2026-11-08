"""Painel do CORVO no TERMINAL: lê o feed público da API e mostra pressão do orçamento e as últimas notícias aprovadas.
Só biblioteca padrão; pensado para a caixa (HDMI ou SSH). Não grava nada e não usa credenciais.

Uso:  python -m corvo_engine.collect.painel [--api URL] [--atualiza 30] [--once]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone

API = "https://corvo-api.henriquesouza.workers.dev"
COR = {"hot": "\033[91m", "buffer": "\033[93m"}
RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"
ROTULO = {"hot": "GRAVA", "buffer": "FILA "}


def buscar(api: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(f"{api}/api/corvo/feed", headers={"User-Agent": "corvo-painel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL fixa do projeto)
        return json.loads(r.read(2_000_000))


def _idade(iso: str, agora: datetime) -> str:
    try:
        s = int((agora - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds())
    except ValueError:
        return "?"
    return f"{s // 60}min" if s < 3600 else f"{s // 3600}h" if s < 172800 else f"{s // 86400}d"


def render(feed: dict, largura: int = 100, linhas: int = 14, agora: datetime | None = None, cor: bool = True) -> str:
    agora = agora or datetime.now(timezone.utc)
    c = (lambda k: COR.get(k, "")) if cor else (lambda k: "")
    b, d, r = (BOLD, DIM, RESET) if cor else ("", "", "")
    news = feed.get("news", [])
    orc = feed.get("budget", {})
    usado, limite = orc.get("used", 0), max(orc.get("limit", 1), 1)
    cabeca = f"CORVO · painel de terminal   {agora.strftime('%Y-%m-%d %H:%M')} UTC"[:largura]
    estado = f"pressão: {feed.get('pressure', '?')}   escritas hoje: {usado}/{limite} ({100 * usado / limite:.2f}%)   notícias: {len(news)}"[:largura]
    out = [f"{b}{cabeca}{r}", estado, "-" * min(largura, 120)]
    topo = sorted(news, key=lambda n: n.get("published_at", ""), reverse=True)[:linhas]
    for n in topo:
        v = n.get("verdict", "buffer")
        meta = f"{ROTULO.get(v, v):5} {_idade(n.get('published_at', ''), agora):>5} {(n.get('region') or '-')[:12]:12}"
        resto = max(largura - len(meta) - 2, 20)
        out.append(f"{c(v)}{meta}{r} {n.get('title', '')[:resto]}")
    if not topo:
        out.append(f"{d}(o feed está vazio: nada foi enviado ainda){r}")
    ultimo = max((n.get("ingested_at", "") for n in news), default="")
    out.append("-" * min(largura, 120))
    rodape = f"último envio ao banco: {_idade(ultimo, agora) + ' atrás' if ultimo else 'nenhum'} · só coleta, analisa e prevê; não é recomendação"[:largura]
    out.append(f"{d}{rodape}{r}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Painel do CORVO no terminal")
    ap.add_argument("--api", default=API)
    ap.add_argument("--atualiza", type=int, default=30, help="segundos entre atualizações (mínimo 15)")
    ap.add_argument("--once", action="store_true", help="mostra uma vez e sai")
    args = ap.parse_args(argv)
    espera = max(args.atualiza, 15)
    while True:
        tam = shutil.get_terminal_size((100, 30))
        try:
            texto = render(buscar(args.api), tam.columns, max(tam.lines - 6, 5), cor=sys.stdout.isatty())
        except Exception as exc:  # noqa: BLE001 (rede fora do ar não derruba o painel)
            texto = f"CORVO · sem resposta da API ({type(exc).__name__}). Tentando de novo em {espera}s."
        print(("" if args.once else "\033[2J\033[H") + texto, flush=True)
        if args.once:
            return 0
        time.sleep(espera)


if __name__ == "__main__":
    raise SystemExit(main())
