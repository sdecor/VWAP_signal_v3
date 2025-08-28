# signals/logic/optimizer_exits.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ExitDecision:
    should_exit: bool
    reason: Optional[str] = None          # "sl_atr" | "fixed_ticks" | "cross" | "vwap_level"
    price: Optional[float] = None         # prix d'exit (ex: TP/SL hit, ou close selon règle)
    extra: Optional[Dict[str, Any]] = None


# ---------------------------
# Fixed ticks (TP)
# ---------------------------

def compute_tp_price_fixed_ticks(entry_price: float, side: str, ticks: float, tick_size: float) -> float:
    direction = 1.0 if side.upper() == "BUY" else -1.0
    return entry_price + direction * (ticks * tick_size)


def check_exit_fixed_ticks(
    *,
    side: str,
    entry_price: float,
    high: float,
    low: float,
    ticks: float,
    tick_size: float,
) -> ExitDecision:
    target = compute_tp_price_fixed_ticks(entry_price, side, ticks, tick_size)
    s = side.upper()
    if s == "BUY" and float(high) >= target:
        return ExitDecision(True, reason="fixed_ticks", price=target, extra={"target": target})
    if s == "SELL" and float(low) <= target:
        return ExitDecision(True, reason="fixed_ticks", price=target, extra={"target": target})
    return ExitDecision(False)


# ---------------------------
# Cross VWAP
# ---------------------------

def check_exit_cross_vwap(
    *,
    side: str,
    prev_close: Optional[float],
    prev_vwap: Optional[float],
    close: float,
    vwap: Optional[float],
) -> ExitDecision:
    if prev_close is None or prev_vwap is None or vwap is None:
        return ExitDecision(False)

    s = side.upper()
    pc = float(prev_close)
    pv = float(prev_vwap)
    c = float(close)
    v = float(vwap)

    if s == "BUY" and pc < pv and c >= v:
        return ExitDecision(True, reason="cross", price=c)
    if s == "SELL" and pc > pv and c <= v:
        return ExitDecision(True, reason="cross", price=c)
    return ExitDecision(False)


# ---------------------------
# VWAP level (atteinte simple)
# ---------------------------

def check_exit_vwap_level(
    *,
    side: str,
    close: float,
    vwap: Optional[float],
) -> ExitDecision:
    if vwap is None:
        return ExitDecision(False)

    s = side.upper()
    c = float(close)
    v = float(vwap)

    if s == "BUY" and c >= v:
        return ExitDecision(True, reason="vwap_level", price=c)
    if s == "SELL" and c <= v:
        return ExitDecision(True, reason="vwap_level", price=c)
    return ExitDecision(False)


# ---------------------------
# Stop-Loss ATR
# ---------------------------

def compute_sl_price_atr(entry_price: float, side: str, atr_value: float, atr_multiplier: float) -> float:
    """
    SL = entry ∓ (ATR * multiplier)
      BUY  -> entry - ATR*mult
      SELL -> entry + ATR*mult
    """
    if side.upper() == "BUY":
        return float(entry_price) - float(atr_value) * float(atr_multiplier)
    else:
        return float(entry_price) + float(atr_value) * float(atr_multiplier)


def check_exit_sl_atr(
    *,
    side: str,
    entry_price: float,
    high: float,
    low: float,
    atr_value: Optional[float],
    atr_multiplier: float,
) -> ExitDecision:
    """
    SL intrabar : si la bougie touche le SL, sortie @ SL (price=sl_price).
      BUY  : low  <= SL_buy
      SELL : high >= SL_sell
    """
    if atr_value is None:
        return ExitDecision(False)

    sl_price = compute_sl_price_atr(entry_price, side, float(atr_value), float(atr_multiplier))
    s = side.upper()
    if s == "BUY" and float(low) <= sl_price:
        return ExitDecision(True, reason="sl_atr", price=sl_price, extra={"sl": sl_price})
    if s == "SELL" and float(high) >= sl_price:
        return ExitDecision(True, reason="sl_atr", price=sl_price, extra={"sl": sl_price})
    return ExitDecision(False)


# ---------------------------
# Orchestrateur d'exit (ordre de priorité)
# ---------------------------

def decide_exit(
    *,
    side: str,
    entry_price: float,
    candle: Dict[str, Any],       # {'time','open','high','low','close','vwap'?, 'atr'?}
    cfg_now: Dict[str, Any],      # config horaire optimizer (VWAP_CONFIG, RISK_MANAGEMENT)
    tick_size: float,
    prev_close: Optional[float] = None,
    prev_vwap: Optional[float] = None,
) -> ExitDecision:
    """
    Priorité (convention robuste):
      1) SL ATR   (Dynamic_SL_Fixed_Lots)
      2) TP fixed_ticks
      3) exit cross VWAP
      4) TP vwap_level

    Notes:
      - L'optimizer exprime SL via RISK_MANAGEMENT(METHOD=ATR, ATR_PERIOD, ATR_MULTIPLIER)
      - L'ATR doit être fourni par la pipeline de features (ex: candle['atr']).
    """
    rm = (cfg_now.get("RISK_MANAGEMENT") or {})
    vwap_cfg = (cfg_now.get("VWAP_CONFIG") or {})

    tp_type = str(rm.get("TP_TYPE") or vwap_cfg.get("tp_type") or "").strip().lower()
    exit_type = str(vwap_cfg.get("exit_type") or "").strip().lower()

    high = float(candle.get("high"))
    low = float(candle.get("low"))
    close = float(candle.get("close"))
    vwap = candle.get("vwap")
    atr_value = candle.get("atr")  # doit avoir été calculé dans les features

    # 1) SL ATR
    if str(rm.get("METHOD", "")).upper() == "ATR":
        atr_mult = float(rm.get("ATR_MULTIPLIER", cfg_now.get("ATR_MULTIPLIER", 1.0)))
        sl = check_exit_sl_atr(
            side=side,
            entry_price=entry_price,
            high=high,
            low=low,
            atr_value=(None if atr_value is None else float(atr_value)),
            atr_multiplier=atr_mult,
        )
        if sl.should_exit:
            return sl

    # 2) TP fixed_ticks
    if tp_type == "fixed_ticks":
        ticks = float(rm.get("TP_TICKS", 0))
        res = check_exit_fixed_ticks(
            side=side,
            entry_price=entry_price,
            high=high,
            low=low,
            ticks=ticks,
            tick_size=tick_size,
        )
        if res.should_exit:
            return res

    # 3) exit cross VWAP
    if exit_type == "cross":
        res = check_exit_cross_vwap(
            side=side,
            prev_close=prev_close,
            prev_vwap=prev_vwap,
            close=close,
            vwap=vwap,
        )
        if res.should_exit:
            return res

    # 4) TP vwap_level
    if tp_type == "vwap_level":
        res = check_exit_vwap_level(
            side=side,
            close=close,
            vwap=vwap,
        )
        if res.should_exit:
            return res

    return ExitDecision(False)
