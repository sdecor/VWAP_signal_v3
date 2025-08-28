from datetime import datetime, timezone
from typing import Any, Dict, Optional
from signals.optimizer.optimizer_rules import (
    select_active_schedule,
    validate_and_enrich_decision_for_schedule,
)

def to_utc_datetime(ts_str: str) -> datetime:
    if ts_str.endswith("Z"):
        ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str).astimezone(timezone.utc)

def extract_ts_price(candle: Dict[str, Any]) -> tuple[str, Optional[float]]:
    ts_raw = candle.get("time") or candle.get("timestamp")
    if not ts_raw:
        raise ValueError("Bougie sans 'time' ni 'timestamp'")
    price = candle.get("close") if "close" in candle else candle.get("price")
    return ts_raw, price

def validate_with_optimizer(
    decision: Dict[str, Any],
    optimizer_cfg: Dict[str, Any],
    dt_utc: datetime,
    price: Optional[float],
    vwap: Optional[float],
    general_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    sch = select_active_schedule(optimizer_cfg, dt_utc.hour)
    if sch is None:
        decision = dict(decision or {})
        decision["executed"] = False
        decision["reject_reason"] = "out_of_schedule"
        decision["schedule"] = None
        return decision
    return validate_and_enrich_decision_for_schedule(
        decision=decision or {},
        schedule=sch,
        price=price,
        vwap=vwap,
        general_cfg=general_cfg,
    )
