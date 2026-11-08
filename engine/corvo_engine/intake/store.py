"""Memória de itens já vistos (SQLite local no Oracle): evita reavaliar e reenviar a mesma notícia a cada ciclo.

O que o CORVO guarda de uma notícia DESCARTADA é só o hash da URL e a hora (alguns bytes, por 48 h): nunca o texto. O corpo completo
só existe em memória durante o ciclo. Notícia aprovada é gravada no banco do painel; descartada vira contador e este hash.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time

from .gate import canonical_url


def url_key(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:32]


class SeenStore:
    def __init__(self, path: str = ":memory:", ttl_s: float = 48 * 3600, clock=time.time) -> None:
        self._db = sqlite3.connect(path)
        self._db.execute("CREATE TABLE IF NOT EXISTS seen (k TEXT PRIMARY KEY, ts REAL NOT NULL)")
        self._ttl, self._clock = ttl_s, clock
        self.prune()

    def has(self, key: str) -> bool:
        row = self._db.execute("SELECT ts FROM seen WHERE k = ?", (key,)).fetchone()
        return row is not None and self._clock() - row[0] < self._ttl

    def add_many(self, keys: list[str]) -> None:
        now = self._clock()
        self._db.executemany("INSERT OR REPLACE INTO seen (k, ts) VALUES (?, ?)", [(k, now) for k in keys])
        self._db.commit()

    def prune(self) -> int:
        cur = self._db.execute("DELETE FROM seen WHERE ts < ?", (self._clock() - self._ttl,))
        self._db.commit()
        return cur.rowcount

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
