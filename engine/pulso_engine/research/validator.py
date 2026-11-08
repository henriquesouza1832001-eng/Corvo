"""Validation engine do Sentinela: tenta CONFIRMAR, REFUTAR e CONTEXTUALIZAR uma investigação a partir dos sinais que a
originaram e das evidências da deep search. Determinístico, sem LLM.

Princípios (§21, §27, §28, §49):
- cópias da mesma matéria não são confirmações: títulos quase idênticos formam UM grupo;
- contradição não se resolve escolhendo a versão mais repetida: é REGISTRADA com quem diz o quê, e a versão oficial
  aparece à parte;
- rede social é sensor, nunca confirmação sozinha;
- o resultado sugere um estado e alimenta `EventStats.contradiction` e a confirmação oficial; não decide a verdade.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from ..models import SOCIAL_CLASSES, Signal
from ..processing.keyword_engine import _fold
from .provenance import origin_groups
from .sentinel import Investigation

MIN_INDEPENDENT_CONFIRMED = 3  # sem fonte oficial, confirmar exige 3 origens independentes...
MIN_TYPES_CONFIRMED = 2  # ...de ao menos 2 tipos de fonte, um deles não social

# (tema, lado A, lado B): pares de afirmações incompatíveis sobre o mesmo fato.
CLAIM_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("extensão do bloqueio", r"totalmente (fechad|interditad|bloquead)|bloqueio total|interdi\w+ total", r"bloqueio parcial|interdi\w+ parcial|uma faixa|liberad|trafego normal|normalizad"),
    ("vítimas", r"\bmortos?\b|\bmorre(u|m)\b|vitimas? fatais?|\bferidos?\b", r"sem (vitimas|feridos|mortos)|ninguem (ficou )?ferid|nenhum (ferido|morto)|nao (ha|houve|deixou|deixa) (mortos|feridos|vitimas)"),
    ("situação do fogo/alagamento", r"fora de controle|sem controle|avanca|se espalha", r"controlad|extint|apagad|debelad|baixou|nivel (do rio )?(baixa|recua)"),
    # "apagão" nomeia o evento, não afirma o estado atual: "energia restabelecida após apagão" é desfecho (lado B).
    ("energia/serviço", r"sem energia|sem luz|fora do ar", r"energia (restabelecid|normalizad)|servico (restabelecid|normalizad)|volta ao normal"),
)


# Negativa oficial: a fonte OFICIAL desmente/descarta o que outras dizem. Vale como CONTRADIÇÃO (não como confirmação), por maioria de
# cópias que seja o outro lado.
DENIAL = re.compile(r"nega(?:m|u|ram|do)?|desment\w+|descart\w+|falso|boato|fake|nao ha (?:risco|registro|rompimento|vitima|alerta|previsao)|sem risco|"
                    r"nao (?:indica|indicam|ha indicio|houve|existe|ha confirmacao|prev[eê])|sem previsao de|sem precipitacao|nao ha")
GENERIC = frozenset({"defesa", "civil", "situacao", "risco", "nao", "sem", "normal", "ainda", "sobre", "regiao", "capital", "horas", "proximas",
                     "estado", "cidade", "governo", "prefeitura", "informou", "disse"})
STATES = ("SUPPORTED", "UNCONFIRMED", "DISPUTED")


def _topic_words(s: Signal) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", _fold(f"{s.title} {s.text or ''}")) if w not in GENERIC}


def official_denials(signals: list[Signal]) -> list[dict]:
    """Sinais OFICIAIS que negam um assunto tratado por outros sinais NÃO oficiais. Devolve contradições com `official_side` = "b"."""
    out = []
    claimants = [s for s in signals if s.source_class != "OFFICIAL"]
    for d in (s for s in signals if s.source_class == "OFFICIAL"):
        if not DENIAL.search(_fold(f"{d.title} {d.text or ''}")):
            continue
        topic = _topic_words(d)
        claims = [c for c in claimants if topic & _topic_words(c) and not DENIAL.search(_fold(f"{c.title} {c.text or ''}"))]
        if claims:
            out.append({"topic": "negativa oficial", "side_a": {"sources": sorted({c.source_id for c in claims}), "official": False, "example": claims[0].title},
                        "side_b": {"sources": [d.source_id], "official": True, "example": d.title}, "official_side": "b"})
    return out


def is_denial(s: Signal) -> bool:
    return s.source_class == "OFFICIAL" and bool(DENIAL.search(_fold(f"{s.title} {s.text or ''}")))


@dataclass(frozen=True)
class Validation:
    event_candidate: str
    evidence: tuple[dict, ...]
    contradictions: tuple[dict, ...]
    official_confirmation: bool
    independent_sources: int
    source_types: int
    copy_ratio: float
    suggested_status: str
    contradiction_score: float
    claim_state: str = "UNCONFIRMED"  # SUPPORTED | UNCONFIRMED | DISPUTED (estado da ALEGAÇÃO, separado do status da investigação)  # 0-1, entra em EventStats.contradiction


def _origins(signals: list[Signal]) -> list[list[Signal]]:
    """Agrupa publicações DERIVADAS (republicação, agência, atribuição, cópia, social repetindo): cada grupo vale UMA origem.
    Implementação em `research/provenance.py` (RT-008); mantido o nome por compatibilidade."""
    return origin_groups(signals)


def claim_side(a: str, b: str, folded: str) -> str | None:
    """De que lado do par o texto (já `_fold`) está. O lado B (negação/desfecho) tem precedência sobre as palavras que
    ele mesmo contém: "não deixou feridos" é B, embora tenha "feridos". Só é ambíguo (None) se o lado A aparecer FORA do
    trecho B: "sem vítimas fatais, mas 3 feridos" é outra história."""
    if re.search(b, folded):
        return None if re.search(a, re.sub(b, " ", folded)) else "b"
    return "a" if re.search(a, folded) else None


def find_contradictions(signals: list[Signal]) -> list[dict]:
    out = []
    folded = {s.hash: _fold(f"{s.title} {s.text or ''}") for s in signals}
    for topic, a, b in CLAIM_PAIRS:
        side = {s.hash: claim_side(a, b, folded[s.hash]) for s in signals}
        side_a = [s for s in signals if side[s.hash] == "a"]
        side_b = [s for s in signals if side[s.hash] == "b"]
        if not side_a or not side_b:
            continue
        def pack(side: list[Signal]) -> dict:
            return {"sources": sorted({s.source_id for s in side}), "official": any(s.source_class == "OFFICIAL" for s in side),
                    "example": side[0].title}
        pa, pb = pack(side_a), pack(side_b)
        out.append({"topic": topic, "side_a": pa, "side_b": pb,
                    "official_side": "a" if pa["official"] and not pb["official"] else "b" if pb["official"] and not pa["official"] else None})
    return out


def _status(official: bool, contradictions: list[dict], independent: int, types: int, non_social: bool, current: str) -> str:
    if contradictions:
        return "DISPUTED"
    if official or (independent >= MIN_INDEPENDENT_CONFIRMED and types >= MIN_TYPES_CONFIRMED and non_social):
        return "CONFIRMED"
    if independent >= 2 and types >= 2:
        return "WAITING_CONFIRMATION"
    if independent >= 2:
        return "CORRELATING"
    return "INVESTIGATING" if current in ("NEW", "INVESTIGATING") else current


def validate(inv: Investigation, members: list[Signal], evidence_signals: list[Signal] | None = None) -> Validation:
    """`members`: sinais que originaram a investigação; `evidence_signals`: sinais achados pela deep search."""
    seen: dict[str, Signal] = {}
    for s in [*members, *(evidence_signals or [])]:
        seen.setdefault(s.hash, s)
    signals = list(seen.values())
    groups = _origins(signals)
    independent = len(groups)  # ORIGENS (cópias já fundidas), não veículos
    classes = {s.source_class for s in signals}
    official = any(s.source_class == "OFFICIAL" and not is_denial(s) for s in signals)  # negativa oficial NÃO é confirmação
    non_social = bool(classes - SOCIAL_CLASSES)
    contradictions = find_contradictions(signals) + official_denials(signals)
    copies = len(signals) - len(groups)
    # Fonte oficial que concorda com um dos lados não zera a disputa: a divergência fica registrada.
    status = _status(official, contradictions, independent, len(classes), non_social, inv.status)
    return Validation(
        event_candidate=f"{inv.category} em {inv.scope}", evidence=tuple(
            {"signal_hash": s.hash, "source_id": s.source_id, "source_class": s.source_class, "url": s.url, "title": s.title}
            for s in sorted(signals, key=lambda x: x.timestamp, reverse=True)[:30]),
        contradictions=tuple(contradictions), official_confirmation=official, independent_sources=independent,
        source_types=len(classes), copy_ratio=round(copies / len(signals), 3) if signals else 0.0,
        suggested_status=status, contradiction_score=min(1.0, len(contradictions) / 2),
        claim_state="DISPUTED" if contradictions else ("SUPPORTED" if status == "CONFIRMED" else "UNCONFIRMED"),
    )


_FINAL = frozenset({"RESOLVING", "CLOSED"})


def apply_validation(inv: Investigation, v: Validation) -> Investigation:
    """Aplica o resultado à investigação. Investigação em encerramento (RESOLVING/CLOSED) não é reaberta pela validação."""
    if inv.status in _FINAL:
        return inv
    return replace(inv, status=v.suggested_status, official_confirmation=inv.official_confirmation or v.official_confirmation,
                   evidence_count=max(inv.evidence_count, len(v.evidence)))
