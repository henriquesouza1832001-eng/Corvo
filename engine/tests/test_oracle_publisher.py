import urllib.error

from corvo_engine.intake import IntakeGate, NewsItem
from corvo_engine.oracle import OraclePublisher, classify_kind

NOW = 1_700_000_000.0


class Fake:
    def __init__(self, pressure="normal", fail_pressure=False):
        self.sent, self.pressure, self.fail = [], pressure, fail_pressure

    def request(self, method, path, body=None):
        if path.endswith("/pressure"):
            if self.fail:
                raise urllib.error.URLError("down")
            return {"pressure": self.pressure}
        self.sent.append(body)
        return {"ok": True}


def mk(title, url, src="a"):
    return NewsItem(src, url, title, NOW - 60, "", 0.9)


def pub(fake):
    return OraclePublisher(fake, IntakeGate(clock=lambda: NOW), clock=lambda: NOW)


def test_only_admitted_items_are_sent_and_drops_are_counted():
    f = Fake()
    out = pub(f).run([mk("Fed announces rate cut as inflation cools", "https://x.com/1"), mk("Celebrity perfume launch", "https://x.com/2"), mk("Fed announces rate cut as inflation cools", "https://x.com/1?utm_source=t")])
    body = f.sent[0]
    assert [n["verdict"] for n in body["news"]] == ["hot"] and out["sent_news"] == 1
    s = body["stats"][0]
    assert (s["received"], s["hot"], s["dropped"]) == (3, 1, 2)
    assert s["reasons"] == {"irrelevant": 1, "duplicate_url": 1}
    assert body["news"][0]["assets"] == [] and body["news"][0]["kind"] == "reportagem"


def test_unreadable_pressure_falls_back_to_economy():
    f = Fake(fail_pressure=True)
    p = pub(f)
    assert p.pressure().value == "economy"
    # relevância média (política) cai no buffer, nunca em HOT, sob economia
    p.run([mk("Prime minister resigns as government collapses", "https://x.com/9")])
    assert f.sent[0]["news"][0]["verdict"] == "buffer"


def test_each_run_sends_only_its_own_delta_for_the_hour():
    # o Worker soma os deltas; assim execuções sem memória (GitHub Actions) não se sobrescrevem
    f = Fake()
    p = pub(f)
    p.run([mk("Earthquake hits Tokyo", "https://x.com/q1")])
    p.run([mk("Tsunami warning after quake", "https://x.com/q2")])
    assert f.sent[0]["stats"][0]["received"] == 1 and f.sent[1]["stats"][0]["received"] == 1


def test_classify_kind_defaults_to_report_and_official_is_fact():
    assert classify_kind("Analyst says bitcoin will soar") == "opiniao"
    assert classify_kind("Sources said talks collapsed") == "rumor"
    assert classify_kind("Bitcoin could reach 200k") == "previsao"
    assert classify_kind("Press release", official=True) == "fato"
    assert classify_kind("Press release") == "reportagem"


def test_only_current_hour_bucket_is_sent_and_empty_runs_send_nothing():
    f = Fake()
    clock = [NOW]
    p = OraclePublisher(f, IntakeGate(clock=lambda: clock[0]), clock=lambda: clock[0])
    p.run([mk("Earthquake hits Tokyo", "https://x.com/q1")])
    clock[0] += 3 * 3600
    p.run([NewsItem("a", "https://x.com/q2", "Tsunami warning after quake", clock[0] - 60, "", 0.9)])
    assert len(f.sent[1]["stats"]) == 1
    n = len(f.sent)
    p.run([])
    assert len(f.sent) == n


def test_geolocation_is_attached_only_when_a_place_is_recognised():
    from corvo_engine.intake import locate
    f = Fake()
    pub(f).run([mk("Fed announces rate cut as inflation cools", "https://x.com/1"), mk("Earthquake and tsunami strike, blackout reported", "https://x.com/2")])
    by = {n["url"]: n for n in f.sent[0]["news"]}
    assert by["https://x.com/1"]["region"] == "Estados Unidos" and by["https://x.com/2"]["lat"] is None
    assert locate("Missile strike hits Kyiv as Russia escalates")[0] == "Ucrânia"
    assert locate("Ira e rancor no mercado") is None
