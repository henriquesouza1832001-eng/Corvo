from pulso_engine.intelligence.sensor_value import family_report, marginal_information_gain, verdict_hint


def day(family, d, **kw):
    base = {"family": family, "day": d, "observations": 100, "unique_signals": 60, "duplicates": 10, "events_contributed": 5, "independent_confirmations": 3,
            "false_positive_events": 1, "available_checks": 288, "ok_checks": 280, "fresh_checks": 250}
    return {**base, **kw}


def test_family_report_aggregates_and_flags_small_samples():
    rep = family_report([day("official", f"d{i}") for i in range(4)] + [day("social", "d0", observations=500, duplicates=400)])
    o = rep["official"]
    assert o["status"] == "OK" and o["observations_per_day"] == 100.0 and o["duplicate_ratio"] == 0.1 and o["availability"] == round(280 / 288, 4)
    assert o["false_positive_contribution"] == 0.2 and o["events_contributed"] == 20
    assert rep["social"]["status"] == "INSUFFICIENT_DATA" and rep["social"]["duplicate_ratio"] == 0.8  # 1 dia: não se tira conclusão


def events(n_physical_needed=6, n_total=30):
    ev = []
    for i in range(n_total):
        needs = i < n_physical_needed  # nestes eventos só "physical" + 1 origem de notícia: sem o físico, falta corroboração
        ev.append({"event_id": f"e{i}", "origins": {"physical": 1, "news": 1} if needs else {"news": 3, "social": 2, "physical": 1},
                   "first_seen": {"physical": 40, "news": 10} if needs else {"social": 30, "news": 5, "physical": 20}, "outcome": "FALSE" if i == 0 else "TRUE"})
    return ev


def test_leave_one_family_out_measures_marginal_gain_and_first_reporter():
    g = marginal_information_gain(events())
    assert g["physical"]["needed_for_corroboration"] == 6 and g["physical"]["marginal_gain"] == round(6 / 30, 4)
    assert g["physical"]["first_to_report"] == 6 and g["social"]["first_to_report"] == 24
    assert g["social"]["needed_for_corroboration"] == 0 and g["news"]["needed_for_corroboration"] == 6
    assert g["physical"]["false_positive_dependence"] == 1  # o único falso positivo dependia do físico para parecer corroborado
    assert all(v["status"] == "OK" for v in g.values())


def test_small_event_sample_is_insufficient_not_a_grade():
    g = marginal_information_gain(events(2, 8))
    assert all(v["status"] == "INSUFFICIENT_DATA" for v in g.values())
    assert verdict_hint({"status": "OK"}, g["physical"]) == "INSUFFICIENT_DATA"


def test_hint_is_descriptive_only_and_never_an_automatic_removal():
    rep = {"status": "OK", "duplicate_ratio": 0.8}
    useless = {"status": "OK", "marginal_gain": 0, "first_ratio": 0}
    assert verdict_hint(rep, useless) == "LOW_MARGINAL_VALUE_REVIEW"  # pede REVISÃO humana, não remove
    assert verdict_hint(rep, {"status": "OK", "marginal_gain": 0.2, "first_ratio": 0.1}) == "KEEP_MEASURING"
