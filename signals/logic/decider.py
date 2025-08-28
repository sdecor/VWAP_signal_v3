# signals/logic/decider.py

from typing import Any, Dict, Optional

def _from_trade_decider() -> Optional[callable]:
    """
    Lazy import pour éviter d'exécuter l'import de trade_decider au niveau module.
    Retourne decide_trade() si dispo, sinon None.
    """
    try:
        from signals.logic.trade_decider import decide_trade  # type: ignore
        return decide_trade
    except Exception:
        return None


def process_signal(candle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adaptateur qui wrap decide_trade() si disponible.
    Renvoie au format attendu par la live loop :
    { "action": "BUY"/"SELL"/"FLAT", "prob": float|None, "vwap": float|None, "features": dict|None, "session": str|None }
    """
    decide_trade = _from_trade_decider()
    if decide_trade is None:
        # Fallback neutre (permet au test d’injecter un monkeypatch proprement)
        return {"action": "FLAT", "prob": None, "vwap": None, "features": None, "session": None}

    raw = decide_trade()
    if not raw:
        return {"action": "FLAT", "prob": None, "vwap": None, "features": None, "session": None}

    action = (raw.get("signal") or "FLAT").upper()
    prob = raw.get("probability")
    features = raw.get("features")
    vwap = None
    if isinstance(features, dict):
        vwap = features.get("vwap") or features.get("VWAP")
    session = raw.get("config_used")

    return {
        "action": action,
        "prob": prob,
        "vwap": vwap,
        "features": features,
        "session": session,
    }
