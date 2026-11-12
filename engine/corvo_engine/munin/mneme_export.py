"""In-memory CORVO → MNEME contract preview; this module never stores or sends records."""

from __future__ import annotations

import hashlib
import math
import unicodedata
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlsplit

from ..intake.gate import canonical_url
from .events import build_events

PREVIEW_VERSION = "corvo-mneme-preview-v0"
CLUSTER_VERSION = "munin-events-v1"
_EVIDENCE_KINDS = {"opiniao", "previsao", "rumor", "em_desenvolvimento", "especulacao", "reportagem"}


def _instante(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso(value: object) -> str | None:
    instante = _instante(value)
    return instante.isoformat().replace("+00:00", "Z") if instante else None


def _titulo_hash(title: str) -> str:
    normalizado = " ".join(unicodedata.normalize("NFKC", title).casefold().split())
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def _confiabilidade(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= 1 else None


def exportar_para_mneme(decisions: Iterable[dict]) -> dict:
    """Converte decisões HOT/BUFFER em artigos e eventos candidatos, sem inferir dados ausentes.

    A saída é só um objeto em memória para simulação local. Ela não publica, não grava arquivo e
    nunca promove a classificação de uma fonte oficial a confirmação independente da alegação.
    """
    articles: list[dict] = []
    event_inputs: list[dict] = []
    seen_ids: set[str] = set()
    excluded_by_hugin = 0
    invalid_accepted = 0

    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("verdict") not in {"hot", "buffer"}:
            excluded_by_hugin += 1
            continue

        source = str(decision.get("source_id") or "").strip()
        url = str(decision.get("url") or "").strip()
        title = str(decision.get("title") or "").strip()
        parts = urlsplit(url)
        if not source or not title or parts.scheme not in {"http", "https"} or not parts.netloc:
            invalid_accepted += 1
            continue

        canonical = canonical_url(url)
        article_id = "art_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)

        published_at = _iso(decision.get("published_at"))
        received_at = _iso(decision.get("cycle_at"))
        official = decision.get("source_is_official") is True
        raw_kind = str(decision.get("kind") or "").strip()
        evidence_type = raw_kind if raw_kind in _EVIDENCE_KINDS else "reportagem"
        if official and raw_kind == "fato":
            evidence_type = "publicacao_institucional"
        raw_topics = decision.get("topics", [])
        if isinstance(raw_topics, str):
            raw_topics = [raw_topics]
        if not isinstance(raw_topics, (tuple, list, set, frozenset)):
            raw_topics = []
        topics = sorted({str(topic).strip() for topic in raw_topics if str(topic).strip()})
        reliability = _confiabilidade(decision.get("source_reliability"))
        exported_title = title[:400]

        article = {
            "record_type": "article",
            "id": article_id,
            "fonte": source,
            "url": url,
            "hash_titulo_sha256": _titulo_hash(exported_title),
            "publicado_em": published_at,
            "recebido_em": received_at,
            "ocorrido_em": None,
            "titulo": exported_title,
            "resumo": "",
            "tipo_evidencia": evidence_type,
            "estado_alegacao": "nao_confirmada_independentemente",
            "confiabilidade_fonte_inicial": reliability,
            "relevancia_hugin": _confiabilidade(decision.get("relevance")),
            "veredito_hugin": decision["verdict"],
            "motivo_hugin": str(decision.get("reason") or ""),
            "temas": topics,
            "ativos_candidatos": [],
            "suspeito": None,
            "verificacao_injecao": "pendente_no_destino",
            "texto_externo_nao_confiavel": True,
            "versao_preview": PREVIEW_VERSION,
        }
        articles.append(article)
        event_inputs.append({
            "article_id": article_id,
            "source_id": source,
            "url": canonical,
            "title": exported_title,
            "published_at": published_at,
            "cycle_at": received_at,
            "topics": topics,
        })

    events = []
    for event in build_events(event_inputs):
        received = [_instante(article.get("cycle_at")) for article in event.articles]
        first_received = min(received).isoformat().replace("+00:00", "Z") if received and all(received) else None
        events.append({
            "record_type": "event",
            "event_id": event.event_id,
            "article_ids": sorted(str(article["article_id"]) for article in event.articles),
            "first_received_at": first_received,
            "available_at": event.available_at,
            "observation_time_basis": event.observation_time_basis,
            "source_ids": list(event.source_ids),
            "source_independence": "unverified",
            "coverage_pattern": event.confirmation,
            "state": "candidate",
            "claim_status": "not_independently_confirmed",
            "topics": list(event.topics),
            "assets_candidates": [],
            "cluster_version": CLUSTER_VERSION,
        })

    return {
        "preview_version": PREVIEW_VERSION,
        "articles": articles,
        "events": events,
        "excluded_by_hugin": excluded_by_hugin,
        "invalid_accepted": invalid_accepted,
    }
