"""T9 robustness tests for malformed fetcher responses; no network is used."""
from corvo_engine.collect import run_cycle
from corvo_engine.intake import IntakeGate, NewsItem
from corvo_engine.intake.store import SeenStore
from corvo_engine.oracle import OraclePublisher


NOW = 1_800_000_000.0


class DryTransport:
    def __init__(self):
        self.posts = []

    def request(self, method, path, body=None):
        if path.endswith("/pressure"):
            return {"pressure": "normal"}
        self.posts.append(body)
        return {"ok": True, "dry_run": True}


def test_malformed_feed_payload_is_isolated_without_dropping_healthy_feed():
    transport = DryTransport()
    publisher = OraclePublisher(transport, IntakeGate(clock=lambda: NOW), clock=lambda: NOW)
    store = SeenStore(":memory:", clock=lambda: NOW)
    feeds = [{"id": "bad"}, {"id": "healthy"}]

    def fetcher(feed):
        if feed["id"] == "bad":
            return None
        return [NewsItem("healthy", "https://healthy.test/1", "Fed signals rate decision after inflation data", NOW - 60, "", 0.9)]

    result = run_cycle(feeds, publisher, store, fetcher=fetcher, workers=2)

    assert result["feeds_failed"] == {"bad": "TypeError: fetcher must return a list of NewsItem records"}
    assert result["fetched"] == result["new"] == 1
    assert result["sent_news"] == 1
    assert len(store) == 1
    assert len(transport.posts) == 1
