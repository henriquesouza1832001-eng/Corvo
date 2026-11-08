"""Publicador do CORVO: passa as notícias pelo portão e empurra o resultado à API (Cloudflare), que alimenta o painel."""
from .publisher import HttpTransport, OraclePublisher, classify_kind

__all__ = ["HttpTransport", "OraclePublisher", "classify_kind"]
