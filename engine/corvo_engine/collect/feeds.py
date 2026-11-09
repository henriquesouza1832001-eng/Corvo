"""Leitura de um feed RSS/Atom do catálogo. Reaproveita o leitor endurecido do engine (limite de tamanho, anti-bomba de
descompressão, recusa de ENTITY, no máximo 2 conexões simultâneas por servidor). Só título, link e resumo curto entram."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from ..collectors.news.rss import RssAdapter, _parse_date, http_fetch
from ..intake import NewsItem
from ..processing.keyword_engine import KeywordEngine
from ..processing.normalizer import clean_text

CATALOG_PATH = Path(__file__).with_name("catalog.json")
_KEYWORDS: KeywordEngine | None = None


def load_catalog(path: Path | None = None, tier: int | None = None) -> list[dict]:
    """Feeds habilitados até a CAMADA pedida. Camada 0 (padrão, sem `tier` no catálogo) é o núcleo; 1 e 2 são fontes extras que o
    governador térmico da caixa liga aos poucos (`CORVO_TIER`). Sem a variável, tudo continua como antes: só a camada 0."""
    if tier is None:
        try:
            tier = int(os.environ.get("CORVO_TIER", "0"))
        except ValueError:
            tier = 0
    data = json.loads((path or CATALOG_PATH).read_text(encoding="utf-8"))
    return [f for f in data["feeds"] if f.get("enabled", True) and int(f.get("tier", 0)) <= tier]


def fetch_feed(feed: dict, fetcher: Callable[[str], bytes] = http_fetch, now: Callable[[], float] = time.time) -> list[NewsItem]:
    """Itens do feed como `NewsItem`. Levanta exceção se o feed falhar (o chamador isola a falha por fonte)."""
    global _KEYWORDS
    _KEYWORDS = _KEYWORDS or KeywordEngine()
    adapter = RssAdapter({"id": feed["id"], "source_class": "NEWS_HIGH", "url": feed["url"]}, keywords=_KEYWORDS, fetcher=fetcher)
    t_now = now()
    out: list[NewsItem] = []
    for raw in adapter.fetch():
        title = clean_text(raw.get("title"), 300)
        link = (raw.get("link") or "").strip()
        if not title or not link.startswith(("http://", "https://")):
            continue
        dt = _parse_date(raw.get("date"))
        ts = min(dt.timestamp(), t_now) if dt else t_now  # data futura em feed mal configurado nunca vale; sem data = agora
        out.append(NewsItem(feed["id"], link, title, ts, clean_text(raw.get("summary"), 500) or "", float(feed.get("reliability", 0.5)), float(feed.get("max_age_h", 24)) * 3600))
    return out
