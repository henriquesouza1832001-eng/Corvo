"""CORVO Sentinela (núcleo determinístico): detecta candidatos a anomalia, decide se investiga e mantém o ESTADO das
investigações. Sem LLM, sem rede: estatística (baseline, z-score, tendência) + regras configuráveis.

Fluxo: `detect_candidates` (escopo x categoria com atividade fora do normal) -> `should_investigate` (gatilho) ->
`advance` (abre, atualiza ou encerra investigações, sem duplicar as já ativas). Deep search e validação (passos 6 e 7)
alimentam `evidence`/estado depois; aqui nasce o objeto que elas usam.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ..anomaly import NO_BASELINE, window_anomaly
from ..intelligence.trends import window_metrics
from ..models import Signal
from ..intelligence.baseline_hierarchy import ResolvedBaseline, resolve_baseline
from ..intelligence.context_engine import ContextCalendar
from ..intelligence.coverage import LOW_COVERAGE
from .provenance import provenance

UNEXPECTED_FLOOR = 0.35
ALERT_CATEGORIES = frozenset({"WEATHER", "EMERGENCY", "INFRASTRUCTURE", "HEALTH", "TRAFFIC", "SECURITY"})
STATES = ("NEW", "INVESTIGATING", "CORRELATING", "WAITING_CONFIRMATION", "CONFIRMED", "DISPUTED", "RESOLVING", "CLOSED")


@dataclass(frozen=True)
class SentinelConfig:
    """Todos os valores configuráveis (nenhum número mágico escondido)."""
    anomaly_score: float = 0.65
    unexpected_floor: float = 0.35  # abaixo disto, com baseline VÁLIDO, a atividade é ESPERADA: diversidade/oficial de rotina não abre
    min_anomaly_origins: int = 2  # origens para a ANOMALIA abrir (>= 1 delas não social): 1000 cópias de uma matéria são 1 origem
    min_origins: int = 3  # origens independentes (cópias não contam) para a diversidade de tipos abrir uma investigação
    source_type_count: int = 3
    min_signals_for_types: int = 3  # tipos de fonte só disparam com volume mínimo (2 sinais de 3 tipos não é nada)
    emerging_term_score: float = 0.75
    official_signal: bool = True
    window_min: int = 15
    context_window_min: int = 60
    resolve_after_min: int = 90  # sem atividade anormal por este tempo: RESOLVING
    close_after_min: int = 180  # e depois de mais este tempo: CLOSED
    dedup_window_min: int = 360  # reaproveita investigação ativa no mesmo escopo/categoria dentro desta janela


@dataclass(frozen=True)
class Candidate:
    scope: str
    category: str
    score: float
    z: float
    basis: str
    signal_count: int
    source_type_count: int
    official_signal: bool
    emerging_term_score: float = 0.0
    signal_hashes: tuple[str, ...] = ()
    origin_count: int = 0  # origens (cópias/republicações já fundidas)
    independent_origins: int = 0  # origens NÃO sociais
    official_alert: bool = False  # sinal oficial de categoria de impacto físico (clima, emergência, infraestrutura...), não boletim de rotina
    baseline_valid: bool = True  # False = não se sabe o que é normal (BASELINE INSUFICIENTE)
    baseline_level: str = "dow_hour"  # nível do fallback usado (dow_hour, hour, all_hours, national_scaled, insufficient)
    baseline_reliability: float = 1.0  # 0-1
    coverage: float | None = None  # razão de fontes FRESH (None = não se aplica/desconhecida); baixa = visão degradada
    context: tuple[str, ...] = ()  # eventos programados/feriado que explicam parte da atividade (o ESPERADO nunca confirma nada)

    @property
    def expectedness(self) -> str:
        """UNEXPECTED (fora do normal), EXPECTED (dentro do normal conhecido) ou UNKNOWN (sem baseline: nada se afirma)."""
        return "UNEXPECTED" if self.score >= UNEXPECTED_FLOOR else ("EXPECTED" if self.baseline_valid else "UNKNOWN")


@dataclass(frozen=True)
class Investigation:
    investigation_id: str
    scope: str  # BR | UF:MG
    category: str
    status: str
    started_at: datetime
    last_update: datetime
    initial_anomaly: float
    anomaly: float  # última medida
    evidence_count: int
    official_confirmation: bool
    reasons: tuple[str, ...] = ()
    last_anomalous_at: datetime | None = None
    signal_hashes: tuple[str, ...] = field(default=())


def _id(scope: str, category: str, at: datetime) -> str:
    return "inv-" + hashlib.sha1(f"{scope}|{category}|{at.strftime('%Y%m%d%H')}".encode()).hexdigest()[:10]


def _baseline(rows: list[dict], scope: str, category: str, now: datetime, calendar: ContextCalendar | None = None) -> ResolvedBaseline:
    """Melhor base disponível com o fallback VISÍVEL (dia da semana x hora -> hora -> todas as horas -> nacional escalado -> inválido).
    Feriado conta como domingo quando há calendário. Nunca finge normal."""
    return resolve_baseline(rows, scope, category, now, calendar.holidays if calendar else None)


def detect_candidates(signals: list[Signal], obs_rows: list[dict], now: datetime,
                      cfg: SentinelConfig = SentinelConfig(), emerging: dict[tuple[str, str], float] | None = None,
                      duplicates_by_hash: dict[str, int] | None = None, calendar: ContextCalendar | None = None,
                      coverage: float | None = None) -> list[Candidate]:
    """Um candidato por (escopo, categoria) com atividade recente. O gatilho é decidido em `should_investigate`."""
    cells: dict[tuple[str, str], list[Signal]] = {}
    for s in signals:
        if s.category == "OTHER" or s.timestamp > now or s.collected_at > now:  # nada publicado OU coletado depois do corte entra
            continue
        for scope in ["BR"] + ([f"UF:{s.state}"] if s.state else []):
            cells.setdefault((scope, s.category), []).append(s)
    out = []
    for (scope, cat), sigs in sorted(cells.items()):
        win = window_metrics(sigs, now, cfg.window_min, duplicates_by_hash)
        ctx = window_metrics(sigs, now, cfg.context_window_min, duplicates_by_hash)
        if not win.signal_count and not ctx.signal_count:
            continue
        # Contexto: um evento programado ativo (jogo, show) eleva o normal: o volume é comparado com o normal AJUSTADO, não com o do dia comum.
        mult, ctx_labels = calendar.expected_multiplier(scope, cat, now) if calendar else (1.0, ())
        rb = _baseline(obs_rows, scope, cat, now, calendar)
        an = window_anomaly(round(win.signal_count / mult), cfg.window_min, rb.base)
        window = [s for s in sigs if now - s.timestamp <= timedelta(minutes=cfg.context_window_min)]
        recent = tuple(sorted(s.hash for s in window))
        prov = provenance(window)
        alert = any(s.source_class == "OFFICIAL" and s.category in ALERT_CATEGORIES for s in window)
        out.append(Candidate(scope, cat, an["score"], an["z"], an["basis"], ctx.signal_count, ctx.source_type_count,
                             ctx.official_confirmation, (emerging or {}).get((scope, cat), 0.0), recent,
                             prov["origin_count"], prov["independent_origin_count"], alert, an["status"] != NO_BASELINE, rb.level, rb.reliability, coverage, ctx_labels))
    return out


def should_investigate(c: Candidate, cfg: SentinelConfig = SentinelConfig()) -> tuple[bool, tuple[str, ...]]:
    """Gatilho: o INESPERADO manda; diversidade e sinal oficial só corroboram quando há inesperado (ou quando não se sabe o normal).

    - anomalia forte abre sozinha;
    - diversidade de tipos de fonte abre só se houver >= `min_origins` ORIGENS (cem cópias não são cem origens) E a atividade for
      inesperada ou o baseline for desconhecido (com baseline válido e atividade esperada, três tipos de fonte falando é rotina);
    - sinal oficial abre se for ALERTA de impacto físico, ou se vier junto de atividade inesperada; boletim oficial de rotina não;
    - termo emergente forte.
    Devolve os motivos (explicação do "por que abriu"); sem motivo = não abre."""
    reasons = []
    unexpected = c.score >= cfg.unexpected_floor
    # Volume bruto não é evidência: uma cascata de cópias (1 origem) ou uma enxurrada só de redes sociais não abre investigação sozinha.
    evidence_ok = c.origin_count >= cfg.min_anomaly_origins and c.independent_origins >= 1
    if c.score >= cfg.anomaly_score and evidence_ok:
        reasons.append(f"anomalia {c.score:.2f} (z {c.z:.1f}, base {c.basis}, {c.origin_count} origens)")
    gate = unexpected or not c.baseline_valid
    if gate and c.source_type_count >= cfg.source_type_count and c.signal_count >= cfg.min_signals_for_types and c.origin_count >= cfg.min_origins:
        why = "atividade inesperada" if unexpected else "base insuficiente: normal desconhecido"
        reasons.append(f"{c.source_type_count} tipos de fonte, {c.origin_count} origens ({why})")
    if cfg.official_signal and c.official_signal and (c.official_alert or unexpected):
        reasons.append("alerta oficial de impacto" if c.official_alert else "sinal oficial com atividade inesperada")
    if c.emerging_term_score >= cfg.emerging_term_score:
        reasons.append(f"termo emergente {c.emerging_term_score:.2f}")
    if reasons and c.coverage is not None and c.coverage < LOW_COVERAGE:  # a visão está degradada: a explicação diz isso
        reasons.append(f"visão degradada: cobertura {c.coverage:.0%}")
    return bool(reasons), tuple(reasons)


def find_active(active: list[Investigation], scope: str, category: str, now: datetime,
                cfg: SentinelConfig = SentinelConfig()) -> Investigation | None:
    """Evita pesquisa repetida (§54): investigação não encerrada da mesma categoria e escopo dentro da janela de tempo.
    BR e UF são escopos distintos de propósito: uma anomalia só em MG não cobre o país, e vice-versa."""
    for inv in active:
        if inv.status == "CLOSED" or inv.category != category or inv.scope != scope:
            continue
        if now - inv.last_update <= timedelta(minutes=cfg.dedup_window_min):
            return inv
    return None


def advance(active: list[Investigation], candidates: list[Candidate], now: datetime,
            cfg: SentinelConfig = SentinelConfig()) -> list[Investigation]:
    """Novo estado das investigações: abre as novas, atualiza as existentes e esfria/encerra as sem atividade anormal.
    Devolve só as que MUDARAM (escrita condicional no banco)."""
    changed: dict[str, Investigation] = {}
    for c in candidates:
        go, reasons = should_investigate(c, cfg)
        if not go:
            continue
        existing = find_active(active, c.scope, c.category, now, cfg)
        if existing is not None:
            hashes = tuple(sorted(set(existing.signal_hashes) | set(c.signal_hashes)))
            changed[existing.investigation_id] = replace(
                existing, last_update=now, last_anomalous_at=now, anomaly=c.score, signal_hashes=hashes,
                evidence_count=len(hashes), official_confirmation=existing.official_confirmation or c.official_signal,
                status="INVESTIGATING" if existing.status in ("NEW", "RESOLVING") else existing.status,
                reasons=tuple(dict.fromkeys(existing.reasons + reasons)),
            )
        else:
            inv = Investigation(_id(c.scope, c.category, now), c.scope, c.category, "NEW", now, now, c.score, c.score,
                                len(c.signal_hashes), c.official_signal, reasons, now, c.signal_hashes)
            changed[inv.investigation_id] = inv
    for inv in active:  # esfriamento: sem atividade anormal por tempo suficiente
        if inv.investigation_id in changed or inv.status == "CLOSED":
            continue
        quiet = now - (inv.last_anomalous_at or inv.last_update)
        if inv.status != "RESOLVING" and quiet >= timedelta(minutes=cfg.resolve_after_min):
            changed[inv.investigation_id] = replace(inv, status="RESOLVING", last_update=now)
        elif inv.status == "RESOLVING" and quiet >= timedelta(minutes=cfg.resolve_after_min + cfg.close_after_min):
            changed[inv.investigation_id] = replace(inv, status="CLOSED", last_update=now)
    return sorted(changed.values(), key=lambda i: i.investigation_id)
