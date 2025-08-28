# signals/logic/execution/runner.py

from typing import Optional, Dict, Any

from signals.metrics.perf_tracker import PerformanceTracker
# import modules pour permettre monkeypatch
from . import payload as pl
from . import api_client as api


def execute_and_track_order(
    *,
    symbol: str,
    side: str,
    qty: float,
    limit_price: Optional[float],
    market_price: Optional[float],
    tracker: Optional[PerformanceTracker] = None,
) -> Dict[str, Any]:
    """
    Exécute un ordre en prod :
    - En dry-run : simule un fill et met à jour tracker.
    - En prod : appelle place_order() via APIClient, puis met à jour tracker.
    Retourne un dict structuré avec executed/fill_price/qty/side.
    """
    if pl.is_dry_run():
        if tracker and market_price is not None and qty > 0:
            tracker.on_fill(price=float(market_price), qty=float(qty), side=side)
        return {
            "status": "dry_run",
            "executed": True,
            "fill_price": market_price,
            "qty": qty,
            "side": side,
        }

    # Construire payload depuis signal minimal
    signal = {"action": side, "qty": qty}
    payload = pl.build_order_payload(signal)
    if limit_price is not None:
        payload["price"] = float(limit_price)

    # ✅ Appel via module api_client (patchable)
    api_result = api.place_order(payload)
    if api_result.get("status") != "ok":
        return {
            "status": "error",
            "executed": False,
            "error": api_result.get("error"),
            "fill_price": None,
            "qty": qty,
            "side": side,
        }

    # fallback : assume fill au market_price
    fill_price = market_price
    filled_qty = qty

    if tracker and filled_qty and fill_price is not None:
        tracker.on_fill(price=float(fill_price), qty=float(filled_qty), side=side)

    return {
        "status": "ok",
        "executed": True,
        "response": api_result.get("response"),
        "fill_price": fill_price,
        "qty": filled_qty,
        "side": side,
    }


def execute_signal_legacy(
    signal: Dict[str, Any],
    *,
    tracker: Optional[PerformanceTracker] = None,
    market_price: Optional[float] = None,
    limit_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    SHIM (ancienne API):
    - Dry-run : simule et met à jour tracker.
    - Prod : délègue à execute_and_track_order().
    """
    payload = pl.build_order_payload(signal)
    side, qty = pl.extract_side_and_qty(signal)

    if pl.is_dry_run():
        if tracker and market_price is not None and qty > 0:
            tracker.on_fill(price=float(market_price), qty=qty, side=side)
        return {
            "status": "dry_run",
            "payload": payload,
            "executed": True,
            "fill_price": market_price,
            "qty": qty,
            "side": side,
        }

    return execute_and_track_order(
        symbol=payload["symbol"],
        side=side,
        qty=qty,
        limit_price=limit_price if limit_price is not None else signal.get("limit_price"),
        market_price=market_price,
        tracker=tracker,
    )
