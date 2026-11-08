"""Coleta global do CORVO: lê os feeds do catálogo, descarta o que já foi visto e entrega ao portão/publicador."""
from .feeds import fetch_feed, load_catalog
from .runner import run_cycle

__all__ = ["fetch_feed", "load_catalog", "run_cycle"]
