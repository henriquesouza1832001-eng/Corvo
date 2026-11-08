"""T9 robustness tests for malformed fetcher responses; no network is used."""
import time
import urllib.error
import pytest

from corvo_engine.collect import run_cycle
from corvo_engine.intake import IntakeGate, NewsItem
from corvo_engine.intake.store import SeenStore
from corvo_engine.oracle import OraclePublisher
from corvo_engine.collectors.news.rss import FeedContentError


NOW = 1_800_000_000.0


class DryTransport:
    def __init__(self):
        self.posts = []

    def request(self, method, path, body=None):
        if path.endswith("/pressure"):
            return {"pressure": "normal"}
        self.posts.append(body)
        return {"ok": True, "dry_run": True}


@pytest.mark.parametrize("bad_payload", [None, (), {}, [{}], "not-a-list"])
def test_malformed_feed_payload_is_isolated_without_dropping_healthy_feed(bad_payload):
    transport = DryTransport()
    publisher = OraclePublisher(transport, IntakeGate(clock=lambda: NOW), clock=lambda: NOW)
    store = SeenStore(":memory:", clock=lambda: NOW)
    feeds = [{"id": "bad"}, {"id": "healthy"}]

    def fetcher(feed):
        if feed["id"] == "bad":
            return bad_payload
        return [NewsItem("healthy", "https://healthy.test/1", "Fed signals rate decision after inflation data", NOW - 60, "", 0.9)]

    result = run_cycle(feeds, publisher, store, fetcher=fetcher, workers=2)

    assert result["feeds_failed"] == {"bad": "TypeError: fetcher must return a list of NewsItem records"}
    assert result["fetched"] == result["new"] == 1
    assert result["sent_news"] == 1
    assert len(store) == 1
    assert len(transport.posts) == 1


def test_cycle_records_bad_content_http_timeout_and_redirect_errors_per_feed():
    transport = DryTransport()
    publisher = OraclePublisher(transport, IntakeGate(clock=lambda: NOW), clock=lambda: NOW)
    store = SeenStore(":memory:", clock=lambda: NOW)
    failures = {
        "xml_broken": FeedContentError("XML broken"),
        "empty_body": FeedContentError("empty body"),
        "html_body": FeedContentError("unexpected HTML body"),
        "oversized": ValueError("feed exceeds size limit"),
        "stalled": TimeoutError("fetch deadline exceeded"),
        "forbidden": urllib.error.HTTPError("https://bad.test/feed", 403, "Forbidden", {}, None),
        "server_error": urllib.error.HTTPError("https://bad.test/feed", 503, "Unavailable", {}, None),
        "redirect_loop": urllib.error.URLError("redirect loop"),
    }
    feeds = [{"id": source} for source in (*failures, "healthy")]

    def fetcher(feed):
        source = feed["id"]
        if source == "stalled":
            time.sleep(0.01)  # finite stall simulation; no network call
        if source in failures:
            raise failures[source]
        return [NewsItem("healthy", "https://healthy.test/2", "Fed signals rate decision after inflation data", NOW - 60, "", 0.9)]

    result = run_cycle(feeds, publisher, store, fetcher=fetcher, workers=8)

    assert set(result["feeds_failed"]) == set(failures)
    assert result["feeds_failed"]["xml_broken"].startswith("FeedContentError:")
    assert result["feeds_failed"]["empty_body"].startswith("FeedContentError:")
    assert result["feeds_failed"]["html_body"].startswith("FeedContentError:")
    assert result["feeds_failed"]["oversized"].startswith("ValueError:")
    assert result["feeds_failed"]["stalled"].startswith("TimeoutError:")
    assert result["feeds_failed"]["forbidden"].startswith("HTTPError:")
    assert result["feeds_failed"]["server_error"].startswith("HTTPError:")
    assert result["feeds_failed"]["redirect_loop"].startswith("URLError:")
    assert result["fetched"] == result["new"] == result["sent_news"] == 1
    assert len(store) == 1 and len(transport.posts) == 1
