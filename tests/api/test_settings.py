# tests/api/test_settings.py

from signals.logic.execution.api.settings import load_api_settings


def test_load_api_settings_reads_config(monkeypatch):
    fake = {
        "api": {
            "timeout_seconds": 7,
            "max_retries": 4,
            "backoff_initial_ms": 150,
            "backoff_max_ms": 1200,
            "retryable_statuses": [429, 500],
            "audit_log_file": "logs/custom.ndjson",
        }
    }

    import signals.utils.config_reader as cfg
    monkeypatch.setattr(cfg, "load_config", lambda *a, **k: fake)

    s = load_api_settings()
    assert s["timeout_seconds"] == 7
    assert s["max_retries"] == 4
    assert s["backoff_initial_ms"] == 150
    assert s["backoff_max_ms"] == 1200
    assert s["retryable_statuses"] == [429, 500]
    assert s["audit_log_file"] == "logs/custom.ndjson"
