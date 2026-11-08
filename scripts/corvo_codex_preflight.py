"""Conferência de prontidão do Codex para o treino noturno do CORVO. Uso (raiz do repositório):

    py scripts/corvo_codex_preflight.py            # confere, prepara (amostra, quadro de agentes) e imprime o prompt de partida
    py scripts/corvo_codex_preflight.py --check    # só confere, não escreve nada nem se registra no quadro

Sai com código 0 se estiver PRONTO e 1 se faltar algo, dizendo o que fazer. Nunca lê segredos nem fala com a API.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
CORPUS_DIR = ENGINE / "data" / "corvo_corpus"
CORPUS = CORPUS_DIR / "corpus.jsonl"
SAMPLE = CORPUS_DIR / "corpus.sample.jsonl"
AGENT = "codex-noite"
CLAIMS = ["engine/corvo_engine/intake", "engine/corvo_engine/collect", "engine/corvo_engine/munin", "engine/corvo_engine/oracle",
          "engine/benchmarks", "engine/tests", "docs/corvo"]
TESTS = ["tests/test_intake_gate.py", "tests/test_oracle_publisher.py", "tests/test_collect_runner.py", "tests/test_munin.py", "tests/test_corvo_bench.py"]
MIN_FOR_LABELING = 1500  # itens únicos para começar a rotular (brief, Fase 2)

problems: list[str] = []


def sh(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, f"{type(exc).__name__}: {exc}"


def line(ok: bool | None, title: str, detail: str = "") -> None:
    mark = {True: "OK   ", False: "FALTA", None: "AVISO"}[ok]
    print(f"[{mark}] {title}" + (f"  ({detail})" if detail else ""))
    if ok is False:
        problems.append(title)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="só confere; não cria amostra nem se registra no quadro")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("== CORVO · prontidão do Codex ==\n")

    _, branch = sh(["git", "branch", "--show-current"])
    line(branch == "hen", "branch é a hen", f"atual: {branch}")
    _, dirty = sh(["git", "status", "--porcelain"])
    own = [l for l in dirty.splitlines() if not re.search(r"engine/data/|corvo_seen|\.sqlite", l)]
    line(None if own else True, "árvore de trabalho limpa", f"{len(own)} alteração(ões) pendente(s)" if own else "")
    sh(["git", "fetch", "-q"])
    _, sb = sh(["git", "status", "-sb"])
    behind = re.search(r"behind (\d+)", sb.splitlines()[0] if sb else "")
    line(None if behind else True, "branch em dia com a origem", f"atrás {behind.group(1)}: faça git pull" if behind else "")

    rc, out = sh([sys.executable, "-m", "pytest", *TESTS, "-q", "-p", "no:cacheprovider"], cwd=ENGINE)
    summary = out.splitlines()[-1] if out else ""
    line(rc == 0, "testes do portão, publicador, coleta, Munin e ferramentas", summary)

    for rel, what in (("docs/corvo/CODEX_BRIEF_COLETA.md", "briefing"), ("docs/corvo/HUGIN_MUNIN_TREINO.md", "guia Hugin e Munin"),
                      ("engine/AGENTS.md", "instruções do Codex para o engine"), ("engine/benchmarks/corvo_gate_eval.py", "ferramenta de medição"),
                      ("engine/benchmarks/corvo_label.py", "ferramenta de rotulagem"), ("engine/benchmarks/corvo_make_sample.py", "montador de amostra")):
        line((ROOT / rel).exists(), f"existe {what}", rel)

    uniq, by_src = 0, {}
    if CORPUS.exists():
        urls = set()
        for ln in CORPUS.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                if r["url"] not in urls:
                    urls.add(r["url"])
                    by_src[r["source_id"]] = by_src.get(r["source_id"], 0) + 1
        uniq = len(urls)
    line(CORPUS.exists(), "corpus coletado", f"{uniq} itens únicos de {len(by_src)} fontes" if CORPUS.exists() else
         "rode scripts\\corvo_corpus_loop.ps1 numa janela do PowerShell")
    if CORPUS.exists() and uniq < MIN_FOR_LABELING:
        line(None, f"corpus ainda abaixo de {MIN_FOR_LABELING} itens", "o Codex pode começar pela Fase 0 e T0; a rotulagem espera o corpus crescer")

    if SAMPLE.exists():
        n = len(SAMPLE.read_text(encoding="utf-8").splitlines())
        line(True, "amostra de rotulagem existe", f"{n} itens; a divisão 70/30 é estável por URL, pode regenerar sem contaminar")
    elif not args.check and uniq >= 300:
        rc, out = sh([sys.executable, "benchmarks/corvo_make_sample.py", str(CORPUS), "--n", "300", "--seed", "20261108"], cwd=ENGINE)
        line(rc == 0, "amostra de rotulagem criada", out.splitlines()[0] if out else "")
    else:
        line(None, "amostra de rotulagem ainda não criada", "o Codex cria na Fase 2 (precisa de >= 300 itens únicos)")

    if not args.check:
        rc, _ = sh([sys.executable, "scripts/agentbus.py", "register", AGENT, "--role", "coleta e treino do portao CORVO"])
        rc2, out = sh([sys.executable, "scripts/agentbus.py", "claim", AGENT, *CLAIMS])
        line(rc == 0 and rc2 == 0, f"agente {AGENT} registrado e pastas reservadas no quadro", "CONFLITO" if "CONFLITO" in out else "")
        rc3, out3 = sh(["sh", "scripts/gitcrypt_check.sh"])
        line(rc3 == 0, "nenhum segredo em texto puro no índice do git", out3.splitlines()[-1] if out3 else "")

    brief = (ROOT / "docs/corvo/CODEX_BRIEF_COLETA.md").read_text(encoding="utf-8")
    m = re.search(r"```text\n(.*?)```", brief, re.S)
    print("\n" + ("=" * 64))
    if problems:
        print(f"NÃO PRONTO. Falta resolver {len(problems)} item(ns) marcados FALTA acima.")
    else:
        print("PRONTO. Abra o Codex na pasta do repositório, na branch hen, e cole o prompt abaixo:\n")
        print(m.group(1).strip() if m else "(prompt de partida não encontrado no briefing)")
    print("=" * 64)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
