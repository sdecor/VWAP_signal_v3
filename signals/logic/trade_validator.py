# signals/logic/trade_validator.py

from __future__ import annotations
import os
import json
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple

from signals.utils.config_reader import load_config
from signals.loaders.config_loader import load_json_config


@dataclass
class TimeWindow:
    start: time
    end: time
    days: Optional[List[int]] = None  # 0=Mon .. 6=Sun


def _parse_time(hhmm: str) -> time:
    hh, mm = hhmm.split(":")
    return time(int(hh), int(mm))


def _extract_windows(optimizer_cfg: Dict[str, Any]) -> List[TimeWindow]:
    """
    Essaie d'extraire des fenêtres horaires depuis différents schémas possibles
    (on ne connaît pas exactement la structure -> parse tolérant).
    Exemples acceptés:
      {"sessions":[{"start":"08:00","end":"17:00","days":[0,1,2,3,4]}]}
      {"time_windows":[{"start":"08:00","end":"17:00"}]}
      {"windows":[...]}
    S'il n'y a rien -> 'always on' (aucune restriction horaire).
    """
    candidates_keys = ["sessions", "time_windows", "windows", "horaire", "hours"]
    blocks = None
    for k in candidates_keys:
        if isinstance(optimizer_cfg.get(k), list):
            blocks = optimizer_cfg[k]
            break

    windows: List[TimeWindow] = []
    if not blocks:
        return windows  # vide = pas de restriction (always on) -> on traitera ça plus bas

    for b in blocks:
        try:
            start = _parse_time(str(b.get("start", "00:00")))
            end = _parse_time(str(b.get("end", "23:59")))
            days = b.get("days")  # ex: [0..4]
            if isinstance(days, list):
                days = [int(x) for x in days]
            else:
                days = None
            windows.append(TimeWindow(start=start, end=end, days=days))
        except Exception:
            # si un bloc est invalide, on l'ignore
            continue
    return windows


def _within_windows(ts: datetime, windows: List[TimeWindow]) -> bool:
    if not windows:
        # pas de fenêtres = toujours permis
        return True
    weekday = ts.weekday()
    t = ts.time()
    for w in windows:
        if w.days is not None and weekday not in w.days:
            continue
        if w.start <= t <= w.end:
            return True
    return False


def _min_prob_from_yaml(cfg: Dict[str, Any]) -> Optional[float]:
    # on lit le min_prob depuis config.yaml: signal_rules[].params.min_prob
    rules = cfg.get("signal_rules", [])
    for r in rules:
        if r.get("rule") == "vwap_threshold":
            params = r.get("params", {})
            if "min_prob" in params:
                try:
                    return float(params["min_prob"])
                except Exception:
                    return None
    return None


def is_signal_tradable(
    *,
    decision: Dict[str, Any],
    ts: datetime,
    symbol: str
) -> Tuple[bool, str]:
    """
    Valide un signal en utilisant:
      - min_prob (config.yaml)
      - fenêtres horaires (config optimizer)
    Renvoie (ok, reason)
    """
    cfg = load_config()
    min_prob = _min_prob_from_yaml(cfg)

    # probabilité ML du signal
    prob = decision.get("prob")
    if min_prob is not None and isinstance(prob, (int, float)):
        if prob < min_prob:
            return False, f"prob<{min_prob}"

    # charge la config optimizer
    opt_path = cfg.get("config_horaire", {}).get("path")
    if not opt_path or not os.path.exists(opt_path):
        # si la config horaire n’est pas dispo, on n’impose pas de contrainte horaire
        return True, "no_optimizer_schedule"

    optimizer_cfg = load_json_config(opt_path)

    # il peut y avoir une structure par symbole ; si oui on essaie d'attraper
    sym_block = None
    if isinstance(optimizer_cfg, dict):
        # quelques heuristiques
        for key in [symbol, "symbol", "UB", "UB1", "UB1!", "CBOT_UB1!"]:
            if key in optimizer_cfg and isinstance(optimizer_cfg[key], dict):
                sym_block = optimizer_cfg[key]
                break
    base = sym_block if sym_block is not None else optimizer_cfg

    windows = _extract_windows(base)
    if not _within_windows(ts, windows):
        return False, "outside_schedule"

    return True, "ok"
