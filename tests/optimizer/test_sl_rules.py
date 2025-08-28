# tests/optimizer/test_sl_rules.py
from signals.logic.optimizer_exits import (
    compute_sl_price_atr,
    check_exit_sl_atr,
    decide_exit,
)


def test_compute_sl_price_buy_and_sell():
    entry = 100.0
    atr = 1.2
    mult = 1.5
    sl_buy = compute_sl_price_atr(entry, "BUY", atr, mult)   # 100 - 1.2*1.5 = 98.2
    sl_sell = compute_sl_price_atr(entry, "SELL", atr, mult) # 100 + 1.2*1.5 = 101.8
    assert round(sl_buy, 4) == 98.2
    assert round(sl_sell, 4) == 101.8


def test_check_exit_sl_atr_buy_hits_low():
    entry = 100.0
    atr = 1.0
    mult = 2.0
    sl = compute_sl_price_atr(entry, "BUY", atr, mult)  # 98.0
    res = check_exit_sl_atr(
        side="BUY",
        entry_price=entry,
        high=101.0,
        low=97.9,   # touche SL
        atr_value=atr,
        atr_multiplier=mult,
    )
    assert res.should_exit is True
    assert res.reason == "sl_atr"
    assert abs(res.price - sl) < 1e-9


def test_check_exit_sl_atr_sell_hits_high():
    entry = 100.0
    atr = 0.8
    mult = 1.5
    sl = compute_sl_price_atr(entry, "SELL", atr, mult)  # 101.2
    res = check_exit_sl_atr(
        side="SELL",
        entry_price=entry,
        high=101.3,  # touche SL
        low=98.0,
        atr_value=atr,
        atr_multiplier=mult,
    )
    assert res.should_exit is True
    assert res.reason == "sl_atr"
    assert abs(res.price - sl) < 1e-9


def test_decide_exit_priority_sl_over_tp_and_cross_and_vwap_level():
    """
    SL ATR prioritaire sur TP fixed_ticks, puis cross, puis vwap_level.
    Bougie simulation où tout serait vrai, on attend 'sl_atr'.
    """
    cfg_now = {
        "VWAP_CONFIG": {"exit_type": "cross", "tp_type": "fixed_ticks"},
        "RISK_MANAGEMENT": {"TYPE": "Dynamic_SL_Fixed_Lots", "METHOD": "ATR", "ATR_MULTIPLIER": 1.0, "TP_TYPE": "fixed_ticks", "TP_TICKS": 2},
    }
    entry = 100.0
    tick_size = 0.5
    # Candle qui:
    # - touche SL pour BUY (atr=1.0 -> SL=99.0 -> low=98.9)
    # - touche aussi TP fixed_ticks (target=101.0 -> high=101.1)
    # - et cross + vwap_level valides
    candle = {
        "open": 100.0,
        "high": 101.1,
        "low": 98.9,
        "close": 100.2,
        "vwap": 100.1,
        "atr": 1.0,
    }

    res = decide_exit(
        side="BUY",
        entry_price=entry,
        candle=candle,
        cfg_now=cfg_now,
        tick_size=tick_size,
        prev_close=99.8,
        prev_vwap=100.0,
    )
    assert res.should_exit is True
    assert res.reason == "sl_atr"
