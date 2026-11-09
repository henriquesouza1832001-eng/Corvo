"""Indicadores de ENTRADA e SAÍDA da caixa: rede, CPU, memória, temperatura, energia (ESTIMADA) e fluxo de notícias, em tempo real e por hora.
Só biblioteca padrão. O agente chama `Medidor.amostra()` a cada ~20 s e `Acumulador.registrar()`; no fim de cada hora sai um resumo
(`resumo_hora`) que a API guarda (uma linha por hora). Nada aqui decide nada: só mede.

ENERGIA: a caixa não tem medidor de potência. A estimativa usa um modelo linear pela CPU: P = ociosa + (máxima - ociosa) x uso.
Os padrões (2,5 W e 6,0 W) são típicos de caixas de TV com chip Allwinner e podem ser trocados em deploy/box/.env
(`CORVO_POTENCIA_OCIOSA_W`, `CORVO_POTENCIA_MAXIMA_W`). Com uma tomada medidora, troque a estimativa pela leitura real.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PROC_NET, PROC_STAT, PROC_LOAD = "/proc/net/dev", "/proc/stat", "/proc/loadavg"
OCIOSA_W, MAXIMA_W = 2.5, 6.0


def ler_rede(path: str = PROC_NET) -> tuple[int, int] | None:
    """(bytes recebidos, bytes enviados) somados em todas as interfaces, menos a local. None se o sistema não deixar ler."""
    try:
        linhas = Path(path).read_text().splitlines()[2:]
    except OSError:
        return None
    rx = tx = 0
    for linha in linhas:
        if ":" not in linha:
            continue
        nome, resto = linha.split(":", 1)
        if nome.strip() == "lo":
            continue
        campos = resto.split()
        if len(campos) >= 9:
            rx += int(campos[0])
            tx += int(campos[8])
    return rx, tx


def ler_cpu(path: str = PROC_STAT) -> tuple[int, int] | None:
    """(tempo ocupado, tempo total) em ticks, da linha `cpu` agregada."""
    try:
        campos = [int(x) for x in Path(path).read_text().splitlines()[0].split()[1:9]]
    except (OSError, ValueError, IndexError):
        return None
    ocioso = campos[3] + (campos[4] if len(campos) > 4 else 0)
    total = sum(campos)
    return total - ocioso, total


def carga(path: str = PROC_LOAD) -> float | None:
    try:
        return float(Path(path).read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def potencia_w(cpu_pct: float | None, ociosa: float = OCIOSA_W, maxima: float = MAXIMA_W) -> float | None:
    """Estimativa da potência (W) pelo uso de CPU. None sem leitura de CPU."""
    if cpu_pct is None:
        return None
    return round(ociosa + (maxima - ociosa) * max(0.0, min(100.0, cpu_pct)) / 100.0, 2)


def _env_float(nome: str, padrao: float) -> float:
    try:
        return float(os.environ.get(nome, padrao))
    except ValueError:
        return padrao


class Medidor:
    """Guarda a leitura anterior e devolve taxas entre duas amostras."""

    def __init__(self, ler_rede_fn=ler_rede, ler_cpu_fn=ler_cpu, carga_fn=carga, ociosa: float | None = None, maxima: float | None = None):
        self._rede, self._cpu, self._carga = ler_rede_fn, ler_cpu_fn, carga_fn
        self.ociosa = ociosa if ociosa is not None else _env_float("CORVO_POTENCIA_OCIOSA_W", OCIOSA_W)
        self.maxima = maxima if maxima is not None else _env_float("CORVO_POTENCIA_MAXIMA_W", MAXIMA_W)
        self._ant: tuple[float, tuple[int, int] | None, tuple[int, int] | None] | None = None

    def amostra(self, agora: float) -> dict:
        rede, cpu = self._rede(), self._cpu()
        out: dict = {"cpu_pct": None, "load1": self._carga(), "rx_bytes": rede[0] if rede else None, "tx_bytes": rede[1] if rede else None,
                     "rx_bps": None, "tx_bps": None, "power_w": None}
        if self._ant:
            t0, rede0, cpu0 = self._ant
            dt = agora - t0
            if cpu and cpu0 and cpu[1] > cpu0[1]:
                out["cpu_pct"] = round(100.0 * (cpu[0] - cpu0[0]) / (cpu[1] - cpu0[1]), 1)
            if rede and rede0 and dt > 0:
                out["rx_bps"] = max(0, round((rede[0] - rede0[0]) / dt))  # contador que zera (reinício) nunca vira taxa negativa
                out["tx_bps"] = max(0, round((rede[1] - rede0[1]) / dt))
        out["power_w"] = potencia_w(out["cpu_pct"], self.ociosa, self.maxima)
        self._ant = (agora, rede, cpu)
        return out


def hora_de(agora: float) -> str:
    return __import__("time").strftime("%Y-%m-%dT%H", __import__("time").gmtime(agora))


class Acumulador:
    """Soma as amostras da hora UTC corrente. Ao virar a hora, `registrar` devolve o resumo da hora que acabou."""

    def __init__(self):
        self.hora: str | None = None
        self._zerar()

    def _zerar(self):
        self.n = 0
        self.soma_temp = self.soma_cpu = self.soma_pot = self.energia_wh = 0.0
        self.max_temp: float | None = None
        self.min_mem: int | None = None
        self.rx0 = self.tx0 = self.rx1 = self.tx1 = None
        self.n_cpu = self.n_pot = self.n_temp = 0
        self._t_ant: float | None = None

    def registrar(self, agora: float, live: dict, temp_c: float | None, mem_kb: int | None, extra: dict | None = None) -> dict | None:
        h = hora_de(agora)
        fechada = None
        if self.hora is not None and h != self.hora:
            fechada = self.resumo(extra)
            self._zerar()
        self.hora = h
        self.n += 1
        if temp_c is not None:
            self.soma_temp += temp_c
            self.n_temp += 1
            self.max_temp = temp_c if self.max_temp is None else max(self.max_temp, temp_c)
        if live.get("cpu_pct") is not None:
            self.soma_cpu += live["cpu_pct"]
            self.n_cpu += 1
        if live.get("power_w") is not None:
            self.soma_pot += live["power_w"]
            self.n_pot += 1
            if self._t_ant is not None:
                self.energia_wh += live["power_w"] * max(0.0, agora - self._t_ant) / 3600.0
        if mem_kb is not None:
            self.min_mem = mem_kb if self.min_mem is None else min(self.min_mem, mem_kb)
        if live.get("rx_bytes") is not None:
            if self.rx0 is None:
                self.rx0, self.tx0 = live["rx_bytes"], live["tx_bytes"]
            self.rx1, self.tx1 = live["rx_bytes"], live["tx_bytes"]
        self._t_ant = agora
        return fechada

    def resumo(self, extra: dict | None = None) -> dict:
        def media(soma, n, casas=1):
            return round(soma / n, casas) if n else None
        rx = max(0, (self.rx1 or 0) - (self.rx0 or 0)) if self.rx0 is not None else None
        tx = max(0, (self.tx1 or 0) - (self.tx0 or 0)) if self.tx0 is not None else None
        out = {"hour": self.hora, "samples": self.n, "temp_avg": media(self.soma_temp, self.n_temp), "temp_max": self.max_temp,
               "cpu_avg": media(self.soma_cpu, self.n_cpu), "mem_min_kb": self.min_mem, "power_w_avg": media(self.soma_pot, self.n_pot, 2),
               "energy_wh": round(self.energia_wh, 3), "rx_bytes": rx, "tx_bytes": tx}
        out.update(extra or {})
        return out


def _linhas_json(path: Path, n: int) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def fluxo_da_hora(hora: str, log: Path, corpus: Path) -> dict:
    """O que passou pelo portão naquela hora UTC (`AAAA-MM-DDTHH`): do log de ciclos (lidas, novas, enviadas, gravadas, falhas) e do
    corpus (decisão de cada item, por fonte). O log tem uma linha `<data UTC> ciclo` antes do resumo JSON de cada ciclo."""
    out = {"cycles": 0, "fetched": 0, "new": 0, "sent": 0, "written": 0, "feeds": 0, "feeds_failed": 0, "hot": 0, "buffer": 0, "dropped": 0, "reasons": {}, "sources": {}}
    ts = None
    for linha in _linhas_json(log, 3000):
        if linha.endswith(" ciclo") and len(linha) > 20:
            ts = linha[:13]
            continue
        if ts == hora and linha.startswith("{") and '"feeds"' in linha:
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            out["cycles"] += 1
            out["fetched"] += int(d.get("fetched", 0))
            out["new"] += int(d.get("new", 0))
            out["sent"] += int(d.get("sent_news", 0))
            out["written"] += int((d.get("api") or {}).get("written", 0))
            out["feeds"] = int(d.get("feeds", 0))
            out["feeds_failed"] += len(d.get("feeds_failed") or {})
    fontes: dict[str, list[int]] = {}
    for linha in _linhas_json(corpus, 6000):
        try:
            d = json.loads(linha)
        except ValueError:
            continue
        if not str(d.get("cycle_at", "")).startswith(hora):
            continue
        v = d.get("verdict")
        out["hot" if v == "hot" else "buffer" if v == "buffer" else "dropped"] += 1
        if v == "drop":
            r = str(d.get("reason", "?"))
            out["reasons"][r] = out["reasons"].get(r, 0) + 1
        f = fontes.setdefault(str(d.get("source_id", "?")), [0, 0])
        f[0] += 1
        f[1] += 0 if v == "drop" else 1
    out["sources"] = dict(sorted(fontes.items(), key=lambda kv: -kv[1][0])[:40])
    return out
