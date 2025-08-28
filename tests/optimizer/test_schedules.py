# tests/optimizer/test_schedules.py
from datetime import datetime, timezone

import signals.logic.optimizer_parity as parity
import signals.logic.decider as decider


def test_is_in_schedule_simple_range():
    cfg = {"HOUR_RANGE_START": 9, "HOUR_RANGE_END": 17}
    assert parity.is_in_schedule(9, cfg) is True       # début inclusif
    assert parity.is_in_schedule(16, cfg) is True
    assert parity.is_in_schedule(17, cfg) is False     # fin exclusive
    assert parity.is_in_schedule(8, cfg) is False


def test_is_in_schedule_wrap_midnight():
    cfg = {"HOUR_RANGE_START": 22, "HOUR_RANGE_END": 2}
    # actif 22,23,0,1
    for h in (22, 23, 0, 1):
        assert parity.is_in_schedule(h, cfg) is True
    for h in (2, 3, 21):
        assert parity.is_in_schedule(h, cfg) is False


def test_get_active_schedule_first_match_wins():
    schedules = {
        "A": {"HOUR_RANGE_START": 0, "HOUR_RANGE_END": 24},   # recouvre tout
        "B": {"HOUR_RANGE_START": 10, "HOUR_RANGE_END": 12},  # plus précis
    }
    # dict conserve l'ordre d'insertion → "A" est renvoyé
    out = parity.get_active_schedule(hour_utc=11, optimizer_cfg_by_schedule=schedules)
    assert out is not None and out[0] == "A"


def test_get_active_schedule_wrap_and_normal():
    schedules = {
        "NIGHT": {"HOUR_RANGE_START": 22, "HOUR_RANGE_END": 2},
        "DAY": {"HOUR_RANGE_START": 8, "HOUR_RANGE_END": 16},
    }
    s = parity.get_active_schedule(hour_utc=23, optimizer_cfg_by_schedule=schedules)
    assert s and s[0] == "NIGHT"
    s = parity.get_active_schedule(hour_utc=9, optimizer_cfg_by_schedule=schedules)
    assert s and s[0] == "DAY"
    s = parity.get_active_schedule(hour_utc=5, optimizer_cfg_by_schedule=schedules)
    assert s is None


def test_process_signal_respects_schedule(monkeypatch):
    """
    process_signal() doit renvoyer None hors plage et un signal dans la plage.
    """
    fake_cfg = {"config_horaire": {"path": "dummy.json"}}
    monkeypatch.setattr(decider.cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    opt_cfg = {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "NIGHT": {"HOUR_RANGE_START": 22, "HOUR_RANGE_END": 2, "ML_THRESHOLD": 0.5, "VWAP_CONFIG": {"entry_threshold": 1.0}},
        }
    }
    monkeypatch.setattr(decider.rules, "load_optimizer_config", lambda p: opt_cfg)

    # 05:00Z → hors plage (NIGHT est 22->2)
    now_off = datetime(2025, 7, 14, 5, 0, tzinfo=timezone.utc)
    out_off = decider.process_signal(
        candle={"time": now_off.isoformat(), "close": 115.0},
        features={"normalized_dist_to_vwap": 2.0},
        prob=0.9,
        now=now_off,
        tracker=None,
    )
    assert out_off is None

    # 23:00Z → dans la plage
    now_on = datetime(2025, 7, 14, 23, 0, tzinfo=timezone.utc)
    out_on = decider.process_signal(
        candle={"time": now_on.isoformat(), "close": 115.0},
        features={"normalized_dist_to_vwap": 2.0},
        prob=0.9,
        now=now_on,
        tracker=None,
    )
    assert out_on is not None
    assert out_on["session"] == "NIGHT"
