from datetime import datetime, timedelta, timezone

from pulso_engine.models import Signal
from pulso_engine.research.information_gain import information_gain
from pulso_engine.research.sentinel import Investigation
from pulso_engine.research.validator import validate

NOW = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)


def sig(i, cls="NEWS_REGIONAL", title=None, source=None, state="MG", conf=70, text=None):
    ts = NOW - timedelta(minutes=5)
    return Signal(signal_id=str(i), source_id=source or f"s{i}", source_class=cls, timestamp=ts, collected_at=ts,
                  title=title or f"Relato {i} de alagamento no bairro {['Centro', 'Norte', 'Sul', 'Leste'][i % 4]} {i * 13}", text=text, category="WEATHER",
                  hash=f"h{i}", state=state, geo_confidence=conf)


def inv():
    return Investigation("inv-1", "UF:MG", "WEATHER", "NEW", NOW, NOW, 0.7, 0.7, 1, False, (), NOW, ())


def actions(g):
    return [x.action for x in g]


def test_social_only_event_asks_for_official_physical_and_independent_evidence():
    sigs = [sig(i, "SOCIAL") for i in range(8)]
    g = information_gain("WEATHER", sigs, validate(inv(), sigs), "FLOOD", missing_sensors=["rainfall", "radar", "river_level"])
    assert {"CHECK_OFFICIAL_SOURCE", "CHECK_PHYSICAL_SENSOR", "FIND_INDEPENDENT_ORIGIN"} <= set(actions(g))
    assert all(0 < x.gain <= 1 and x.reason for x in g) and [x.gain for x in g] == sorted((x.gain for x in g), reverse=True)


def test_gain_disappears_when_the_gap_is_closed():
    sigs = [sig(1, "OFFICIAL", source="defesa-civil-idap", title="Defesa Civil confirma alagamento no bairro Norte"), sig(2, "NEWS_HIGH"), sig(3, "NEWS_REGIONAL")]
    g = information_gain("WEATHER", sigs, validate(inv(), sigs), "FLOOD", missing_sensors=[])
    assert "CHECK_OFFICIAL_SOURCE" not in actions(g) and "FIND_INDEPENDENT_ORIGIN" not in actions(g) and "CHECK_PHYSICAL_SENSOR" not in actions(g)


def test_contradiction_is_the_top_priority():
    sigs = [sig(i, "NEWS_REGIONAL", title=f"Barragem rompe e moradores fogem {i * 7} {['norte', 'sul', 'leste', 'centro'][i % 4]}") for i in range(4)]
    sigs.append(sig(50, "OFFICIAL", title="Defesa Civil nega rompimento de barragem", text="Não há rompimento.", source="dc"))
    v = validate(inv(), sigs)
    g = information_gain("INFRASTRUCTURE", sigs, v, None)
    assert g[0].action == "RESOLVE_CONTRADICTION" and "negativa oficial" in g[0].reason


def test_ambiguous_geography_suggests_resolution_and_is_deterministic():
    sigs = [sig(1, state="ES", conf=35), sig(2, state="BA", conf=35), sig(3, "OFFICIAL", state="PE", conf=35, source="o")]
    g1, g2 = information_gain("WEATHER", sigs, None), information_gain("WEATHER", sigs, None)
    assert "RESOLVE_GEOLOCATION" in actions(g1) and g1 == g2
    assert information_gain("WEATHER", [], None, top=2)[0].action == "CHECK_OFFICIAL_SOURCE"  # sem dado: pede o que falta, sem inventar nada
