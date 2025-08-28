# tests/api/test_transport.py

import time
from signals.logic.execution.api.transport import should_retry, sleep_backoff


def test_should_retry_on_status_and_error():
    # Status retryable
    assert should_retry(500, None, [429, 500])
    # Error string retryable
    assert should_retry(None, "connection reset by peer", [429, 500])
    # Neither
    assert not should_retry(200, None, [429, 500])
    assert not should_retry(None, "some other error", [429, 500])


def test_sleep_backoff_is_bounded(monkeypatch):
    # remplace time.sleep pour ne pas attendre
    called = {"secs": []}
    monkeypatch.setattr(time, "sleep", lambda s: called["secs"].append(s))

    sleep_backoff(attempt=1, initial_ms=100, max_ms=500)
    sleep_backoff(attempt=3, initial_ms=100, max_ms=500)  # 100*2^(3-1)=400ms +/- jitter
    sleep_backoff(attempt=10, initial_ms=100, max_ms=500) # plafonné à 500ms +/- jitter

    assert len(called["secs"]) == 3
    # chaque sleep est entre 0 et ~0.6s (500ms + jitter 10%)
    assert all(0.0 <= s <= 0.6 for s in called["secs"])
