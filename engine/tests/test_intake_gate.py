from corvo_engine.intake import Decision, GateConfig, IntakeGate, NewsItem, Pressure

NOW = 1_000_000.0


def item(title, url="https://x.com/a", src="s", age=60, rel=0.9, text=""):
    return NewsItem(src, url, title, NOW - age, text, rel)


def gate(**kw):
    return IntakeGate(clock=lambda: NOW, **kw)


def test_hot_for_central_bank_news():
    v = gate().admit(item("Fed announces surprise rate cut as inflation cools"))
    assert v.decision is Decision.HOT and "banco_central" in v.topics


def test_irrelevant_and_noise_dropped():
    g = gate()
    assert g.admit(item("Local bakery wins award", "https://x.com/1")).reason == "irrelevant"
    assert g.admit(item("Sponsored: bitcoin giveaway", "https://x.com/2")).reason == "irrelevant"


def test_stale_and_malformed():
    g = gate()
    assert g.admit(item("Bitcoin ETF approved", age=10 * 3600)).reason == "stale"
    assert g.admit(item("", "https://x.com/z")).reason == "malformed"


def test_url_duplicate_ignores_tracking_params():
    g = gate()
    assert g.admit(item("Bitcoin ETF approved by SEC", "https://www.x.com/a?utm_source=tw")).decision is not Decision.DROP
    assert g.admit(item("Different words entirely about bitcoin hack", "https://x.com/a/")).reason == "duplicate_url"


def test_near_duplicate_title_across_sources():
    g = gate()
    g.admit(item("Russia launches missile strike on Ukraine energy grid", "https://a.com/1", "a"))
    v = g.admit(item("Russia launches missile strike on Ukraine energy grid today", "https://b.com/2", "b"))
    assert v.reason == "near_duplicate"


def test_source_quota_does_not_burn_on_junk():
    g = gate(config=GateConfig(per_source_per_hour=2))
    for i in range(10):
        g.admit(item(f"Celebrity gossip {i}", f"https://x.com/j{i}"))
    assert g.admit(item("Earthquake hits Tokyo", "https://x.com/q1")).decision is Decision.HOT
    assert g.admit(item("Tsunami warning issued after quake", "https://x.com/q2")).decision is Decision.HOT
    assert g.admit(item("Hurricane makes landfall in Florida", "https://x.com/q3")).reason == "source_quota"


def test_pressure_tightens_gate():
    t = "Congress debates election bill"  # política, relevância média
    assert gate().admit(item(t)).decision is Decision.HOT
    assert gate().admit(item(t), Pressure.ECONOMY).decision is Decision.BUFFER
    assert gate().admit(item(t), Pressure.CRITICAL).decision is Decision.DROP


def test_critical_still_passes_top_news():
    v = gate().admit(item("Earthquake and tsunami hit coast, blackout reported", rel=1.0), Pressure.CRITICAL)
    assert v.decision is Decision.HOT
