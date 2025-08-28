# signals/logic/execution/api/settings.py

from typing import Any, Dict
# ❌ from signals.utils.config_reader import load_config
# ✅
from signals.utils import config_reader as cfg


def load_api_settings() -> Dict[str, Any]:
    conf = cfg.load_config()
    api = (conf.get("api") or {})
    return {
        "timeout_seconds": int(api.get("timeout_seconds", 5)),
        "max_retries": int(api.get("max_retries", 3)),
        "backoff_initial_ms": int(api.get("backoff_initial_ms", 200)),
        "backoff_max_ms": int(api.get("backoff_max_ms", 2000)),
        "retryable_statuses": list(api.get("retryable_statuses", [429, 500, 502, 503, 504])),
        "audit_log_file": api.get("audit_log_file", "logs/api_responses.ndjson"),
    }
