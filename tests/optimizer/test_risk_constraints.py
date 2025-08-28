# tests/optimizer/test_risk_constraints.py
from datetime import datetime, timezone

import pytest

from signals.logic.risk_constraints import (
    get_drawdown_usd,
    get_dd_limit_from_optimizer,
    allow_new_entry,
)
import signals.logic.decider as decider


class DummyTracker:
    def __init__(self, dd):
        self.dd = dd  # drawdown en USD
    def get_current_drawdown_usd(self):
        return self.dd


def test_get_drawdown_usd_variants():
    class T1:
        def get_current_drawdown_usd(self): return 123.4
    class T2:
        current_drawdown_usd = 55.5
    class T3:
        drawdown = 9

    assert get_drawdown_usd(T1()) == 123.4
    assert get_drawdown_usd(T2()) == 55.5
    assert get_drawdown_usd(T3()) == 9.0


def test_get_dd_limit_precedence():
    # schedule-level > global > app_cfg
    cfg_now = {"CONSTRAINTS": {"MAX_EQUITY_DD_USD_LIMIT": 500.0}}
    optimizer_root = {"GLOBAL_CONSTANTS": {"MAX_EQUITY_DD_USD_LIMIT": 800.0}}
    app_cfg = {"general": {"MAX_EQUITY_DD_USD": 900.0}}
    assert get_dd_limit_from_optimizer(cfg_now=cfg_now, optimizer_root=optimizer_root, app_cfg=app_cfg) == 500.0

    # pas de schedule-level -> global
    cfg_now = {}
    assert get_dd_limit_from_optimizer(cfg_now=cfg_now, optimizer_root=optimizer_root, app_cfg=app_cfg) == 800.0

    # pas de schedule/global -> app_cfg
    assert get_dd_limit_from_optimizer(cfg_now=cfg_now, optimizer_root=None, app_cfg=app_cfg) == 900.0

    # rien -> None
    assert get_dd_limit_from_optimizer(cfg_now=cfg_now, optimizer_root=None, app_cfg=None) is None


def test_allow_new_entry_blocks_when_limit_hit():
    tracker = DummyTracker(dd=600.0)
    assert allow_new_entry(tracker=tracker, dd_limit_usd=800.0) is True
    assert allow_new_entry(tracker=tracker, dd_limit_usd=500.0) is False
    assert allow_new_entry(tracker=tracker, dd_limit_usd=None) is True


def test_process_signal_dd_guard_blocks(monkeypatch):
    """
    Vérifie que process_signal() bloque l'entrée si drawdown >= limite.
    """
    fake_cfg = {"config_horaire": {"path": "dummy.json"}}
    monkeypatch.setattr(decider.cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    opt_cfg = {
        "GLOBAL_CONSTANTS": {"MAX_EQUITY_DD_USD_LIMIT": 800.0},
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "HOUR_RANGE_START": 0, "HOUR_RANGE_END": 2,
                "ML_THRESHOLD": 0.6,
                "VWAP_CONFIG": {"entry_threshold": 1.0},
            }
        }
    }
    monkeypatch.setattr(decider.rules, "load_optimizer_config", lambda p: opt_cfg)

    # heure dans la plage (0-2)
    now = datetime(2025, 7, 14, 0, 30, tzinfo=timezone.utc)
    features = {"normalized_dist_to_vwap": 2.0}

    # drawdown sous la limite -> autorisé
    tracker_ok = DummyTracker(dd=100.0)
    out = decider.process_signal(
        candle={"time": now.isoformat(), "close": 115.0},
        features=features,
        prob=0.95,
        now=now,
        tracker=tracker_ok,
    )
    assert out is not None and out["action"] in ("BUY", "SELL")

    # drawdown au-dessus de la limite -> bloqué
    tracker_ko = DummyTracker(dd=900.0)
    out2 = decider.process_signal(
        candle={"time": now.isoformat(), "close": 115.0},
        features=features,
        prob=0.95,
        now=now,
        tracker=tracker_ko,
    )
    assert out2 is None


def test_process_signal_dd_guard_schedule_overrides_global(monkeypatch):
    """
    Vérifie la priorité: CONSTRAINTS du schedule override la limite globale.
    """
    fake_cfg = {"config_horaire": {"path": "dummy.json"}}
    monkeypatch.setattr(decider.cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    opt_cfg = {
        "GLOBAL_CONSTANTS": {"MAX_EQUITY_DD_USD_LIMIT": 800.0},
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "HOUR_RANGE_START": 0, "HOUR_RANGE_END": 2,
                "ML_THRESHOLD": 0.6,
                "VWAP_CONFIG": {"entry_threshold": 1.0},
                "CONSTRAINTS": {"MAX_EQUITY_DD_USD_LIMIT": 500.0},
            }
        }
    }
    monkeypatch.setattr(decider.rules, "load_optimizer_config", lambda p: opt_cfg)

    now = datetime(2025, 7, 14, 0, 30, tzinfo=timezone.utc)
    features = {"normalized_dist_to_vwap": 2.0}

    # dd=600 -> >500 (schedule) mais <800 (global) => doit BLOQUER (schedule prioritaire)
    tracker = DummyTracker(dd=600.0)
    out = decider.process_signal(
        candle={"time": now.isoformat(), "close": 115.0},
        features=features,
        prob=0.95,
        now=now,
        tracker=tracker,
    )
    assert out is None
