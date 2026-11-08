"""Portão de admissão do CORVO: controla COMO a notícia chega, para não sobrecarregar o banco (D1 grátis: 100 mil linhas/dia).

Determinístico, sem rede e sem LLM. Cada item passa por: frescor -> duplicata exata -> quase-duplicata -> relevância -> cota por fonte
-> pressão do orçamento. O resultado é HOT (grava já), BUFFER (fica no buffer local/Oracle e sobe agregado em lote) ou DROP (com motivo
contado). Texto externo é dado, nunca instrução. O que o portão nega nunca é "fato negado": só não ocupa linha no banco.
"""
from __future__ import annotations

import re
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Domínios de interesse do CORVO: política, catástrofe, mercado (cripto, ações, câmbio, juros, commodities). Pesos são hipóteses a medir.
TOPICS: dict[str, tuple[float, re.Pattern[str]]] = {
    "catastrofe": (1.0, re.compile(r"\b(earthquake|tsunami|hurricane|wildfire|explosion|blackout|terremoto|enchente|inc[eê]ndio)\b", re.I)),
    "geopolitica": (0.9, re.compile(r"\b(war|invasion|sanctions?|tariffs?|coup|missile|ceasefire|guerra|san[cç][aã]o|san[cç][oõ]es)\b", re.I)),
    "politica": (0.7, re.compile(r"\b(election|president|parliament|congress|senate|elei[cç][aã]o|elei[cç][oõ]es)\b", re.I)),
    "banco_central": (1.0, re.compile(r"\b(fed|fomc|ecb|copom|rate (cut|hike)|interest rates?|juros|inflation|cpi|payrolls?)\b", re.I)),
    "cripto": (0.8, re.compile(r"\b(bitcoin|btc|ethereum|eth|solana|etf|stablecoin|hack|exploit|sec|cftc)\b", re.I)),
    "mercado": (0.6, re.compile(r"\b(s&p ?500|nasdaq|wall street|oil|gold|dollar|dxy|stocks?|a[cç][oõ]es|ouro|petr[oó]leo)\b", re.I)),
}
_NOISE = re.compile(r"\b(sponsored|advertorial|giveaway|horoscope|celebrity|publieditorial)\b", re.I)
_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref", "cmpid"}
_WORD = re.compile(r"[a-zà-ú0-9]{3,}", re.I)


class Decision(str, Enum):
    HOT = "hot"
    BUFFER = "buffer"
    DROP = "drop"


class Pressure(str, Enum):
    """Espelha o modo do orçamento de escrita do D1 (apps/worker/src/lib/budget.ts)."""
    NORMAL = "normal"
    ECONOMY = "economy"
    CRITICAL = "critical"


@dataclass(frozen=True)
class NewsItem:
    source_id: str
    url: str
    title: str
    published_at: float  # epoch s
    text: str = ""
    source_reliability: float = 0.5  # 0-1, nota inicial a ser medida pelo histórico


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    reason: str
    relevance: float = 0.0
    topics: tuple[str, ...] = ()


@dataclass
class GateConfig:
    max_age_s: float = 6 * 3600
    per_source_per_hour: int = 30
    near_dup_jaccard: float = 0.7
    dedup_window: int = 5000
    # relevância mínima para gravar já (HOT) e para entrar no buffer, por pressão do orçamento
    hot_min: dict[Pressure, float] = field(default_factory=lambda: {Pressure.NORMAL: 0.6, Pressure.ECONOMY: 0.8, Pressure.CRITICAL: 0.95})
    buffer_min: dict[Pressure, float] = field(default_factory=lambda: {Pressure.NORMAL: 0.3, Pressure.ECONOMY: 0.5, Pressure.CRITICAL: 0.95})


def canonical_url(url: str) -> str:
    p = urlsplit(url.strip())
    q = urlencode(sorted((k, v) for k, v in parse_qsl(p.query) if k.lower() not in _TRACKING))
    return urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), q, ""))


def _tokens(title: str) -> frozenset[str]:
    return frozenset(w.lower() for w in _WORD.findall(title))


def score(item: NewsItem) -> tuple[float, tuple[str, ...]]:
    blob = f"{item.title} {item.text[:500]}"
    if _NOISE.search(blob):
        return 0.0, ()
    hits = [(w, name) for name, (w, rx) in TOPICS.items() if rx.search(blob)]
    if not hits:
        return 0.0, ()
    best = max(w for w, _ in hits)
    bonus = min(0.15, 0.05 * (len(hits) - 1))  # tema cruzado (ex.: guerra + petróleo) pesa mais
    rel = min(1.0, (best + bonus) * (0.6 + 0.4 * item.source_reliability))
    return round(rel, 3), tuple(sorted(n for _, n in hits))


class IntakeGate:
    def __init__(self, config: GateConfig | None = None, clock=time.time) -> None:
        self.cfg = config or GateConfig()
        self._clock = clock
        self._seen_url: OrderedDict[str, None] = OrderedDict()
        self._seen_tok: OrderedDict[frozenset[str], None] = OrderedDict()
        self._quota: dict[str, list[float]] = {}
        self.stats: Counter[str] = Counter()

    def _remember(self, url_key: str, toks: frozenset[str]) -> None:
        self._seen_url[url_key] = None
        self._seen_tok[toks] = None
        for d in (self._seen_url, self._seen_tok):
            while len(d) > self.cfg.dedup_window:
                d.popitem(last=False)

    def _near_dup(self, toks: frozenset[str]) -> bool:
        if len(toks) < 4:
            return False
        return any(len(toks & o) / len(toks | o) >= self.cfg.near_dup_jaccard for o in self._seen_tok)

    def _within_quota(self, source: str, now: float) -> bool:
        window = [t for t in self._quota.get(source, []) if now - t < 3600]
        ok = len(window) < self.cfg.per_source_per_hour
        if ok:
            window.append(now)
        self._quota[source] = window
        return ok

    def admit(self, item: NewsItem, pressure: Pressure = Pressure.NORMAL) -> Verdict:
        v = self._decide(item, pressure)
        self.stats[f"{v.decision.value}:{v.reason}"] += 1
        return v

    def _decide(self, item: NewsItem, pressure: Pressure) -> Verdict:
        now = self._clock()
        if not item.title.strip() or not item.url:
            return Verdict(Decision.DROP, "malformed")
        if now - item.published_at > self.cfg.max_age_s:
            return Verdict(Decision.DROP, "stale")
        key, toks = canonical_url(item.url), _tokens(item.title)
        if key in self._seen_url:
            return Verdict(Decision.DROP, "duplicate_url")
        if self._near_dup(toks):
            return Verdict(Decision.DROP, "near_duplicate")
        rel, topics = score(item)
        if rel < self.cfg.buffer_min[pressure]:
            return Verdict(Decision.DROP, "irrelevant" if rel == 0 else "below_threshold", rel, topics)
        # a cota só é gasta por item que seria admitido, para lixo não consumir a vez de notícia boa
        if not self._within_quota(item.source_id, now):
            return Verdict(Decision.DROP, "source_quota", rel, topics)
        self._remember(key, toks)
        if rel >= self.cfg.hot_min[pressure]:
            return Verdict(Decision.HOT, "relevant", rel, topics)
        return Verdict(Decision.BUFFER, "batch_later", rel, topics)
