# signals/logic/optimizer_parity.py
"""
Parité d'entrée avec l'optimizer (Mean Reversion + ML).
Fonctions pures, testables et réutilisables.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Tuple, List


def is_in_schedule(hour_utc: int, cfg_now: Dict[str, Any]) -> bool:
    """
    Vérifie si hour_utc appartient à la plage [start, end) de la config (UTC).
    Supporte les plages qui traversent minuit (ex: 22 -> 2).
    Interprétations:
      - début inclusif, fin exclusive,
      - si la durée modulo 24 est 0 (ex: 0->24), alors c'est 'toute la journée'.
    """
    start_raw = int(cfg_now.get("HOUR_RANGE_START", 0))
    end_raw = int(cfg_now.get("HOUR_RANGE_END", 24))

    # normalise dans [0, 23]
    start = start_raw % 24
    end = end_raw % 24
    hour = int(hour_utc) % 24

    # span modulo 24 : 0 = "full day"
    span = (end_raw - start_raw) % 24
    if span == 0:
        return True  # toute la journée active

    if start < end:
        # ex: 9 -> 17
        return start <= hour < end
    else:
        # wrap minuit: ex: 22 -> 2  (actif si [22,24) ou [0,2))
        return (hour >= start) or (hour < end)


def get_active_schedule(
    *,
    hour_utc: int,
    optimizer_cfg_by_schedule: Dict[str, Dict[str, Any]],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Renvoie (label, config) du premier schedule actif correspondant à hour_utc.
    Détermination *strictement* basée sur l'ordre du dict (insertion du JSON).
    Aucune logique de 'meilleur fit' n'est appliquée.
    """
    # ⚠️ Ne surtout pas trier ni re-construire le dict ici
    for label, scfg in optimizer_cfg_by_schedule.items():
        if is_in_schedule(hour_utc, scfg):
            return label, scfg
    return None


def decide_entry_from_features(
    *,
    features: Dict[str, float],
    prob: float,
    cfg_now: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Reproduit la décision d'entrée de l'optimizer:

      Conditions:
      - prob >= ML_THRESHOLD
      - |normalized_dist_to_vwap| >= VWAP_CONFIG.entry_threshold

      Direction (Mean Reversion contrarien):
      - dist > 0 (prix au-dessus du VWAP)  -> SELL
      - dist < 0 (prix en dessous du VWAP) -> BUY

    Retour: dict signal minimal {action, prob, features{normalized_dist_to_vwap}}
            ou None si pas de signal.
    """
    ml_th = float(cfg_now.get("ML_THRESHOLD", 0.5))
    if prob < ml_th:
        return None

    vwap_cfg = (cfg_now.get("VWAP_CONFIG") or {})
    entry_th = float(vwap_cfg.get("entry_threshold", 0.0))

    dist = float(features.get("normalized_dist_to_vwap", 0.0))
    if abs(dist) < entry_th:
        return None

    action = "SELL" if dist > 0 else "BUY"
    return {
        "action": action,
        "prob": float(prob),
        "features": {"normalized_dist_to_vwap": dist},
    }


def qty_from_risk_management(cfg_now: Dict[str, Any], default_lots: float = 1.0) -> float:
    """
    Extrait la quantité FIXED_LOTS depuis la section RISK_MANAGEMENT.
    """
    rm = (cfg_now.get("RISK_MANAGEMENT") or {})
    try:
        return float(rm.get("FIXED_LOTS", default_lots))
    except Exception:
        return float(default_lots)


def enrich_signal_with_session_and_qty(
    signal: Dict[str, Any],
    *,
    session_label: Optional[str],
    cfg_now: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ajoute 'session' et 'qty' (depuis FIXED_LOTS) au signal.
    """
    out = dict(signal)
    if session_label:
        out["session"] = session_label
    out.setdefault("qty", qty_from_risk_management(cfg_now))
    return out
