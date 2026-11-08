from corvo_engine.collect import run_cycle
from corvo_engine.intake import IntakeGate, NewsItem
from corvo_engine.intake.store import SeenStore
from corvo_engine.oracle import OraclePublisher

NOW = 1_700_000_000.0


class Fake:
    def __init__(self):
        self.sent = []

    def request(self, method, path, body=None):
        if path.endswith("/pressure"):
            return {"pressure": "normal"}
        self.sent.append(body)
        return {"ok": True}


def mk(src, title, url):
    return NewsItem(src, url, title, NOW - 60, "", 0.9)


FEEDS = [{"id": "a", "official": True}, {"id": "b"}, {"id": "broken"}]
DATA = {
    "a": [mk("a", "Fed announces rate cut as inflation cools", "https://a.com/1")],
    "b": [mk("b", "Earthquake hits Tokyo", "https://b.com/1"), mk("b", "Celebrity perfume launch", "https://b.com/2")],
}


def fetcher(feed):
    if feed["id"] == "broken":
        raise TimeoutError("fonte fora do ar")
    return DATA[feed["id"]]


def setup():
    t = Fake()
    pub = OraclePublisher(t, IntakeGate(clock=lambda: NOW), clock=lambda: NOW)
    return t, pub, SeenStore(":memory:", clock=lambda: NOW)


def test_cycle_isolates_failed_feed_and_counts_only_new_items():
    t, pub, store = setup()
    out = run_cycle(FEEDS, pub, store, fetcher=fetcher)
    assert list(out["feeds_failed"]) == ["broken"] and out["fetched"] == 3 and out["new"] == 3 and out["sent_news"] == 2
    assert t.sent[0]["stats"][0]["sources"] == {"a": 1, "b": 2}
    # fonte oficial vira "fato"; o resto fica "reportagem"
    kinds = {n["source_id"]: n["kind"] for n in t.sent[0]["news"]}
    assert kinds["a"] == "fato" and kinds["b"] == "reportagem"


def test_second_cycle_skips_already_seen_urls_and_sends_nothing():
    t, pub, store = setup()
    run_cycle(FEEDS, pub, store, fetcher=fetcher)
    n = len(t.sent)
    out = run_cycle(FEEDS, pub, store, fetcher=fetcher)
    assert out["new"] == 0 and len(t.sent) == n


def test_failed_publish_does_not_mark_items_as_seen():
    t, pub, store = setup()

    def boom(method, path, body=None):
        if path.endswith("/pressure"):
            return {"pressure": "normal"}
        raise ConnectionError("down")

    t.request = boom
    try:
        run_cycle(FEEDS, pub, store, fetcher=fetcher)
    except ConnectionError:
        pass
    assert len(store) == 0


def test_decisions_are_recorded_for_every_item_including_drops():
    t, pub, store = setup()
    run_cycle(FEEDS, pub, store, fetcher=fetcher)
    reasons = {d["title"]: d["reason"] for d in pub.last_decisions}
    assert reasons["Celebrity perfume launch"] == "irrelevant" and len(pub.last_decisions) == 3
