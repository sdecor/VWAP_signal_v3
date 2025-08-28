# signals/logic/order_executor.py
"""
Shim de compatibilité pour l'exécution d'ordres.
Délègue la logique vers signals.logic.execution.*
- API moderne : execute_and_track_order(...)
- API legacy  : execute_signal(...)
"""

from typing import Optional, Dict, Any

from signals.metrics.perf_tracker import PerformanceTracker
from signals.logic.execution import (
    build_order_payload,             # utile si du code l’utilisait déjà
    execute_and_track_order as _exec_and_track,
    execute_signal_legacy as _exec_legacy,
)

__all__ = [
    "build_order_payload",
    "execute_and_track_order",
    "execute_signal",
]


def execute_and_track_order(
    *,
    symbol: str,
    side: str,                  # "BUY" | "SELL"
    qty: float,
    limit_price: Optional[float],
    market_price: Optional[float],
    tracker: Optional[PerformanceTracker] = None,
) -> Dict[str, Any]:
    """
    Nouvelle API : en prod appelle l'API et met à jour le tracker à la confirmation (ou fallback).
    En dry-run, simule un fill et met à jour le tracker.
    """
    return _exec_and_track(
        symbol=symbol,
        side=side,
        qty=qty,
        limit_price=limit_price,
        market_price=market_price,
        tracker=tracker,
    )


def execute_signal(
    signal: Dict[str, Any],
    *,
    tracker: Optional[PerformanceTracker] = None,
    market_price: Optional[float] = None,
    limit_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    API legacy : conserve la signature historique.
    - En dry-run : log virtuel + MAJ tracker (si fourni).
    - En prod    : délègue à execute_and_track_order().
    """
    return _exec_legacy(
        signal,
        tracker=tracker,
        market_price=market_price,
        limit_price=limit_price,
    )
