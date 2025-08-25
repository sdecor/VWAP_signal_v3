# signals/logic/order_executor.py

from signals.loaders.config_loader import (
    get_symbol,
    get_order_type,
    get_time_in_force,
    get_dry_run_mode,
    get_default_lots,
)
from signals.utils.env_loader import ACCOUNT_ID  # sensible: .env
from signals.api.client import APIClient


def build_order_payload(signal: dict) -> dict:
    """
    Construit le payload pour l’endpoint placeOrder à partir du signal.
    Adapte les clés selon le schéma attendu par ton API.
    """
    side = signal["signal"]  # "BUY" / "SELL"
    qty = signal.get("qty") or get_default_lots()

    payload = {
        "accountId": ACCOUNT_ID,
        "symbol": get_symbol(),
        "side": side,                  # BUY / SELL
        "orderType": get_order_type(), # market / limit ...
        "timeInForce": get_time_in_force(),
        "quantity": qty,
        # Optionnels selon API :
        # "price": signal.get("limit_price"),
        # "stopPrice": signal.get("stop_price"),
        # "clientOrderId": signal.get("client_order_id"),
        # "tag": "vwap_mr_live",
    }
    return payload


def execute_signal(signal: dict) -> dict:
    """
    Exécute le signal : dry-run (log) ou envoi réel via APIClient.
    Retourne la réponse (ou un dict d’info en dry-run).
    """
    payload = build_order_payload(signal)
    if get_dry_run_mode():
        print(f"🟡 DRY-RUN → PlaceOrder {payload}")
        return {"status": "dry_run", "payload": payload}

    client = APIClient()
    print(f"🟢 LIVE → PlaceOrder {payload}")
    try:
        resp = client.post("placeOrder", payload=payload, debug=False)
        print(f"✅ Ordre envoyé. Réponse API: {resp}")
        return {"status": "ok", "response": resp, "payload": payload}
    except Exception as e:
        print(f"❌ Échec envoi d’ordre: {e}")
        return {"status": "error", "error": str(e), "payload": payload}
