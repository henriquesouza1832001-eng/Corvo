"""Hipóteses de impacto (proposta M3): do TEMA do Hugin aos ATIVOS que ele pode mexer, com direção e horizonte.

Tabela EDITÁVEL e AUDITÁVEL; nada de modelo de linguagem decidindo. **Direção e ativo são HIPÓTESES**: só viram peso depois que Munin
medir, com amostra mínima (30 por tema, ativo e horizonte), que a hipótese se sustenta. Até lá, são só perguntas a testar.
Os temas são os de `intake/gate.py` (`TOPICS`); um teste garante que a tabela não cita tema inexistente.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hypothesis:
    asset: str
    direction: str  # "up" | "down" | "volatile"
    horizon: str
    hypothesis: bool = True  # sempre verdadeiro até a bancada provar o contrário


# tema do portão -> hipóteses. "volatile" = mexe na volatilidade; a direção não é afirmada.
HYPOTHESES: dict[str, tuple[Hypothesis, ...]] = {
    "banco_central": (Hypothesis("USD", "volatile", "24h"), Hypothesis("BTC", "volatile", "24h"), Hypothesis("OURO", "volatile", "24h")),
    "banco_central_lideranca": (Hypothesis("USD", "volatile", "24h"),),
    "dados_macro": (Hypothesis("USD", "volatile", "24h"), Hypothesis("SP500", "volatile", "24h")),
    "comercio": (Hypothesis("USD", "volatile", "24h"), Hypothesis("SP500", "down", "24h")),
    "energia": (Hypothesis("PETROLEO", "volatile", "24h"),),
    "conflito_chave": (Hypothesis("PETROLEO", "up", "24h"), Hypothesis("OURO", "up", "24h")),
    "catastrofe": (Hypothesis("SP500", "volatile", "6h"),),
    "infraestrutura": (Hypothesis("PETROLEO", "volatile", "24h"),),
    "cripto": (Hypothesis("BTC", "down", "6h"), Hypothesis("ETH", "down", "6h")),
    "empresas": (Hypothesis("SP500", "down", "24h"),),
    "mercado": (Hypothesis("SP500", "volatile", "24h"), Hypothesis("BTC", "volatile", "24h")),
}


def candidates(topics: list[str] | tuple[str, ...]) -> list[Hypothesis]:
    """Hipóteses a testar para os temas de um evento (sem repetir ativo, direção e horizonte). Tema sem entrada não gera nada."""
    seen: set[tuple[str, str, str]] = set()
    out: list[Hypothesis] = []
    for t in topics:
        for h in HYPOTHESES.get(t, ()):
            k = (h.asset, h.direction, h.horizon)
            if k not in seen:
                seen.add(k)
                out.append(h)
    return out


def question_for(topic: str, h: Hypothesis) -> str:
    """Pergunta fechada, com horizonte e resposta objetiva (retorno ANORMAL, não "acima de zero")."""
    verbo = {"up": "terá retorno anormal positivo", "down": "terá retorno anormal negativo", "volatile": "terá movimento anormal (em qualquer direção)"}[h.direction]
    return f"Depois de um evento de {topic.replace('_', ' ')}, {h.asset} {verbo} acima de 1 desvio-padrão nas próximas {h.horizon}?"
