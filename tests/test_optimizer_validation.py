# tests/test_optimizer_validation.py

from datetime import datetime, timezone

import pytest

from signals.optimizer.optimizer_rules import (
    select_active_schedule,
    validate_and_enrich_decision_for_schedule,
)
from signals.runner.live.pipeline import validate_with_optimizer


@pytest.fixture
def optimizer_cfg_basic():
    # Config simple: 00:00–02:00 UTC, ML_THRESHOLD=0.95
    return {
        "GLOBAL_CONSTANTS": {
            "TICK_SIZE": 0.03125,
            "TICK_VALUE": 31.25,
        },
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "VWAP_CONFIG": {
                    "vwap_period": "session_RTH",
                    "entry_threshold": 0.5,
                    "exit_type": "cross",
                    "tp_type": "vwap_level",
                },
                "ML_THRESHOLD": 0.95,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 2,
                "RISK_MANAGEMENT": {
                    "TYPE": "Dynamic_SL_Fixed_Lots",
                    "METHOD": "ATR",
                    "ATR_PERIOD": 14,
                    "ATR_MULTIPLIER": 1.5,
                    "TP_TYPE": "vwap_level",
                    "TP_TICKS": 4,
                    "FIXED_LOTS": 3,
                },
            }
        },
    }


@pytest.fixture
def optimizer_cfg_wrap():
    # Fenêtre traversant minuit: 22:00–02:00
    return {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "NIGHT": {
                "VWAP_CONFIG": {
                    "vwap_period": "session_RTH",
                    "entry_threshold": 1.0,
                    "exit_type": "cross",
                    "tp_type": "vwap_level",
                },
                "ML_THRESHOLD": 0.6,
                "HOUR_RANGE_START": 22,
                "HOUR_RANGE_END": 2,
                "RISK_MANAGEMENT": {
                    "TYPE": "Dynamic_SL_Fixed_Lots",
                    "METHOD": "ATR",
                    "ATR_PERIOD": 14,
                    "ATR_MULTIPLIER": 1.0,
                    "TP_TYPE": "vwap_level",
                    "TP_TICKS": 4,
                    "FIXED_LOTS": 1,
                },
            }
        }
    }


