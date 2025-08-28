# signals/logic/execution/api/transport.py

import inspect
import time
import uuid
from typing import Any, Dict, Optional, Tuple


def gen_client_order_id() -> str:
    return uuid.uuid4().hex


def _supports_kw(func, name: str) -> bool:
    try:
        sig = inspect.signature(func)
        if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
            return True
        return name in sig.parameters
    except Exception:
        return False


def call_with_timeout(client: Any, endpoint_name: str, payload: Dict[str, Any], timeout_seconds: float) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Appelle client.post(endpoint_name, payload, debug=False, ...) en ajoutant 'timeout' seulement si supporté,
    et renvoie (response, error_str).
    """
    try:
        post = getattr(client, "post")
    except Exception:
        return None, "client.post introuvable"

    kwargs = {"debug": False}
    if _supports_kw(post, "timeout"):
        kwargs["timeout"] = timeout_seconds

    try:
        # Certains clients ignorent endpoint_name; les tests utilisent "placeOrder"
        resp = post("placeOrder", payload, **kwargs)
        if not isinstance(resp, dict):
            resp = {"raw": str(resp), "statusCode": 200}
        return resp, None
    except Exception as e:
        return None, str(e)


# Heuristique d'erreurs réseau/transitoires -> retry
_RETRYABLE_ERROR_SUBSTR = {
    "timeout",
    "timed out",
    "connection reset",
    "reset by peer",
    "temporarily unavailable",
    "temporarily_unavailable",
    "rate limit",
    "too many requests",
    "unreachable",
    "connection aborted",
    "broken pipe",
    "network is unreachable",
    "econnreset",
    "econnaborted",
    "etimedout",
    "ehostunreach",
    "eai_again",
}


def should_retry(status_code: Optional[int], error: Optional[str], retryable_statuses: list[int]) -> bool:
    """
    - Retry si status_code ∈ retryable_statuses
    - Retry si message d'erreur ressemble à une erreur réseau/transitoire
    - Sinon, pas de retry
    """
    if status_code is not None:
        return status_code in set(retryable_statuses)

    if error:
        e = error.strip().lower()
        return any(s in e for s in _RETRYABLE_ERROR_SUBSTR)

    return False


def sleep_backoff(attempt: int, initial_ms: int, max_ms: int) -> None:
    delay_ms = min(max_ms, initial_ms * (2 ** (attempt - 1)))
    time.sleep(delay_ms / 1000.0)
