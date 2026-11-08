"""Lado Oracle do CORVO: roda junto do MNEME, passa as notícias pelo portão e empurra o resultado ao painel (Cloudflare)."""
from .publisher import HttpTransport, OraclePublisher, classify_kind

__all__ = ["HttpTransport", "OraclePublisher", "classify_kind"]
