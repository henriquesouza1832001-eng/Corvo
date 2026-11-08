"""Política de guarda e esquecimento de Munin: o que pode ser gravado e por quanto tempo.

Os prazos aqui DEVEM ser iguais aos do Worker (`RETAIN_NEWS_DAYS`, `RETAIN_STATS_DAYS` em apps/worker/src/routes/corvo.ts); um teste
confere. Regra central: o que é DESCARTADO não deixa texto em lugar nenhum; só o aprovado vira linha, e só com os campos permitidos.
"""
from __future__ import annotations

RETAIN_NEWS_DAYS = 30
RETAIN_STATS_DAYS = 14
RETAIN_HASH_HOURS = 48

# Único conjunto de campos que uma notícia aprovada pode ter no lote. Nunca o corpo da matéria, nunca pessoas.
ALLOWED_NEWS_FIELDS = frozenset({
    "item_id", "source_id", "source_reliability", "title", "url", "published_at", "verdict", "reason", "relevance",
    "kind", "topics", "lat", "lon", "region", "assets",
})


def storable_payload(verdict: str, item: dict) -> dict | None:
    """Devolve o que pode ser gravado: `None` para DROP (nada), ou o item filtrado pelos campos permitidos para HOT/BUFFER."""
    if verdict == "drop":
        return None
    if verdict not in ("hot", "buffer"):
        raise ValueError(f"veredito desconhecido: {verdict}")
    return {k: v for k, v in item.items() if k in ALLOWED_NEWS_FIELDS}
