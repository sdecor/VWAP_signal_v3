# tests/features/test_feature_integration_live.py
from datetime import datetime, timezone
import pandas as pd
import pytest

import signals.logic.decider_live as live


def test_live_feature_order_and_decision(monkeypatch):
    # --- Config : model.features = ["b","a"] ; schedule actif 0-2h avec thresholds
    fake_cfg = {
        "model": {"features": ["b", "a"]},
        "config_horaire": {"path": "dummy.json"},
        "general": {"TICK_SIZE": 0.25, "TICK_VALUE": 12.5},
    }
    monkeypatch.setattr(live.cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    fake_opt = {
        "GLOBAL_CONSTANTS": {},
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "HOUR_RANGE_START": 0, "HOUR_RANGE_END": 2,
                "ML_THRESHOLD": 0.6,
                "VWAP_CONFIG": {"entry_threshold": 1.0},
                # Pas de "features" ici → on utilisera model.features ["b","a"]
                "RISK_MANAGEMENT": {"FIXED_LOTS": 2}
            }
        }
    }
    monkeypatch.setattr(live.rules, "load_optimizer_config", lambda p: fake_opt)

    # --- DataFrame enrichi, colonnes dans un ordre arbitraire
    df = pd.DataFrame({
        "a": [1.1, 1.2],
        "normalized_dist_to_vwap": [1.1, 2.2],  # > entry_threshold => OK
        "b": [3.3, 3.4],
        "close": [100.0, 101.0],
        "vwap": [99.0, 100.5],
    })

    # --- On monkeypatch la prédiction pour:
    # 1) vérifier l'ordre des colonnes reçues,
    # 2) renvoyer une proba suffisante (>= ML_THRESHOLD)
    captured = {}
    def fake_predict_proba(model, X):
        captured["cols"] = list(X.columns)
        return 0.95

    monkeypatch.setattr(live, "predict_proba", fake_predict_proba)

    class DummyModel: pass

    now = datetime(2025, 7, 14, 0, 30, tzinfo=timezone.utc)  # ASIAN02 actif
    out = live.process_signal_from_enriched(
        enriched_df=df,
        row_index=len(df) - 1,
        now=now,
        tracker=None,
        model=DummyModel(),
    )

    assert out is not None, "Aucun signal retourné alors que seuils atteints"
    assert out["action"] in ("BUY", "SELL")
    # ordre exact attendu : ['b','a'] (venant de model.features)
    assert captured["cols"] == ["b", "a"]
    # FIXED_LOTS appliqué
    assert out["qty"] == 2
    assert out["session"] == "ASIAN02"
