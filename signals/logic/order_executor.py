# signals/logic/order_executor.py

from typing import Optional, Dict, Any
from signals.logic.execution import runner as rn


def execute_signal(signal: Dict[str, Any], *, tracker=None, market_price: Optional[float] = None, limit_price: Optional[float] = None) -> Dict[str, Any]:
    return rn.execute_signal_legacy(signal, tracker=tracker, market_price=market_price, limit_price=limit_price)


def execute_and_track_order(
    *,
    symbol: str,
    side: str,
    qty: float,
    limit_price: Optional[float],
    market_price: Optional[float],
    tracker,
) -> Dict[str, Any]:
    return rn.execute_and_track_order(
        symbol=symbol,
        side=side,
        qty=qty,
        limit_price=limit_price,
        market_price=market_price,
        tracker=tracker,
    )
