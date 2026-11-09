"""GOVERNADOR TÉRMICO da caixa: cresce o trabalho aos poucos enquanto a temperatura deixa, e recua antes de chegar ao limite.

Regra (todas as constantes ficam em `Cfg`, trocáveis em deploy/box/.env):
- LIMITE térmico (padrão 80 °C) e TETO de trabalho = 85% do limite (68 °C). O governador mantém a caixa abaixo do teto.
- SUBE uma camada de fontes quando a mediana dos últimos ~5 min está ao menos `folga_c` abaixo do teto, há memória sobrando e
  passaram 30 min da última mudança (para um degrau não esquentar o seguinte antes de ser medido).
- DESCE uma camada quando a mediana chega ao teto ou a memória livre cai demais.
- EMERGÊNCIA: a 95% do limite volta à camada 0; no limite, PEDE para desligar o coletor (marca "parado": só o dono religa).
Só decide. Quem aplica a camada é o agente (`corvo.sh tier N`).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median


@dataclass
class Cfg:
    limite_c: float = 80.0
    teto_frac: float = 0.85
    folga_c: float = 4.0
    emergencia_frac: float = 0.95
    min_entre_mudancas_s: float = 1800.0
    tier_max: int = 2
    mem_promover_kb: int = 300_000
    mem_rebaixar_kb: int = 150_000
    amostras_para_decidir: int = 9  # ~3 min de leituras a cada 20 s
    amostras_para_subir: int = 12  # ~4 min

    @property
    def teto_c(self) -> float:
        return round(self.limite_c * self.teto_frac, 1)


@dataclass
class Estado:
    tier: int = 0
    ultima_mudanca: float = 0.0
    janela: deque = field(default_factory=lambda: deque(maxlen=15))
    no_limite: int = 0


@dataclass(frozen=True)
class Decisao:
    tier: int
    motivo: str = ""  # vazio = sem mudança
    parar: bool = False


def decidir(est: Estado, temp_c: float | None, mem_kb: int | None, agora: float, cfg: Cfg | None = None) -> Decisao:
    cfg = cfg or Cfg()
    if temp_c is None:  # sem leitura de temperatura, nunca cresce (e não recua por falta de dado)
        return Decisao(est.tier)
    est.janela.append(temp_c)
    est.no_limite = est.no_limite + 1 if temp_c >= cfg.limite_c else 0
    if est.no_limite >= 3:
        return Decisao(0, f"temperatura no limite ({cfg.limite_c:g} °C): coletor desligado por segurança", parar=True)
    if temp_c >= cfg.limite_c * cfg.emergencia_frac and est.tier > 0:
        return Decisao(0, f"emergência térmica ({temp_c:g} °C): voltou à camada 0")
    med = median(est.janela)
    sozinha = agora - est.ultima_mudanca
    if len(est.janela) >= cfg.amostras_para_decidir and est.tier > 0:
        if med >= cfg.teto_c:
            return Decisao(est.tier - 1, f"mediana {med:g} °C no teto ({cfg.teto_c:g}): desceu para a camada {est.tier - 1}")
        if mem_kb is not None and mem_kb < cfg.mem_rebaixar_kb:
            return Decisao(est.tier - 1, f"memória livre baixa ({round(mem_kb / 1024)} MB): desceu para a camada {est.tier - 1}")
    if (est.tier < cfg.tier_max and len(est.janela) >= cfg.amostras_para_subir and med <= cfg.teto_c - cfg.folga_c
            and (mem_kb is None or mem_kb >= cfg.mem_promover_kb) and sozinha >= cfg.min_entre_mudancas_s):
        return Decisao(est.tier + 1, f"mediana {med:g} °C com folga até o teto ({cfg.teto_c:g}): subiu para a camada {est.tier + 1}")
    return Decisao(est.tier)
