# tests/optimizer/test_entry_rules.py
import builtins
from datetime import datetime, timezone

import pytest

from signals.logic.optimizer_parity import decide_entry_from_features, is_in_schedule
import signals.logic.decider as decider


def test_is_in_schedule():
    cfg_now = {"HOUR_RANGE_START": 0, "HOUR_RANGE_END": 2}
    assert is_in_schedule(0, cfg_now)
    assert is_in_schedule(1, cfg_now)
    assert not is_in_schedule(2, cfg_now)
    assert not is_in_schedule(23, cfg_now)


def test_decide_entry_from_features_positive_dist_sell():
    cfg_now = {
        "ML_THRESHOLD": 0.7,
        "VWAP_CONFIG": {"entry_threshold": 1.5},
    }
    features = {"normalized_dist_to_vwap": 2.0}
    sig = decide_entry_from_features(features=features, prob=0.96, cfg_now=cfg_now)
    assert sig is not None
    assert sig["action"] == "SELL"
    assert pytest.approx(sig["prob"], 1e-9) == 0.96


def test_decide_entry_from_features_negative_dist_buy():
    cfg_now = {
        "ML_THRESHOLD": 0.6,
        "VWAP_CONFIG": {"entry_threshold": 1.0},
    }
    features = {"normalized_dist_to_vwap": -1.2}
    sig = decide_entry_from_features(features=features, prob=0.65, cfg_now=cfg_now)
    assert sig is not None
    assert sig["action"] == "BUY"


def test_decide_entry_from_features_prob_too_low_returns_none():
    cfg_now = {
        "ML_THRESHOLD": 0.8,
        "VWAP_CONFIG": {"entry_threshold": 1.0},
    }
    features = {"normalized_dist_to_vwap": 3.0}
    assert decide_entry_from_features(features=features, prob=0.79, cfg_now=cfg_now) is None


def test_decide_entry_from_features_distance_below_threshold_returns_none():
    cfg_now = {
        "ML_THRESHOLD": 0.5,
        "VWAP_CONFIG": {"entry_threshold": 2.0},
    }
    features = {"normalized_dist_to_vwap": 1.99}
    assert decide_entry_from_features(features=features, prob=0.9, cfg_now=cfg_now) is None


def test_process_signal_integration_minimal(monkeypatch):
    """
    Teste process_signal() avec config optimizer factice + heure dans la plage.
    On monkeypatch load_config() et load_optimizer_config() pour éviter le FS.
    """
    fake_cfg = {"config_horaire": {"path": "dummy.json"}}
    monkeypatch.setattr(decider.cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    opt_cfg = {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "HOUR_RANGE_START": 0, "HOUR_RANGE_END": 2,
                "ML_THRESHOLD": 0.7,
                "VWAP_CONFIG": {"entry_threshold": 1.5},
            }
        }
    }
    monkeypatch.setattr(decider.rules, "load_optimizer_config", lambda p: opt_cfg)

    # now = 00:30 UTC (dans la plage 0-2)
    now = datetime(2025, 7, 14, 0, 30, tzinfo=timezone.utc)
    features = {"normalized_dist_to_vwap": 2.1}
    out = decider.process_signal(
        candle={"time": now.isoformat(), "close": 115.0},  # non utilisé ici
        features=features,
        prob=0.95,
        now=now,
    )
    assert out is not None
    assert out["action"] == "SELL"
    assert out["session"] == "ASIAN02"
