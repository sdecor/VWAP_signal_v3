# signals/logic/risk_constraints.py
from __future__ import annotations
from typing import Any, Dict, Optional


def get_drawdown_usd(tracker: Any) -> float:
    """
    Essaie d'extraire la valeur de drawdown courant en USD depuis différents attributs/méthodes possibles.
    Retourne 0.0 par défaut si introuvable (plutôt permissif — les tests pourront injecter un tracker ad hoc).
    """
    candidates = (
        "get_current_drawdown_usd",
        "current_drawdown_usd",
        "get_drawdown",
        "current_drawdown",
        "drawdown",
        "dd",
        "dd_usd",
    )
    for name in candidates:
        if hasattr(tracker, name):
            obj = getattr(tracker, name)
            val = obj() if callable(obj) else obj
            try:
                return float(val)
            except Exception:
                continue
    return 0.0


def get_dd_limit_from_optimizer(
    *,
    cfg_now: Dict[str, Any],
    optimizer_root: Optional[Dict[str, Any]],
    app_cfg: Optional[Dict[str, Any]],
) -> Optional[float]:
    """
    Priorité des sources de limite DD (USD) :
      1) cfg_now['CONSTRAINTS']['MAX_EQUITY_DD_USD_LIMIT']
      2) optimizer_root['GLOBAL_CONSTANTS']['MAX_EQUITY_DD_USD_LIMIT']
      3) app_cfg['general']['MAX_EQUITY_DD_USD']
      4) None si rien trouvé
    """
    # 1) Par schedule
    cons = (cfg_now.get("CONSTRAINTS") or {})
    if "MAX_EQUITY_DD_USD_LIMIT" in cons:
        try:
            return float(cons["MAX_EQUITY_DD_USD_LIMIT"])
        except Exception:
            pass

    # 2) Global optimizer
    if optimizer_root:
        glob = (optimizer_root.get("GLOBAL_CONSTANTS") or {})
        if "MAX_EQUITY_DD_USD_LIMIT" in glob:
            try:
                return float(glob["MAX_EQUITY_DD_USD_LIMIT"])
            except Exception:
                pass

    # 3) Fallback config.yaml
    if app_cfg:
        gen = (app_cfg.get("general") or {})
        if "MAX_EQUITY_DD_USD" in gen:
            try:
                return float(gen["MAX_EQUITY_DD_USD"])
            except Exception:
                pass

    # 4) No guard
    return None


def allow_new_entry(
    *,
    tracker: Any,
    dd_limit_usd: Optional[float],
) -> bool:
    """
    Renvoie False si le drawdown courant >= limite, True sinon (ou si pas de limite définie).
    """
    if dd_limit_usd is None:
        return True
    dd = get_drawdown_usd(tracker)
    return dd < float(dd_limit_usd)
