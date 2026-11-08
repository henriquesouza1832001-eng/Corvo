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
    assert g.admit(item("Bitcoin ETF approved", age=30 * 3600)).reason == "stale"
    assert g.admit(item("", "https://x.com/z")).reason == "malformed"


def test_url_duplicate_ignores_tracking_params():
    g = gate()
    assert g.admit(item("Bitcoin ETF approved by SEC", "https://www.x.com/a?utm_source=tw")).decision is not Decision.DROP
    assert g.admit(item("Bitcoin ETFs see record outflows this week", "https://x.com/a/")).reason == "duplicate_url"


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
    t = "Prime minister resigns as government collapses"  # crise política: relevância média (~0,63)
    assert gate().admit(item(t)).decision is Decision.BUFFER
    assert gate().admit(item(t), Pressure.ECONOMY).decision is Decision.BUFFER
    assert gate().admit(item(t), Pressure.CRITICAL).decision is Decision.DROP
    t2 = "Fed announces surprise rate cut as inflation cools"  # banco central, alta relevância
    assert gate().admit(item(t2), Pressure.ECONOMY).decision is Decision.HOT


def test_only_market_moving_news_is_kept():
    g = gate()
    for title in ("Election campaign enters final week", "Local fire destroys 50 cars in parking lot", "Football star signs new deal",
                  "Bitcoin price prediction: will it hit 200k?", "Minister visits school in capital"):
        assert g.admit(item(title, f"https://x.com/{abs(hash(title))}")).decision is Decision.DROP, title
    for title in ("OPEC agrees surprise oil output cut", "US imposes new tariffs on Chinese chips", "Fire shuts down major refinery",
                  "Exchange hack drains 200 million from hot wallet"):
        assert g.admit(item(title, f"https://x.com/{abs(hash(title))}")).decision is not Decision.DROP, title


def test_topic_in_summary_alone_never_reaches_hot():
    v = gate().admit(item("City council approves budget", "https://x.com/s1", text="The war in the region and new tariffs were mentioned."))
    assert v.decision is not Decision.HOT


def test_critical_still_passes_top_news():
    v = gate().admit(item("Earthquake and tsunami hit coast, blackout reported at nationwide grid", rel=1.0), Pressure.CRITICAL)
    assert v.decision is Decision.HOT


def test_market_lexicon_accepts_the_right_things_and_drops_routine():
    g = gate()
    accept = [
        "Bank rate increased to 4% - November 2026 Monetary Policy Summary and Minutes",
        "Minutes of the Federal Open Market Committee, September 15-16, 2026",
        "U.S. added 165,000 jobs in October, blowing past 65,000 estimate",
        "US Treasury cuts off MEXC over alleged $16B in illicit transactions",
        "Bitcoin ETFs flip negative for 2026 after $1.28 billion outflow week",
        "AI stocks climb after trillions wiped from market values",
        "Paraguay's former president charged after bank collapse",
        "Russia launches massive strike on Kyiv",
    ]
    drop = [
        "Federal Reserve Board announces approval of application by Peoples Bancorp Inc.",
        "Federal Reserve Board announces enforcement action with Ontario Bancorporation, Inc.",
        "Bank of England announces the four animals that will feature on our next series of banknotes",
        "Minutes of the Money Market Committee meeting - September 2026",
        "Gold for the West Bank: Meet Palestinian karate champ Mariam Bsharat",
        "Trump's war secretary Hegseth may soon visit China",
        "Married off at 14: In Yemen's war, women and girls suffer devastating consequences",
        "Pro-Israel conservatives blast JD Vance for blaming Israel after GOP midterm losses",
    ]
    for i, title in enumerate(accept):
        assert g.admit(item(title, f"https://x.com/a{i}")).decision is not Decision.DROP, title
    for i, title in enumerate(drop):
        assert g.admit(item(title, f"https://x.com/d{i}")).decision is Decision.DROP, title


def test_relevance_is_judged_before_age_and_official_sources_get_a_longer_window():
    g = gate()
    # irrelevante e velho: o motivo é "irrelevant", não "stale"
    assert g.admit(item("Celebrity perfume launch", "https://x.com/o1", age=3 * 86400)).reason == "irrelevant"
    # relevante e velho (imprensa, 24 h): stale; a mesma notícia de fonte oficial (72 h) passa
    old = 2 * 86400
    assert g.admit(item("Fed announces rate cut as inflation cools", "https://x.com/o2", age=old)).reason == "stale"
    official = NewsItem("fed", "https://x.com/o3", "Fed announces rate cut as inflation cools", NOW - old, "", 0.95, 72 * 3600)
    assert g.admit(official).decision is Decision.HOT
