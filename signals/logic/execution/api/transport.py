# signals/logic/execution/api/transport.py

import random
import time
from typing import Any, Dict, Optional, Tuple

def gen_client_order_id(prefix: str = "vwap") -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:16]}"

def should_retry(status_code: Optional[int], error: Optional[str], retryable_statuses: list[int]) -> bool:
    if status_code is not None and status_code in retryable_statuses:
        return True
    if error:
        s = error.lower()
        for needle in ("timeout", "temporarily", "unavailable", "connection", "reset", "unreachable"):
            if needle in s:
                return True
    return False

def sleep_backoff(attempt: int, initial_ms: int, max_ms: int) -> None:
    delay_ms = min(max_ms, int(initial_ms * (2 ** (attempt - 1))))
    jitter = random.uniform(-0.1, 0.1) * delay_ms
    time.sleep(max(0.0, (delay_ms + jitter) / 1000.0))

def call_with_timeout(client, endpoint_key: str, payload: Dict[str, Any], timeout_seconds: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Appelle client.post(); tente avec timeout kw, fallback sans.
    Retour: (resp_dict_or_None, error_str_or_None)
    """
    try:
        try:
            resp = client.post(endpoint_key, payload=payload, debug=False, timeout=timeout_seconds)  # type: ignore[arg-type]
        except TypeError:
            resp = client.post(endpoint_key, payload=payload, debug=False)
        if isinstance(resp, dict):
            return resp, None
        return {"raw": str(resp)}, None
    except Exception as e:
        return None, str(e)
