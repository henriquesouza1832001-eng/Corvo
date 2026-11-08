"""Proveniência: de N publicações a quantas ORIGENS independentes? (RT-008)

Uma origem factual não pode virar 1000 confirmações. Duas publicações são **da mesma origem** quando há evidência de derivação:
1. mesma URL canônica (sem parâmetros de rastreio) ou mesmo hash de conteúdo;
2. título quase idêntico (conjunto de palavras; ordem, pontuação, caixa e prefixos como "URGENTE:" não importam);
3. texto copiado (contenção de *shingles* de 4 palavras no título+resumo);
4. mesmo crédito de AGÊNCIA (Agência Brasil, Reuters, AFP, AP, Estadão Conteúdo...) sobre o mesmo assunto, em janela curta;
5. atribuição explícita a outro veículo ("segundo o G1", "de acordo com a Folha", "via ...") sobre o mesmo assunto;
6. rede social que compartilha o link, cita o título ou repete o texto de outra publicação (social copiando blog ou social).
Duas matérias independentes sobre o MESMO acontecimento (redações diferentes, sem crédito nem cópia) permanecem origens distintas:
o dedup nunca pode destruir independência verdadeira. Sem embeddings/LLM: só regras determinísticas e auditáveis; o que não for
detectável por elas (reescrita completa) é, por definição, jornalismo independente ou desconhecido — o limite é documentado nos testes.

Métricas: `publisher_count` (veículos distintos), `origin_count`, `independent_origin_count` (origens NÃO sociais), `social_origin_count`,
`sensor_family_count` e `duplicate_origin_ratio` = 1 - origens / publicações.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from ..models import SOCIAL_CLASSES, Signal
from ..processing.cluster_refine import entities
from ..processing.clustering import _STOP
from ..processing.normalizer import canonical_url, fold

TITLE_JACCARD = 0.8
TITLE_MIN_WORDS = 3
SHINGLE_N = 4
SHINGLE_CONTAINMENT = 0.6
MIN_SHINGLE_WORDS = 12
MAX_BUCKET = 400  # bucket maior que isto (palavra comum) é ignorado: não discrimina origem e custaria O(n²)
REPS_PER_GROUP = 6  # derivação não é transitiva (social copia o blog, não o jornal): vários representantes por grupo
TOPIC_JACCARD = 0.35  # mesmo assunto (para crédito de agência/atribuição): sobreposição mínima de palavras do título
AGENCY_WINDOW = timedelta(hours=8)
SOCIAL_TEXT_CONTAINMENT = 0.7

_PREFIX = re.compile(r"^\s*(urgente|ao vivo|atualizado|atualiza[cç][aã]o|veja|v[ií]deo|fotos?|exclusivo|plant[aã]o)\s*[:\-–|]\s*", re.I)
AGENCIES = {
    "agencia brasil": "agencia-brasil", "reuters": "reuters", "afp": "afp", "associated press": "ap", "(ap)": "ap",
    "estadao conteudo": "estadao-conteudo", "agencia estado": "estadao-conteudo", "folhapress": "folhapress",
    "agencia lusa": "lusa", "agencia o globo": "agencia-o-globo", "agencia senado": "agencia-senado", "agencia camara": "agencia-camara",
    "ansa": "ansa", "efe": "efe",
}
_ATTRIBUTION = re.compile(r"(?:segundo|de acordo com|conforme|informou|publicou|revelou|fonte:|via\s+@)\s*(?:o|a|os|as)?\s*([a-z0-9][a-z0-9\-]{1,30})", re.I)
_RT = re.compile(r"^\s*(rt|via)\s+@?\w+[: ]", re.I)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", fold(_PREFIX.sub("", text or ""))) if len(w) >= 3 and w not in _STOP]


def title_tokens(title: str) -> frozenset[str]:
    return frozenset(_words(title))


def shingles(text: str, n: int = SHINGLE_N) -> frozenset[str]:
    ws = _words(text)
    return frozenset(" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)) if len(ws) >= MIN_SHINGLE_WORDS else frozenset()


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def containment(a: frozenset, b: frozenset) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def agency_credits(text: str) -> frozenset[str]:
    f = fold(text or "")
    return frozenset(v for k, v in AGENCIES.items() if k in f)


def cited_outlets(text: str) -> frozenset[str]:
    return frozenset(re.sub(r"[^a-z0-9]+", "", fold(m.group(1))) for m in _ATTRIBUTION.finditer(text or ""))


def _outlet_ids(s: Signal) -> frozenset[str]:
    """Identificadores pelos quais OUTRA publicação pode citar este veículo (id da fonte e domínio sem TLD)."""
    ids = {re.sub(r"[^a-z0-9]+", "", fold(s.source_id))}
    for u in (s.canonical_url or canonical_url(s.url) or "",):
        host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
        if host:
            ids.add(re.sub(r"[^a-z0-9]+", "", host.split(".")[0]))
    return frozenset(i for i in ids if i)


@dataclass(frozen=True)
class Features:
    sig: Signal
    url: str | None
    title: frozenset[str]
    ents: frozenset[str]  # nomes próprios/códigos do título (BR-381, Betim): lugares diferentes = acontecimentos diferentes
    shingle: frozenset[str]
    agencies: frozenset[str]
    cites: frozenset[str]
    outlets: frozenset[str]
    social: bool
    links: frozenset[str]  # URLs canônicas citadas no texto (compartilhamento de link)


_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+")


def features(s: Signal) -> Features:
    body = f"{s.title}. {s.text or ''}"
    return Features(s, s.canonical_url or canonical_url(s.url), title_tokens(s.title), frozenset(fold(e) for e in entities(s.title)), shingles(body), agency_credits(body),
                    cited_outlets(body), _outlet_ids(s), s.source_class in SOCIAL_CLASSES,
                    frozenset(u for u in (canonical_url(m.group(0).rstrip(".,);")) for m in _URL_IN_TEXT.finditer(s.text or "")) if u))


def _place_conflict(a: Features, b: Features) -> bool:
    """Lugares/códigos citados nos títulos sem NENHUMA palavra em comum ("Betim" x "Guarulhos", "BR-381" x "BR-116"): outro acontecimento."""
    wa = {w for e in a.ents for w in e.split()}
    wb = {w for e in b.ents for w in e.split()}
    return bool(wa and wb and not (wa & wb))


def derived(a: Features, b: Features) -> str | None:
    """Motivo pelo qual `a` e `b` são da mesma origem, ou None (independentes)."""
    if a.url and a.url == b.url:
        return "mesma URL canônica"
    if (a.url and a.url in b.links) or (b.url and b.url in a.links):
        return "cita a URL da outra publicação"
    place_conflict = _place_conflict(a, b)  # títulos-modelo ("Acidente na BR-381" x "BR-116") não são cópia
    if (len(a.title) >= TITLE_MIN_WORDS and len(b.title) >= TITLE_MIN_WORDS and jaccard(a.title, b.title) >= TITLE_JACCARD
            and not place_conflict):
        return "título quase idêntico"
    if a.shingle and b.shingle and containment(a.shingle, b.shingle) >= SHINGLE_CONTAINMENT:
        return "texto copiado"
    topic = jaccard(a.title, b.title) >= TOPIC_JACCARD or containment(a.title, b.title) >= 0.6
    close = abs(a.sig.timestamp - b.sig.timestamp) <= AGENCY_WINDOW
    if topic and close and not place_conflict and a.agencies & b.agencies:
        return "mesmo crédito de agência"
    if topic and close and not place_conflict and ((a.cites & b.outlets) or (b.cites & a.outlets)):
        return "atribuição explícita a outro veículo"
    # social copiando outra publicação: link compartilhado, título citado ou texto repetido
    for x, y in ((a, b), (b, a)):
        if x.social:
            text = fold(x.sig.text or "") + " " + fold(x.sig.title or "")
            if y.url and y.url.split("//")[-1].lower() in text:
                return "social compartilha o link"
            if y.title and len(y.title) >= TITLE_MIN_WORDS and containment(y.title, title_tokens(text)) >= SOCIAL_TEXT_CONTAINMENT and close:
                return "social repete o título"
    if a.social and b.social and close and (_RT.match(a.sig.title or "") or _RT.match(b.sig.title or "")) and topic:
        return "repost"
    return None


class _UF:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def origin_groups(signals: list[Signal]) -> list[list[Signal]]:
    """Agrupa as publicações por origem (união transitiva das derivações). Compara só pares que partilham alguma palavra do
    título ou shingle (índice invertido), para ficar rápido com milhares de publicações."""
    feats = [features(s) for s in signals]
    uf = _UF(len(feats))
    # 1) Cópias exatas (mesma URL canônica ou mesmo conjunto de palavras do título) fundem em O(n): é o caso das cascatas enormes.
    exact: dict[object, int] = {}
    for i, f in enumerate(feats):
        for key in ([("url", f.url)] if f.url else []) + ([("title", f.title)] if len(f.title) >= TITLE_MIN_WORDS else []):
            if key in exact:
                uf.union(exact[key], i)
            else:
                exact[key] = i
    # 2) O resto compara REPRESENTANTES (um por grupo exato) por índice invertido; palavra comum demais não discrimina origem.
    reps_idx = sorted({uf.find(i) for i in range(len(feats))})
    index: dict[object, list[int]] = defaultdict(list)
    for i in reps_idx:
        f = feats[i]
        for k in set(f.title) | set(f.shingle) | ({f.url} if f.url else set()) | set(f.links):
            index[k].append(i)
    for ids in index.values():
        if len(ids) > MAX_BUCKET:
            continue
        reps: dict[int, list[int]] = {}  # raiz -> até REPS_PER_GROUP membros (derivação não é transitiva)
        for i in ids:
            if uf.find(i) in reps:
                continue
            linked = [r for r, members in reps.items() if any(derived(feats[m], feats[i]) for m in members)]
            if not linked:
                reps[uf.find(i)] = [i]
                continue
            for r in linked:
                uf.union(r, i)
            root = uf.find(i)
            merged = [m for r in linked for m in reps.pop(r, [])] + [i]
            reps[root] = merged[:REPS_PER_GROUP]
    groups: dict[int, list[Signal]] = defaultdict(list)
    for i, f in enumerate(feats):
        groups[uf.find(i)].append(f.sig)
    return list(groups.values())


def provenance(signals: list[Signal]) -> dict:
    """Contagens que NÃO confundem volume com confirmação. `independent_origin_count` exclui origens só-sociais (social é sensor)."""
    if not signals:
        return {"publisher_count": 0, "signal_count": 0, "origin_count": 0, "independent_origin_count": 0, "social_origin_count": 0,
                "sensor_family_count": 0, "duplicate_origin_ratio": 0.0}
    groups = origin_groups(signals)
    social_only = sum(1 for g in groups if all(s.source_class in SOCIAL_CLASSES for s in g))
    return {"publisher_count": len({s.source_id for s in signals}), "signal_count": len(signals), "origin_count": len(groups),
            "independent_origin_count": len(groups) - social_only, "social_origin_count": social_only,
            "sensor_family_count": len({s.source_class for s in signals}),
            "duplicate_origin_ratio": round(1 - len(groups) / len(signals), 4)}
