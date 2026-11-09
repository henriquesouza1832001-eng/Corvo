"""Agente da CAIXA: só faz requisições de SAÍDA. A cada ~30 s informa o estado à API e recebe, se houver, UM comando de uma lista fechada
(ligar, desligar, reiniciar o coletor, atualizar, reiniciar a caixa). Nada fora da lista é executado, e nunca há `shell=True`.
Só biblioteca padrão. Roda sob `deploy/box/agente.sh` (que o reinicia se ele sair, por exemplo depois de `update`).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
CORVO_SH = str(ROOT / "deploy" / "box" / "corvo.sh")
LOG = ROOT / "engine" / "data" / "corvo_corpus" / "caixa.log"
ENV_FILE = ROOT / "deploy" / "box" / ".env"
USER_AGENT = "corvo-agente/1.0"

# Lista fechada: ação -> argumentos. O que vem da API é só a CHAVE; o comando real é fixo aqui.
ACOES: dict[str, list[str]] = {
    "on": ["sh", CORVO_SH, "on"],
    "off": ["sh", CORVO_SH, "off"],
    "restart": ["sh", CORVO_SH, "restart"],
    "update": ["sh", CORVO_SH, "atualizar"],
}
REBOOT = [["su", "-c", "reboot"], ["reboot"]]  # tenta com su; sem root, a tentativa falha e é informada

Post = Callable[[str, dict], dict]
Run = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _run(args: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(args, capture_output=True, text=True, timeout=120, check=False)  # noqa: S603 (lista fechada, sem shell)


def ler_env(path: Path = ENV_FILE) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def estado(run: Run = _run, env: dict[str, str] | None = None) -> dict:
    """O que a caixa informa: coletor ligado, modo, memória disponível, disco livre, último ciclo e versão."""
    env = env if env is not None else ler_env()
    ps = run(["ps", "-ef"]).stdout
    running = "deploy/box/run.sh" in ps
    mem = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                mem = int(line.split()[1])
                break
    except OSError:
        pass
    disk = ""
    try:
        rows = run(["df", "-h", str(ROOT)]).stdout.strip().splitlines()
        disk = rows[-1].split()[3] if rows else ""
    except (OSError, IndexError):
        pass
    last = ""
    try:
        lines = [x for x in LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-200:] if '"feeds"' in x]
        last = lines[-1][:300] if lines else ""
    except OSError:
        pass
    try:
        version = run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]).stdout.strip()[:40]
    except OSError:
        version = ""
    return {"running": running, "mode": "envia" if env.get("CORVO_INGEST_TOKEN") else "seco", "mem_kb": mem, "disk": disk, "last_cycle": last, "version": version}


def executar(action: str, run: Run = _run) -> tuple[bool, str]:
    """Executa UMA ação da lista fechada. Ação desconhecida é recusada sem executar nada."""
    if action == "reboot":
        for cmd in REBOOT:
            try:
                if run(cmd).returncode == 0:
                    return True, "reiniciando a caixa"
            except OSError:
                continue
        return False, "sem permissão para reiniciar a caixa (precisa de root)"
    args = ACOES.get(action)
    if args is None:
        return False, "ação desconhecida"
    r = run(args)
    return r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:150]


def ciclo(post: Post, run: Run, env: dict[str, str], ack: dict | None) -> tuple[dict | None, dict | None, bool]:
    """Um sync. Devolve (comando recebido, próximo ack, sair?). `sair` pede ao supervisor para reiniciar o agente (ex.: depois de `update`)."""
    body: dict = {"status": estado(run, env)}
    if ack:
        body["ack"] = ack
    resp = post("/api/corvo/box/sync", body)
    cmd = resp.get("command")
    if not cmd:
        return None, None, False
    action, cid = str(cmd.get("action", "")), str(cmd.get("id", ""))
    if action == "reboot":  # confirma ANTES: depois de reiniciar não haveria como avisar
        post("/api/corvo/box/sync", {"status": body["status"], "ack": {"id": cid, "ok": True, "note": "reiniciando a caixa"}})
        ok, note = executar(action, run)
        return cmd, {"id": cid, "ok": ok, "note": note}, False
    ok, note = executar(action, run)
    return cmd, {"id": cid, "ok": ok, "note": note}, action == "update"


def main() -> int:
    env = ler_env()
    url, token = env.get("CORVO_API_URL", ""), env.get("CORVO_INGEST_TOKEN", "")
    if not (url and token):
        print("agente: sem CORVO_API_URL/CORVO_INGEST_TOKEN em deploy/box/.env; nada a fazer", file=sys.stderr)
        time.sleep(300)
        return 0

    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 (URL do próprio projeto)
            return json.loads(r.read(100_000))

    ack: dict | None = None
    while True:
        try:
            _, ack, sair = ciclo(post, _run, env, ack)
            if sair:  # envia a confirmação pendente e deixa o supervisor subir a versão nova
                ciclo(post, _run, env, ack)
                return 0
        except Exception as exc:  # noqa: BLE001 (rede fora do ar não derruba o agente)
            print(f"agente: {type(exc).__name__}", file=sys.stderr)
        time.sleep(int(os.environ.get("CORVO_AGENTE_INTERVALO", "30")))


if __name__ == "__main__":
    raise SystemExit(main())
