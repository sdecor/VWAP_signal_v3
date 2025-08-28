# signals/logic/execution/payload.py

from typing import Dict, Any, Tuple

from signals.loaders.config_loader import (
    get_symbol,
    get_order_type,
    get_time_in_force,
    get_dry_run_mode,
    get_default_lots,
)
# ⚠️ Importe le module, pas la valeur (pour que monkeypatch marche)
from signals.utils import env_loader as env


def extract_side_and_qty(signal: Dict[str, Any]) -> Tuple[str, float]:
    side = (signal.get("signal") or signal.get("action") or "FLAT").upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"Côté invalide pour exécution: {side}")
    qty = float(signal.get("qty") or get_default_lots())
    return side, qty


def build_order_payload(signal: Dict[str, Any]) -> Dict[str, Any]:
    side, qty = extract_side_and_qty(signal)
    payload = {
        "accountId": env.ACCOUNT_ID,     # ✅ lu dynamiquement
        "symbol": get_symbol(),
        "side": side,
        "orderType": get_order_type(),
        "timeInForce": get_time_in_force(),
        "quantity": qty,
        # "price": signal.get("limit_price"),
        # "stopPrice": signal.get("stop_price"),
        # "clientOrderId": signal.get("client_order_id"),
        # "tag": "vwap_mr_live",
    }
    return payload


def is_dry_run() -> bool:
    return get_dry_run_mode()