def test_schedule_selection_and_enrichment_pass(optimizer_cfg_basic):
    # Heure 01:00 UTC -> ASIAN02 active, prob=0.96 (>0.95) -> exécuté
    hour = 1
    sch = select_active_schedule(optimizer_cfg_basic, hour)
    assert sch is not None
    assert sch.name == "ASIAN02"
    assert sch.ml_threshold == pytest.approx(0.95)

    # Décision de base
    decision = {"action": "BUY", "prob": 0.96}
    enriched = validate_and_enrich_decision_for_schedule(
        decision=decision,
        schedule=sch,
        price=115.50,
        vwap=115.40,
        general_cfg={"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
    )
    # Validations clés
    assert enriched["executed"] is True
    assert enriched["schedule"] == "ASIAN02"
    assert enriched["qty"] == 3  # FIXED_LOTS
    assert "risk" in enriched and enriched["risk"]["ATR_PERIOD"] == 14
    assert enriched["vwap_config"]["entry_threshold"] == 0.5
    assert enriched["vwap_config"]["exit_type"] == "cross"
    assert enriched["vwap_config"]["vwap_period"] == "session_RTH"


def test_reject_below_ml_threshold(optimizer_cfg_basic):
    # Heure 01:00 UTC, prob trop faible -> rejet
    sch = select_active_schedule(optimizer_cfg_basic, 1)
    decision = {"action": "BUY", "prob": 0.90}
    enriched = validate_and_enrich_decision_for_schedule(
        decision=decision,
        schedule=sch,
        price=115.5,
        vwap=115.4,
        general_cfg={"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
    )
    assert enriched["executed"] is False
    assert enriched["schedule"] == "ASIAN02"
    assert "reject_reason" in enriched
    assert enriched["reject_reason"].startswith("prob<")  # évite les soucis de float exact


def test_out_of_schedule_reject_via_pipeline(optimizer_cfg_basic):
    # Heure 10:00 UTC -> hors plage (0–2) -> out_of_schedule
    dt_utc = datetime(2025, 7, 14, 10, 0, tzinfo=timezone.utc)
    decision = {"action": "SELL", "prob": 0.99, "vwap": 115.4}
    enriched = validate_with_optimizer(
        decision=decision,
        optimizer_cfg=optimizer_cfg_basic,
        dt_utc=dt_utc,
        price=115.5,
        vwap=115.4,
        general_cfg={"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
    )
    assert enriched["executed"] is False
    assert enriched.get("schedule") is None
    assert enriched.get("reject_reason") == "out_of_schedule"


def test_wraparound_schedule_selection(optimizer_cfg_wrap):
    # Plage 22–02 -> 23h et 01h doivent sélectionner "NIGHT"
    sch_23 = select_active_schedule(optimizer_cfg_wrap, 23)
    sch_01 = select_active_schedule(optimizer_cfg_wrap, 1)
    assert sch_23 is not None and sch_23.name == "NIGHT"
    assert sch_01 is not None and sch_01.name == "NIGHT"

def test_fixed_lots_applied_per_schedule():
    # Deux schedules non chevauchantes, FIXED_LOTS différents
    optimizer_cfg = {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "EARLY": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 0.5, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.6,
                "HOUR_RANGE_START": 6,
                "HOUR_RANGE_END": 8,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 2, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
            "LATE": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 0.5, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.6,
                "HOUR_RANGE_START": 20,
                "HOUR_RANGE_END": 22,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 5, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
        }
    }

    # Heure 07:00 → EARLY
    sch_early = select_active_schedule(optimizer_cfg, 7)
    dec = {"action": "BUY", "prob": 0.99}
    enriched_early = validate_and_enrich_decision_for_schedule(
        decision=dec,
        schedule=sch_early,
        price=115.5,
        vwap=115.4,
        general_cfg={"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
    )
    assert enriched_early["executed"] is True
    assert enriched_early["schedule"] == "EARLY"
    assert enriched_early["qty"] == 2  # FIXED_LOTS de EARLY

    # Heure 21:00 → LATE
    sch_late = select_active_schedule(optimizer_cfg, 21)
    enriched_late = validate_and_enrich_decision_for_schedule(
        decision=dec,
        schedule=sch_late,
        price=115.5,
        vwap=115.4,
        general_cfg={"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
    )
    assert enriched_late["executed"] is True
    assert enriched_late["schedule"] == "LATE"
    assert enriched_late["qty"] == 5  # FIXED_LOTS de LATE


def test_first_matching_schedule_wins_by_insertion_order():
    # Deux schedules qui matchent la même plage (0–23), la première doit gagner
    optimizer_cfg_a = {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "FIRST": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 0.5, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.5,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 23,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 1, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
            "SECOND": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 1.0, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.9,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 23,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 9, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
        }
    }
    sch = select_active_schedule(optimizer_cfg_a, 12)
    assert sch is not None
    assert sch.name == "FIRST"  # ordre d'insertion Python 3.7+

    # Inverse l'ordre: SECOND d'abord → doit être choisi
    optimizer_cfg_b = {
        "CONFIGURATIONS_BY_SCHEDULE": {
            "SECOND": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 1.0, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.9,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 23,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 9, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
            "FIRST": {
                "VWAP_CONFIG": {"vwap_period": "session_RTH", "entry_threshold": 0.5, "exit_type": "cross", "tp_type": "vwap_level"},
                "ML_THRESHOLD": 0.5,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 23,
                "RISK_MANAGEMENT": {"FIXED_LOTS": 1, "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.0, "TP_TYPE": "vwap_level", "TP_TICKS": 4},
            },
        }
    }
    sch2 = select_active_schedule(optimizer_cfg_b, 12)
    assert sch2 is not None
    assert sch2.name == "SECOND"
