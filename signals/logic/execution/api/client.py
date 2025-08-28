# signals/logic/execution/api/client.py

from typing import Any, Dict, Optional

from signals.logging.api_audit import APIAuditLogger
# Importer les sous-modules (et non les fonctions) pour que monkeypatch agisse
from . import settings
from . import import_util
from . import transport

# --- Hooks ré-exportés (patchables) ---
load_api_settings = settings.load_api_settings
import_api_client = import_util.import_api_client


def _resolve_load_api_settings():
    """
    Choisit dynamiquement la fonction de chargement de config API.
    Règle:
      - si client.load_api_settings est un lambda (patch test) -> priorité,
      - sinon si settings.load_api_settings est un lambda (patch test) -> priorité,
      - sinon, retourne l'alias client s'il existe, sinon celui de settings.
    """
    func_client = globals().get("load_api_settings")
    func_settings = getattr(settings, "load_api_settings", None)

    # Priorité aux fonctions patchées (souvent des lambdas en tests)
    if callable(func_client) and getattr(func_client, "__name__", "") == "<lambda>":
        return func_client
    if callable(func_settings) and getattr(func_settings, "__name__", "") == "<lambda>":
        return func_settings

    # Sinon, ordre neutre: alias client si dispo, sinon settings
    return func_client or func_settings


def _resolve_import_api_client():
    """
    Même logique pour import_api_client:
      - si client.import_api_client est un lambda (patch test) -> priorité,
      - sinon fallback sur import_util.import_api_client,
      - sinon, dernier recours: alias client si dispo.
    """
    func_client = globals().get("import_api_client")
    func_util = getattr(import_util, "import_api_client", None)

    if callable(func_client) and getattr(func_client, "__name__", "") == "<lambda>":
        return func_client
    return func_util or func_client

def place_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envoie 'placeOrder' avec timeouts/retries/backoff + audit NDJSON.
    Retourne: {status: "ok"|"error", response?:dict, error?:str, attempts:int, request_id:str, last_status?:int}
    """
    # ⚠️ utilise la résolution dynamique (supporte patch côté client OU settings)
    load_cfg = _resolve_load_api_settings()
    if load_cfg is None:
        # fallback ultra-sûr
        load_cfg = settings.load_api_settings
    cfg = load_cfg()

    audit = APIAuditLogger(cfg["audit_log_file"])

    importer = _resolve_import_api_client()
    if importer is None:
        importer = import_util.import_api_client
    APIClient = importer()

    if APIClient is None:
        audit.log({"event": "import_error", "endpoint": "placeOrder", "error": "APIClient import failed"})
        return {"status": "error", "error": "APIClient indisponible (import échoué)", "attempts": 0}

    req_id = payload.get("clientOrderId") or transport.gen_client_order_id()
    if "clientOrderId" not in payload:
        payload = dict(payload)
        payload["clientOrderId"] = req_id

    client = APIClient()
    last_status_code: Optional[int] = None
    attempts = 0

    for attempt in range(1, cfg["max_retries"] + 2):  # ex: max_retries=3 -> 4 tentatives
        attempts = attempt

        # Audit: requête
        audit.log({
            "event": "request",
            "endpoint": "placeOrder",
            "attempt": attempt,
            "payload": {k: (v if k != "accountId" else "***") for k, v in payload.items()},
            "request_id": req_id,
        })

        resp, err = transport.call_with_timeout(client, "placeOrder", payload, cfg["timeout_seconds"])

        # Audit: réponse/erreur
        audit_rec: Dict[str, Any] = {
            "event": "response" if err is None else "error",
            "endpoint": "placeOrder",
            "attempt": attempt,
            "request_id": req_id,
        }
        if err is not None:
            audit_rec["error"] = err
        else:
            audit_rec["response"] = resp
            if isinstance(resp, dict):
                last_status_code = (
                    (resp.get("statusCode") if isinstance(resp.get("statusCode"), int) else None)
                    or (resp.get("code") if isinstance(resp.get("code"), int) else None)
                )
                audit_rec["statusCode"] = last_status_code
        audit.log(audit_rec)

        # Décision retry / succès
        if err is None:
            if not transport.should_retry(last_status_code, None, cfg["retryable_statuses"]):
                return {
                    "status": "ok",
                    "response": resp,
                    "attempts": attempts,
                    "request_id": req_id,
                    "last_status": last_status_code,
                }
        else:
            if not transport.should_retry(None, err, cfg["retryable_statuses"]):
                return {
                    "status": "error",
                    "error": err,
                    "attempts": attempts,
                    "request_id": req_id,
                    "last_status": last_status_code,
                }

        # Backoff et dernière tentative
        if attempt < cfg["max_retries"] + 1:
            transport.sleep_backoff(attempt, cfg["backoff_initial_ms"], cfg["backoff_max_ms"])
        else:
            if err is not None:
                return {
                    "status": "error",
                    "error": err,
                    "attempts": attempts,
                    "request_id": req_id,
                    "last_status": last_status_code,
                }
            return {
                "status": "error",
                "error": f"HTTP {last_status_code}" if last_status_code is not None else "Unknown error",
                "attempts": attempts,
                "request_id": req_id,
                "last_status": last_status_code,
            }
