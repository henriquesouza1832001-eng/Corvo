"""Vazamento temporal: nunca usar, ao prever, informação que só existiria depois. A bancada de prova depende disto.

`as_of_view` devolve só o que Munin JÁ SABIA naquele instante. `check_resolution_after` garante que um resultado só vale se foi
observado depois do horizonte da previsão (nunca antes, nunca com dado de outro momento).
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping


class LeakageError(AssertionError):
    """Alguma informação do futuro entrou na previsão."""


def _ts(v: str | datetime) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def as_of_view(rows: Iterable[Mapping], as_of: str | datetime, key: str = "ingested_at") -> list[Mapping]:
    """Linhas conhecidas em `as_of`: só as com `key` <= `as_of`. Usar o instante de CHEGADA (ingested_at), não o de publicação."""
    cut = _ts(as_of)
    return [r for r in rows if _ts(r[key]) <= cut]


def assert_point_in_time(rows: Iterable[Mapping], as_of: str | datetime, key: str = "ingested_at") -> None:
    """Falha se alguma linha for posterior ao instante da previsão (use em testes e na montagem de features)."""
    cut = _ts(as_of)
    bad = [r for r in rows if _ts(r[key]) > cut]
    if bad:
        raise LeakageError(f"{len(bad)} linha(s) posterior(es) a {cut.isoformat()} entraram na previsão")


def check_resolution_after(created_at: str | datetime, resolves_at: str | datetime, observed_at: str | datetime) -> None:
    """O resultado precisa ser observado em ou depois de `resolves_at`, e a previsão criada antes do horizonte."""
    created, resolves, observed = _ts(created_at), _ts(resolves_at), _ts(observed_at)
    if resolves <= created:
        raise LeakageError("o horizonte precisa ser posterior à criação da previsão")
    if observed < resolves:
        raise LeakageError("resultado observado antes do horizonte: ainda não vale como resolução")
