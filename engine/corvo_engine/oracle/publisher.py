"""Publicador: notícias -> portão (intake) -> lote para `POST /api/corvo/ingest`.

Só o que o portão aprova (HOT/BUFFER) vira linha no D1; o resto vira só contagem por motivo. A pressão do orçamento vem do próprio
Worker (`GET /api/corvo/pressure`); se ela não puder ser lida, o portão assume ECONOMY (na dúvida, grava menos). Sem LLM, sem ordens.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Protocol

from ..intake import Decision, IntakeGate, NewsItem, Pressure
from ..intake.gate import canonical_url

USER_AGENT = "corvo-oracle/0.1 (+https://github.com/henriquesouza1832001-eng/Corvo)"

_KINDS = (
    ("opiniao", re.compile(r"\b(opinion|opini[aã]o|commentary|analyst says|why i)\b", re.I)),
    ("previsao", re.compile(r"\b(forecast|price prediction|could (hit|reach)|expected to|poised to|previs[aã]o)\b", re.I)),
    ("rumor", re.compile(r"\b(rumou?rs?|reportedly|unconfirmed|sources? (say|said)|leak(s|ed)?|boato)\b", re.I)),
)


def classify_kind(title: str, official: bool = False) -> str:
    """Tipo da notícia por regras. Na dúvida é "reportagem" (ainda precisa de outra fonte); só fonte oficial vira "fato"."""
    for kind, rx in _KINDS:
        if rx.search(title):
            return kind
    return "fato" if official else "reportagem"


class Transport(Protocol):
    def request(self, method: str, path: str, body: dict | None = None) -> dict: ...


class HttpTransport:
    def __init__(self, base_url: str | None = None, token: str | None = None, timeout: int = 30) -> None:
        self.base = (base_url or os.environ.get("CORVO_API_URL", "http://localhost:8787")).rstrip("/")
        self.token = token or os.environ.get("CORVO_INGEST_TOKEN")
        self.timeout = timeout
        if not self.token:
            raise RuntimeError("CORVO_INGEST_TOKEN não definido (use variável de ambiente, nunca o Git).")

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.token}", "User-Agent": USER_AGENT}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{self.base}{path}", data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - URL vem da configuração do projeto
            return json.loads(resp.read())


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OraclePublisher:
    def __init__(self, transport: Transport, gate: IntakeGate | None = None, clock=time.time) -> None:
        self.transport = transport
        self.gate = gate or IntakeGate(clock=clock)
        self._clock = clock
        self._buckets: dict[str, Counter[str]] = {}

    def pressure(self) -> Pressure:
        try:
            return Pressure(self.transport.request("GET", "/api/corvo/pressure")["pressure"])
        except (urllib.error.URLError, TimeoutError, ConnectionError, KeyError, ValueError, json.JSONDecodeError):
            return Pressure.ECONOMY

    def run(self, items: list[NewsItem], official_sources: frozenset[str] = frozenset()) -> dict:
        pressure = self.pressure()
        now = self._clock()
        bucket = _iso(now - now % 3600)
        c = self._buckets.setdefault(bucket, Counter())
        news = []
        for item in items:
            v = self.gate.admit(item, pressure)
            c["received"] += 1
            if v.decision is Decision.DROP:
                c["dropped"] += 1
                c[f"reason:{v.reason}"] += 1
                continue
            c["hot" if v.decision is Decision.HOT else "buffer"] += 1
            news.append({
                "item_id": hashlib.sha1(canonical_url(item.url).encode()).hexdigest()[:32],
                "source_id": item.source_id,
                "source_reliability": round(item.source_reliability, 3),
                "title": item.title[:400],
                "url": item.url[:1000],
                "published_at": _iso(item.published_at),
                "verdict": v.decision.value,
                "reason": v.reason,
                "relevance": v.relevance,
                "kind": classify_kind(item.title, item.source_id in official_sources),
                "topics": list(v.topics),
                "assets": [],  # impacto por ativo vem do motor de previsão (MNEME/CORVO), ainda não ligado
            })
        stats = [{
            "bucket": b, "pressure": pressure.value, "received": k["received"], "hot": k["hot"], "buffer": k["buffer"], "dropped": k["dropped"],
            "reasons": {n.removeprefix("reason:"): v for n, v in k.items() if n.startswith("reason:")},
        } for b, k in self._buckets.items()]
        result = self.transport.request("POST", "/api/corvo/ingest", {"news": news, "stats": stats[-48:]})
        return {"pressure": pressure.value, "sent_news": len(news), "received": len(items), "api": result}
