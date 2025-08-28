# tests/test_dryrun_integration.py

import os
import csv
import json
import pathlib
import builtins
import pytest

# --- Helpers pour importer la bonne run_live_loop quelle que soit ta structure ---

def import_run_live_loop():
    """
    Essaie d'importer la boucle live depuis l'orchestrateur modulaire,
    sinon depuis la version monolithique.
    """
    try:
        from signals.runner.live.orchestrator import run_live_loop
        return run_live_loop, "orchestrator"
    except Exception:
        from signals.runner.live_loop import run_live_loop
        return run_live_loop, "monolith"


def import_feed_reset():
    try:
        from signals.feeds.realtime import reset_feed
        return reset_feed
    except Exception:
        # pas bloquant si pas dispo
        return None


def import_process_signal_module():
    """
    Retourne le module où patcher process_signal, en essayant d'abord l'adaptateur
    puis (fallback) la version monolithique si elle existe.
    """
    try:
        import signals.logic.decider as decider
        return decider
    except Exception:
        # Si tu appelles directement decide_trade() ailleurs, on ne patchera pas
        # et le test devra lire de vraies features -> on évite ça ici.
        raise RuntimeError(
            "Impossible d'importer signals.logic.decider. "
            "Ajoute l'adaptateur process_signal() comme discuté."
        )

# ------------------------------------------------------------------------------------


@pytest.fixture
def tmp_csv_5m(tmp_path):
    """Crée un mini CSV 5m compatible avec le feed realtime."""
    path = tmp_path / "CBOT_UB1!, 5.csv"
    rows = [
        ["time", "open", "high", "low", "close", "volume"],
        ["2025-07-14T00:00:00Z", "115.46875", "115.50000", "115.43750", "115.46875", "1200"],
        ["2025-07-14T00:05:00Z", "115.46875", "115.46875", "115.40625", "115.40625", "2233"],
        ["2025-07-14T00:10:00Z", "115.40625", "115.43750", "115.37500", "115.43750", "1800"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(rows)
    return path


@pytest.fixture
def optimizer_config(tmp_path):
    """Crée un JSON optimizer minimal avec fenêtre horaire couvrant 00:00-02:00 UTC et ML_THRESHOLD=0.5."""
    path = tmp_path / "config_optimale_vwap_mr_ALL.json"
    data = {
        "GLOBAL_CONSTANTS": {
            "TICK_SIZE": 0.03125,
            "TICK_VALUE": 31.25,
            "MAX_EQUITY_DD_USD_LIMIT": 800.0,
            "MODEL_TYPE": "XGBoost",
            "MODEL_FILE": "xgb_model_for_vwap_mr_fixed_lots.json"
        },
        "CONFIGURATIONS_BY_SCHEDULE": {
            "ASIAN02": {
                "VWAP_CONFIG": {
                    "vwap_period": "session_RTH",
                    "entry_threshold": 0.5,
                    "exit_type": "cross",
                    "tp_type": "vwap_level"
                },
                "ML_THRESHOLD": 0.5,
                "HOUR_RANGE_START": 0,
                "HOUR_RANGE_END": 2,
                "RISK_MANAGEMENT": {
                    "TYPE": "Dynamic_SL_Fixed_Lots",
                    "METHOD": "ATR",
                    "ATR_PERIOD": 14,
                    "ATR_MULTIPLIER": 1.5,
                    "TP_TYPE": "vwap_level",
                    "TP_TICKS": 4,
                    "FIXED_LOTS": 1
                }
            }
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_dryrun_pipeline_end_to_end(tmp_path, monkeypatch, tmp_csv_5m, optimizer_config):
    # --- 1) Monkeypatch du config.yaml (tout centralisé) ---
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    signal_csv = str(logs_dir / "signals_log.csv")
    perf_csv = str(logs_dir / "performance_log.csv")

    fake_config = {
        "logging": {
            "enable_api_logging": True,
            "dry_run_mode": True,
            "signal_csv": signal_csv,
            "performance_csv": perf_csv,
        },
        "config_horaire": {
            "path": str(optimizer_config),
        },
        "general": {
            "TICK_SIZE": 0.03125,
            "TICK_VALUE": 31.25,
            "timezone": "UTC",
        },
        "data": {
            "data_path": str(tmp_path),
            "input_5m": tmp_csv_5m.name,
            "tf_files": {},  # pas utilisé ici
        },
        "trading": {
            "symbol": "CBOT_UB1!",
            "order_type": "market",
            "time_in_force": "DAY",
            "dry_run": True,
        },
    }

    # rediriger load_config() pour retourner notre config isolée
    import signals.utils.config_reader as cfg_reader
    monkeypatch.setattr(cfg_reader, "load_config", lambda *a, **k: fake_config)

    # Certains modules importent load_config localement
    # -> on assure la cohérence en patchant là où nécessaire (feeds/logic)
    try:
        import signals.feeds.realtime as feed_rt
        monkeypatch.setattr(feed_rt, "load_config", lambda *a, **k: fake_config)
    except Exception:
        pass

    # --- 2) Réinitialiser le feed si dispo ---
    reset_feed = import_feed_reset()
    if reset_feed:
        reset_feed()

    # --- 3) Monkeypatch process_signal() pour éviter dépendance ML/features ---
    decider = import_process_signal_module()

    def fake_process_signal(candle):
        # Renvoie systématiquement un BUY valide (prob > ML_THRESHOLD=0.5)
        close = float(candle["close"])
        vwap = close  # simplification
        return {
            "action": "BUY",
            "prob": 0.96,
            "vwap": vwap,
            "features": {
                "normalized_dist_to_vwap": 2.1,
                "vwap_slope_5": 0.0,
                "price": close,
                "vwap": vwap,
                "vol_proxy_std": 0.01,
            },
            "session": None,
            # "qty" sera injecté par la validation optimizer (FIXED_LOTS=1)
        }

    monkeypatch.setattr(decider, "process_signal", fake_process_signal)

    # --- 4) Chemin du checkpoint isolé ---
    monkeypatch.setenv("CHECKPOINT_PATH", str(tmp_path / "checkpoint.json"))

    # --- 5) Lancer la boucle jusqu'à épuisement du CSV ---
    run_live_loop, kind = import_run_live_loop()
    run_live_loop()

    # --- 6) Vérifications : logs écrits et non vides ---
    assert os.path.exists(signal_csv), "signals_log.csv non créé"
    assert os.path.exists(perf_csv), "performance_log.csv non créé"

    # il y a 3 lignes de bougies => au moins 3 signaux logués + header
    with open(signal_csv, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
        assert len(lines) >= 2, f"signals_log.csv est vide: {len(lines)} lignes"
        # header + >=1 ligne
        assert any("BUY" in l for l in lines[1:]), "Aucun BUY logué dans signals_log.csv"

    with open(perf_csv, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
        assert len(lines) >= 2, f"performance_log.csv est vide: {len(lines)} lignes"
