# tests/optimizer/test_exit_rules.py
from signals.logic.optimizer_exits import (
    compute_tp_price_fixed_ticks,
    check_exit_fixed_ticks,
    check_exit_cross_vwap,
    check_exit_vwap_level,
    decide_exit,
)


def test_fixed_ticks_buy_reaches_target():
    tick_size = 0.5
    entry = 100.0
    ticks = 4  # TP = 102.0
    target = compute_tp_price_fixed_ticks(entry, "BUY", ticks, tick_size)
    assert target == 102.0

    res = check_exit_fixed_ticks(
        side="BUY",
        entry_price=entry,
        high=102.1,   # atteint
        low=99.0,
        ticks=ticks,
        tick_size=tick_size,
    )
    assert res.should_exit is True
    assert res.reason == "fixed_ticks"
    assert res.price == target


def test_fixed_ticks_sell_reaches_target():
    tick_size = 0.5
    entry = 100.0
    ticks = 2  # TP = 99.0
    target = compute_tp_price_fixed_ticks(entry, "SELL", ticks, tick_size)
    assert target == 99.0

    res = check_exit_fixed_ticks(
        side="SELL",
        entry_price=entry,
        high=101.0,
        low=98.9,   # atteint
        ticks=ticks,
        tick_size=tick_size,
    )
    assert res.should_exit is True
    assert res.reason == "fixed_ticks"
    assert res.price == target


def test_cross_vwap_buy():
    # BUY: prev_close < prev_vwap ET close >= vwap
    res = check_exit_cross_vwap(
        side="BUY",
        prev_close=99.8,
        prev_vwap=100.0,
        close=100.2,
        vwap=100.1,
    )
    assert res.should_exit is True
    assert res.reason == "cross"


def test_cross_vwap_sell():
    # SELL: prev_close > prev_vwap ET close <= vwap
    res = check_exit_cross_vwap(
        side="SELL",
        prev_close=100.4,
        prev_vwap=100.0,
        close=99.9,
        vwap=100.05,
    )
    assert res.should_exit is True
    assert res.reason == "cross"


def test_vwap_level_buy():
    res = check_exit_vwap_level(
        side="BUY",
        close=100.2,
        vwap=100.1,
    )
    assert res.should_exit is True
    assert res.reason == "vwap_level"


def test_decide_exit_priority_fixed_over_cross():
    """
    Si fixed_ticks et cross sont tous les deux vrais sur la même bougie,
    on priorise le TP fixed_ticks (comme dans beaucoup de moteurs).
    """
    cfg_now = {
        "VWAP_CONFIG": {"exit_type": "cross", "tp_type": "fixed_ticks"},
        "RISK_MANAGEMENT": {"TP_TYPE": "fixed_ticks", "TP_TICKS": 2},
    }
    tick_size = 0.5
    entry = 100.0
    candle = {
        "high": 101.1,  # TP hit (target=101.0)
        "low": 99.0,
        "close": 100.2,
        "vwap": 100.1,
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
    assert res.reason == "fixed_ticks"
    assert res.price == 101.0
