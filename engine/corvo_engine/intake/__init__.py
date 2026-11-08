"""CORVO: portão de admissão de notícias (decide o que entra no banco, antes de gravar)."""
from .gate import Decision, GateConfig, IntakeGate, NewsItem, Pressure, Verdict

__all__ = ["Decision", "GateConfig", "IntakeGate", "NewsItem", "Pressure", "Verdict"]
