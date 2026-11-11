"""Closed, deterministic questions and price-resolution rules for Munin."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from .impact import Hypothesis, candidates


MIN_VOLATILITY_RETURNS = 30
SIGMA_THRESHOLD = 1.0
PRICE_RULE_VERSION = "local-close-abnormal-return-v2"


@dataclass(frozen=True)
class ClosedQuestion:
    question_id: str
    event_id: str
    topic: str
    asset: str
    direction: str
    horizon_hours: int
    text: str
    rule_version: str = PRICE_RULE_VERSION
    sigma_threshold: float = SIGMA_THRESHOLD
    min_prior_returns: int = MIN_VOLATILITY_RETURNS
    instrument_available: bool = False
    resolution_rule: str = "last known close at/before event to first close at/after horizon; abnormal return versus 30 prior same-horizon returns"
    annulment_rule: str = "cancel if the instrument's known market calendar is closed during the forecast window"


_CONTINUOUS_ASSETS = frozenset({"BTC", "ETH", "SOL", "BNB", "XRP"})
_FX_ASSETS = frozenset({"USDBRL", "USDEUR", "USDJPY", "USDGBP", "USDCNY"})


def _horizon_hours(value: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]*)h", value)
    if not match:
        raise ValueError(f"unsupported horizon: {value}")
    return int(match.group(1))


def _question(event_id: str, topic: str, h: Hypothesis, available: frozenset[str]) -> ClosedQuestion:
    hours = _horizon_hours(h.horizon)
    action = {
        "up": "excederá +1 desvio-padrão",
        "down": "ficará abaixo de -1 desvio-padrão",
        "volatile": "terá valor absoluto acima de 1 desvio-padrão",
    }.get(h.direction)
    if action is None:
        raise ValueError(f"invalid hypothesis direction: {h.direction}")
    text = (
        f"Nas {hours} horas após o evento {event_id}, o retorno anormal logarítmico de {h.asset} "
        f"{action} da média e do desvio-padrão de 30 retornos de {hours}h anteriores ao instante em que o evento ficou disponível?"
    )
    raw_id = "|".join((event_id, topic, h.asset, h.direction, h.horizon, PRICE_RULE_VERSION))
    qid = "q_" + hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:20]
    return ClosedQuestion(
        question_id=qid,
        event_id=event_id,
        topic=topic,
        asset=h.asset,
        direction=h.direction,
        horizon_hours=hours,
        text=text,
        instrument_available=h.asset in available,
        annulment_rule=(
            "no market-close annulment; crypto trades continuously"
            if h.asset in _CONTINUOUS_ASSETS
            else "cancel when the FX weekend closure intersects the horizon (UTC approximation)"
            if h.asset in _FX_ASSETS
            else "calendar unknown until an exact local instrument is registered; keep unresolved"
        ),
    )


def questions_for_event(
    event: object,
    *,
    available_price_symbols: set[str] | frozenset[str] = frozenset(),
) -> list[ClosedQuestion]:
    """Create one closed question per event-topic/hypothesis pair.

    Availability requires an exact local price symbol match. In particular,
    ``USD`` is not silently mapped to one of several possible FX pairs, and
    assets without local prices remain explicit pending questions.
    """
    event_id = str(getattr(event, "event_id", "") or "").strip()
    topics = tuple(sorted(set(getattr(event, "topics", ()) or ())))
    if not event_id or not topics:
        return []
    available = frozenset(str(symbol) for symbol in available_price_symbols)
    out: list[ClosedQuestion] = []
    for topic in topics:
        out.extend(_question(event_id, topic, hypothesis, available) for hypothesis in candidates([topic]))
    # Keep one question per topic: the baseline key is topic-specific, so
    # collapsing equal hypotheses across topics would silently discard evidence.
    unique: dict[tuple[str, str, str, int], ClosedQuestion] = {}
    for question in out:
        key = (question.topic, question.asset, question.direction, question.horizon_hours)
        unique.setdefault(key, question)
    return list(unique.values())
