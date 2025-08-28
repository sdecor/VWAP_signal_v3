# tests/api/test_client.py

import json
import os
from pathlib import Path

from signals.logic.execution.api.client import place_order


def test_place_order_import_error(monkeypatch, tmp_path):
    # force import_api_client à échouer
    import signals.logic.execution.api.client as client
    monkeypatch.setattr(client, "import_api_client", lambda: None)

    # config pour audit path
    fake_cfg = {
        "api": {
            "audit_log_file": str(tmp_path / "audit.ndjson"),
            "max_retries": 0,
        }
    }
    import signals.logic.execution.api.settings as settings
    monkeypatch.setattr(settings, "load_api_settings", lambda: {
        "timeout_seconds": 2, "max_retries": 0, "backoff_initial_ms": 1, "backoff_max_ms": 1,
        "retryable_statuses": [429,500,502,503,504],
        "audit_log_file": fake_cfg["api"]["audit_log_file"],
    })

    res = place_order({"symbol": "CBOT_UB1!", "quantity": 1})
    assert res["status"] == "error"
    assert "import" in res["error"]

    # audit a été écrit
    with open(fake_cfg["api"]["audit_log_file"], "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f]
    assert any(rec.get("event") == "import_error" for rec in lines)


def test_place_order_ok_no_retry(monkeypatch, tmp_path):
    # Fake API client qui renvoie ok
    class FakeClient:
        def post(self, name, payload, debug=False, **kwargs):
            assert name == "placeOrder"
            return {"statusCode": 200, "id": "X", "echo": payload}

    import signals.logic.execution.api.client as client
    monkeypatch.setattr(client, "import_api_client", lambda: FakeClient)

    # settings: pas de retry, audit vers tmp
    audit_file = tmp_path / "audit_ok.ndjson"
    monkeypatch.setattr(client, "load_api_settings", lambda: {
        "timeout_seconds": 2, "max_retries": 0, "backoff_initial_ms": 1, "backoff_max_ms": 1,
        "retryable_statuses": [429,500,502,503,504],
        "audit_log_file": str(audit_file),
    })

    res = place_order({"symbol": "CBOT_UB1!", "quantity": 1})
    assert res["status"] == "ok"
    assert res["attempts"] == 1
    assert "request_id" in res

    # audit contient request + response
    with open(audit_file, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f]
    events = [rec["event"] for rec in lines]
    assert events.count("request") == 1
    assert events.count("response") == 1


def test_place_order_retry_then_ok(monkeypatch, tmp_path):
    # Fake API client qui échoue une fois (HTTP 500) puis OK
    class FakeClient:
        def __init__(self):
            self.calls = 0
        def post(self, name, payload, debug=False, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"statusCode": 500, "msg": "oops"}
            return {"statusCode": 200, "id": "OK"}

    import signals.logic.execution.api.client as client
    fc = FakeClient()
    monkeypatch.setattr(client, "import_api_client", lambda: lambda: fc)  # import -> FakeClient class; call -> instance fc

    # settings: 1 retry possible
    audit_file = tmp_path / "audit_retry.ndjson"
    monkeypatch.setattr(client, "load_api_settings", lambda: {
        "timeout_seconds": 1, "max_retries": 1, "backoff_initial_ms": 1, "backoff_max_ms": 2,
        "retryable_statuses": [429,500,502,503,504],
        "audit_log_file": str(audit_file),
    })

    # neutralise sleep
    import signals.logic.execution.api.transport as tr
    monkeypatch.setattr(tr, "sleep_backoff", lambda *a, **k: None)

    res = place_order({"symbol": "CBOT_UB1!", "quantity": 1})
    assert res["status"] == "ok"
    assert res["attempts"] == 2

    # audit contient 2 requests et 2 responses
    with open(audit_file, "r", encoding="utf-8") as f:
        events = [json.loads(l)["event"] for l in f]
    assert events.count("request") == 2
    assert events.count("response") == 2


def test_place_order_timeout_kw_not_supported(monkeypatch, tmp_path):
    # Fake client sans param timeout
    class FakeClientNoTimeout:
        def post(self, name, payload, debug=False):
            return {"statusCode": 200, "id": "NT"}

    import signals.logic.execution.api.client as client
    monkeypatch.setattr(client, "import_api_client", lambda: FakeClientNoTimeout)

    audit_file = tmp_path / "audit_no_to.ndjson"
    monkeypatch.setattr(client, "load_api_settings", lambda: {
        "timeout_seconds": 1, "max_retries": 0, "backoff_initial_ms": 1, "backoff_max_ms": 1,
        "retryable_statuses": [429,500,502,503,504],
        "audit_log_file": str(audit_file),
    })

    res = place_order({"symbol": "CBOT_UB1!", "quantity": 1})
    assert res["status"] == "ok"
    assert res["response"]["id"] == "NT"
