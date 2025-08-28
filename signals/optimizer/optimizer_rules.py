# signals/optimizer/optimizer_rules.py

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ScheduleConfig:
    name: str
    hour_start: int
    hour_end: int
    ml_threshold: float
    fixed_lots: float
    tp_type: str
    tp_ticks: float
    atr_period: int
    atr_multiplier: float
    vwap_period: str
    entry_threshold: float
    exit_type: str


def load_optimizer_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[OptimizerConfig] Introuvable: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_hour_in_range(hour: int, start: int, end: int) -> bool:
    """
    Gère aussi le cas fenêtré sur minuit. Ex: start=22, end=2 -> heures 22,23,0,1,2
    """
    if start <= end:
        return start <= hour <= end
    return hour >= start or hour <= end


def select_active_schedule(optimizer_cfg: Dict[str, Any], hour_utc: int) -> Optional[ScheduleConfig]:
    """
    Sélectionne une schedule active à l'heure donnée (UTC).
    Retourne la première qui matche (tu peux affiner avec un score si besoin).
    """
    by_schedule = optimizer_cfg.get("CONFIGURATIONS_BY_SCHEDULE", {})
    for name, sc in by_schedule.items():
        start = int(sc.get("HOUR_RANGE_START", 0))
        end = int(sc.get("HOUR_RANGE_END", 23))
        if _is_hour_in_range(hour_utc, start, end):
            risk = sc.get("RISK_MANAGEMENT", {})
            vwap_cfg = sc.get("VWAP_CONFIG", {})
            return ScheduleConfig(
                name=name,
                hour_start=start,
                hour_end=end,
                ml_threshold=float(sc.get("ML_THRESHOLD", 0.5)),
                fixed_lots=float(risk.get("FIXED_LOTS", 1.0)),
                tp_type=str(risk.get("TP_TYPE", "vwap_level")),
                tp_ticks=float(risk.get("TP_TICKS", 4)),
                atr_period=int(risk.get("ATR_PERIOD", 14)),
                atr_multiplier=float(risk.get("ATR_MULTIPLIER", 1.5)),
                vwap_period=str(vwap_cfg.get("vwap_period", "session_RTH")),
                entry_threshold=float(vwap_cfg.get("entry_threshold", 1.0)),
                exit_type=str(vwap_cfg.get("exit_type", "cross")),
            )
    return None


def validate_and_enrich_decision_for_schedule(
    *,
    decision: Dict[str, Any],
    schedule: ScheduleConfig,
    price: Optional[float],
    vwap: Optional[float],
    general_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Applique les règles de la schedule à un signal.
    Renvoie une nouvelle décision enrichie + flag 'executed' pour dry-run.
    """
    # Copie non destructive
    out = dict(decision or {})
    action = (out.get("action") or "FLAT").upper()

    # 1) Probabilité ML
    prob = out.get("prob")
    if prob is None or float(prob) < schedule.ml_threshold:
        out["executed"] = False
        out["reject_reason"] = f"prob<{schedule.ml_threshold}"
        out["schedule"] = schedule.name
        return out

    # 2) Contrainte VWAP / entry_threshold (si vwap fourni)
    if price is not None and vwap is not None:
        spread = abs(price - vwap)
        # NB: ici "entry_threshold" est une abstraction ; dans ton moteur réel,
        # c'est souvent "distance normalisée au VWAP". Ajuste si nécessaire :
        # ex: normalized_dist_to_vwap >= entry_threshold
        out["spread_to_vwap"] = price - vwap
        # On ne refuse pas automatiquement ici sans connaître la normalization exacte.
        # Si tu veux durcir : if normalized < schedule.entry_threshold: reject.

    # 3) Règlages RISK + tailles
    out["qty"] = out.get("qty") or schedule.fixed_lots
    out["risk"] = {
        "TYPE": "Dynamic_SL_Fixed_Lots",
        "METHOD": "ATR",
        "ATR_PERIOD": schedule.atr_period,
        "ATR_MULTIPLIER": schedule.atr_multiplier,
        "TP_TYPE": schedule.tp_type,
        "TP_TICKS": schedule.tp_ticks,
    }

    # 4) Specs futures (pour logs downstream)
    out["futures_spec"] = {
        "TICK_SIZE": float(general_cfg.get("TICK_SIZE", 0.03125)),
        "TICK_VALUE": float(general_cfg.get("TICK_VALUE", 31.25)),
    }

    # 5) Marquage schedule
    out["schedule"] = schedule.name
    out["vwap_config"] = {
        "vwap_period": schedule.vwap_period,
        "entry_threshold": schedule.entry_threshold,
        "exit_type": schedule.exit_type,
    }

    # 6) Si on est ici, on valide pour exécution (en dry-run)
    out["executed"] = action in ("BUY", "SELL")
    return out
