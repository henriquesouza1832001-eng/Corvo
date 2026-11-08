"""CORVO: portão de admissão de notícias (decide o que entra no banco, antes de gravar)."""
from .geo import locate
from .gate import Decision, GateConfig, IntakeGate, NewsItem, Pressure, Verdict

__all__ = ["locate", "Decision", "GateConfig", "IntakeGate", "NewsItem", "Pressure", "Verdict"]
