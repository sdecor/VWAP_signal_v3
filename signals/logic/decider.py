# signals/logic/decider.py
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

import signals.utils.config_reader as cfg_reader
import signals.optimizer.optimizer_rules as rules
from signals.logic.optimizer_parity import get_active_schedule, decide_entry_from_features
from signals.logic.risk_constraints import get_dd_limit_from_optimizer, allow_new_entry


def process_signal(
    candle: Dict[str, Any],
    *,
    features: Dict[str, float],
    prob: float,
    now: Optional[datetime] = None,
    tracker: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Décision d'entrée strictement conforme à l’optimizer :
      - respect du schedule horaire (UTC)
      - ML_THRESHOLD + VWAP_CONFIG.entry_threshold (Mean Reversion)
      - contrainte de drawdown MAX_EQUITY_DD_USD_LIMIT (par schedule > global > config.yaml)

    Args:
        candle: dict bougie courante (time/ohlc etc.)
        features: dict qui doit contenir au moins 'normalized_dist_to_vwap'
        prob: proba ML
        now: datetime (UTC) injectée pour les tests (sinon datetime.now(UTC))
        tracker: (optionnel) objet fournissant drawdown courant (voir risk_constraints.get_drawdown_usd)

    Returns:
        dict signal {action, prob, features{normalized_dist_to_vwap}, session} ou None si pas d'entrée.
    """
    app_cfg = cfg_reader.load_config()
    opt_path = (app_cfg.get("config_horaire", {}) or {}).get("path")
    optimizer_root = rules.load_optimizer_config(opt_path)
    by_schedule = optimizer_root["CONFIGURATIONS_BY_SCHEDULE"]

    # heure courante UTC (ou injectée)
    now = now or datetime.now(timezone.utc)
    hour = now.hour

    # trouver la config active
    sel = get_active_schedule(hour_utc=hour, optimizer_cfg_by_schedule=by_schedule)
    if not sel:
        return None
    session_label, cfg_now = sel

    # contrainte DD (si tracker fourni)
    if tracker is not None:
        dd_limit = get_dd_limit_from_optimizer(cfg_now=cfg_now, optimizer_root=optimizer_root, app_cfg=app_cfg)
        if not allow_new_entry(tracker=tracker, dd_limit_usd=dd_limit):
            # On bloque l'entrée (parité avec le guardrail optimiseur)
            return None

    sig = decide_entry_from_features(features=features, prob=prob, cfg_now=cfg_now)
    if sig:
        sig["session"] = session_label
    return sig
