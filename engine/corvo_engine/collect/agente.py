"""Agente da CAIXA: só faz requisições de SAÍDA. A cada ~20 s informa o estado à API e recebe, se houver, UM comando de uma lista fechada
(ligar, desligar, reiniciar o coletor, atualizar, reiniciar a caixa, diagnóstico, log, rede, falhas por fonte, ciclo agora, preços,
limpeza, modo seco/envio, intervalo, reiniciar o agente). Nada fora da lista é
executado, os argumentos são validados aqui de novo, e nunca há `shell=True`. Só biblioteca padrão.
Roda sob `deploy/box/agente.sh` (que o reinicia se ele sair, por exemplo depois de `update`).
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
DATA = ROOT / "engine" / "data" / "corvo_corpus"
LOG, AGENT_LOG, PRECOS, CORPUS = DATA / "caixa.log", DATA / "agente.log", DATA / "precos.csv", DATA / "corpus.jsonl"
ENV_FILE = ROOT / "deploy" / "box" / ".env"
USER_AGENT = "corvo-agente/1.1"
OUT_MAX = 3800

# Lista fechada: ação -> argumentos. O que vem da API é só a CHAVE; o comando real é fixo aqui.
ACOES: dict[str, list[str]] = {
    "on": ["sh", CORVO_SH, "on"],
    "off": ["sh", CORVO_SH, "off"],
    "restart": ["sh", CORVO_SH, "restart"],
    "update": ["sh", CORVO_SH, "atualizar"],
    "seco": ["sh", CORVO_SH, "seco"],
    "envio": ["sh", CORVO_SH, "envio"],
    "ciclo": ["sh", CORVO_SH, "ciclo"],
    "precos": ["sh", CORVO_SH, "precos"],
    "limpar": ["sh", CORVO_SH, "limpar"],
}
LOCAIS = {"diag", "logs", "rede", "fontes", "agente"}  # feitas aqui mesmo, sem chamar o shell
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


def modo(env: dict[str, str]) -> str:
    """ENVIA só com token E sem a trava de modo seco (`CORVO_MODO=seco`)."""
    return "envia" if env.get("CORVO_INGEST_TOKEN") and env.get("CORVO_MODO") != "seco" else "seco"


def _tail(path: Path, n: int) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def _ultimo_preco(path: Path = PRECOS) -> str:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 400))
            linhas = f.read().decode("utf-8", "replace").strip().splitlines()
        return linhas[-1].split(",")[1][:40] if linhas else ""
    except (OSError, IndexError):
        return ""


_contagem: dict[str, tuple[float, int, int]] = {}


def _linhas(path: Path) -> int | None:
    """Conta linhas do corpus uma vez por mudança de arquivo (não varre 50 MB a cada 20 s)."""
    try:
        st = path.stat()
    except OSError:
        return None
    c = _contagem.get(str(path))
    if c and c[0] == st.st_mtime and c[1] == st.st_size:
        return c[2]
    with path.open("rb") as f:
        n = sum(1 for _ in f)
    _contagem[str(path)] = (st.st_mtime, st.st_size, n)
    return n


def _temp_c() -> float | None:
    """Temperatura da caixa (°C), se o sistema deixar ler; senão None."""
    for i in range(6):
        try:
            v = int(Path(f"/sys/class/thermal/thermal_zone{i}/temp").read_text().strip())
        except (OSError, ValueError):
            continue
        return round(v / 1000 if v > 1000 else v, 1)
    return None


def estado(run: Run = _run, env: dict[str, str] | None = None) -> dict:
    """O que a caixa informa: coletor ligado, modo, memória, disco, último ciclo, versão, intervalo, preço mais novo, corpus e erros recentes."""
    env = env if env is not None else ler_env()
    running = "deploy/box/run.sh" in run(["ps", "-ef"]).stdout
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
    cauda = _tail(LOG, 200)
    ciclos = [x for x in cauda if '"feeds"' in x]
    try:
        version = run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]).stdout.strip()[:40]
    except OSError:
        version = ""
    try:
        intervalo = int(env.get("CORVO_INTERVALO", "900"))
    except ValueError:
        intervalo = 900
    return {
        "running": running, "mode": modo(env), "mem_kb": mem, "disk": disk, "last_cycle": ciclos[-1][:300] if ciclos else "", "version": version,
        "interval_s": intervalo, "prices_last": _ultimo_preco(), "corpus_items": _linhas(CORPUS),
        "errors_recent": sum(1 for x in cauda if "Error" in x or "Traceback" in x),
        "temp_c": _temp_c(),
    }


def _cap(text: str) -> str:
    return text if len(text) <= OUT_MAX else "…" + text[-(OUT_MAX - 1):]


def diagnostico(run: Run, env: dict[str, str]) -> str:
    e = estado(run, env)
    linhas = [
        f"coletor: {'LIGADO' if e['running'] else 'DESLIGADO'}   modo: {e['mode']}   intervalo: {e['interval_s']}s   versão: {e['version']}",
        f"memória livre: {round((e['mem_kb'] or 0) / 1024)} MB   disco livre: {e['disk']}   corpus: {e['corpus_items']} itens   erros recentes: {e['errors_recent']}",
        f"preço mais novo: {e['prices_last'] or '?'}   temperatura: {e['temp_c'] if e['temp_c'] is not None else '?'} °C",
        "últimos ciclos:",
    ]
    linhas += ["  " + x[:200] for x in [y for y in _tail(LOG, 200) if '"feeds"' in y][-3:]] or ["  (nenhum)"]
    t = run(["uptime"]).stdout.strip()
    if t:
        linhas.append(f"uptime: {t[:150]}")
    return _cap("\n".join(linhas))


def _tempo_ms(url: str, timeout: int = 10) -> str:
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URLs fixas)
            r.read(2048)
            return f"{round((time.monotonic() - t0) * 1000)} ms (HTTP {r.status})"
    except Exception as exc:  # noqa: BLE001
        return f"falhou ({type(exc).__name__})"


def rede(env: dict[str, str]) -> str:
    """Teste de rede da caixa: a API do CORVO, a internet em geral e uma fonte de notícias."""
    api = env.get("CORVO_API_URL", "https://corvo-api.henriquesouza.workers.dev").rstrip("/")
    alvos = [("API do CORVO", f"{api}/api/health"), ("internet (Cloudflare)", "https://www.cloudflare.com/cdn-cgi/trace"), ("fonte (Fed)", "https://www.federalreserve.gov/feeds/press_all.xml")]
    return _cap("\n".join(f"{nome}: {_tempo_ms(url)}" for nome, url in alvos))


def fontes_com_falha(n_ciclos: int = 100) -> str:
    """Resume as falhas por fonte nos últimos ciclos do log (qual feed cai mais)."""
    cont: dict[str, int] = {}
    ciclos = 0
    for linha in _tail(LOG, 1500):
        if '"feeds_failed"' not in linha:
            continue
        try:
            d = json.loads(linha[linha.index("{"):])
        except (ValueError, TypeError):
            continue
        ciclos += 1
        for fonte in (d.get("feeds_failed") or {}):
            cont[fonte] = cont.get(fonte, 0) + 1
    if ciclos == 0:
        return "nenhum ciclo no log ainda"
    if not cont:
        return f"nenhuma falha de fonte nos últimos {ciclos} ciclos"
    return _cap(f"falhas por fonte nos últimos {ciclos} ciclos:\n" + "\n".join(f"  {k}: {v}" for k, v in sorted(cont.items(), key=lambda kv: -kv[1])))


def logs(n: int = 40) -> str:
    cauda = _tail(LOG, n)
    ag = _tail(AGENT_LOG, 8)
    return _cap("\n".join(["== coletor (caixa.log) =="] + [x[:240] for x in cauda] + ["== agente (agente.log) =="] + [x[:240] for x in ag]))


def executar(action: str, run: Run = _run, arg: int | None = None, env: dict[str, str] | None = None) -> tuple[bool, str, str]:
    """Executa UMA ação da lista fechada e devolve (ok, nota curta, saída). Ação ou argumento inválido é recusado sem executar nada."""
    if action == "reboot":
        for cmd in REBOOT:
            try:
                if run(cmd).returncode == 0:
                    return True, "reiniciando a caixa", ""
            except OSError:
                continue
        return False, "sem permissão para reiniciar a caixa (precisa de root)", ""
    if action == "diag":
        return True, "diagnóstico", diagnostico(run, env if env is not None else ler_env())
    if action == "logs":
        return True, "log", logs()
    if action == "rede":
        return True, "teste de rede", rede(env if env is not None else ler_env())
    if action == "fontes":
        return True, "falhas por fonte", fontes_com_falha()
    if action == "agente":
        return True, "reiniciando o agente", ""
    if action == "intervalo":
        if not isinstance(arg, int) or isinstance(arg, bool) or not 300 <= arg <= 3600:
            return False, "intervalo inválido (300 a 3600 s)", ""
        r = run(["sh", CORVO_SH, "intervalo", str(arg)])
        return r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:150], ""
    args = ACOES.get(action)
    if args is None:
        return False, "ação desconhecida", ""
    r = run(args)
    return r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:150], _cap(r.stdout.strip())


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
        ok, note, out = executar(action, run, env=env)
        return cmd, {"id": cid, "ok": ok, "note": note, "output": out}, False
    ok, note, out = executar(action, run, cmd.get("arg"), env)
    return cmd, {"id": cid, "ok": ok, "note": note, "output": out}, action in ("update", "agente")


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
            env = ler_env()  # relê: `seco`, `envio` e `intervalo` mudam o arquivo
            _, ack, sair = ciclo(post, _run, env, ack)
            if sair:  # envia a confirmação pendente e deixa o supervisor subir a versão nova
                ciclo(post, _run, env, ack)
                return 0
        except Exception as exc:  # noqa: BLE001 (rede fora do ar não derruba o agente)
            print(f"agente: {type(exc).__name__}", file=sys.stderr)
        time.sleep(int(os.environ.get("CORVO_AGENTE_INTERVALO", "20")))


if __name__ == "__main__":
    raise SystemExit(main())
