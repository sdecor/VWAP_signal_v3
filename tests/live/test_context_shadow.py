# tests/live/test_context_shadow.py

import os
import types

from signals.runner.live import context as ctx


def test_resolve_trading_mode_legacy():
    # fallback via trading.dry_run
    cfg = {"trading": {"dry_run": True}}
    mode, dry_compat = ctx._resolve_trading_mode(cfg)
    assert mode == "dry_run" and dry_compat is True

    cfg = {"trading": {"dry_run": False}}
    mode, dry_compat = ctx._resolve_trading_mode(cfg)
    assert mode == "prod" and dry_compat is False


def test_resolve_trading_mode_new_modes():
    cfg = {"trading": {"mode": "dry_run"}}
    mode, dry_compat = ctx._resolve_trading_mode(cfg)
    assert mode == "dry_run" and dry_compat is True

    cfg = {"trading": {"mode": "prod"}}
    mode, dry_compat = ctx._resolve_trading_mode(cfg)
    assert mode == "prod" and dry_compat is False

    cfg = {"trading": {"mode": "shadow_dual"}}
    mode, dry_compat = ctx._resolve_trading_mode(cfg)
    assert mode == "shadow_dual" and dry_compat is False


def test_init_context_shadow_mode(monkeypatch, tmp_path):
    # --- 1) fake config : shadow_dual + monitoring désactivé (évite serveur)
    fake_cfg = {
        "monitoring": {
            "json_logs": {"enabled": True, "file": str(tmp_path / "app.ndjson"), "level": "INFO"},
            "prometheus": {"enabled": False},
        },
        "logging": {
            "signal_csv": str(tmp_path / "signals.csv"),
            "performance_csv": str(tmp_path / "perf.csv"),
            "shadow_signal_csv": str(tmp_path / "shadow_signals.csv"),
            "shadow_performance_csv": str(tmp_path / "shadow_perf.csv"),
        },
        "trading": {"mode": "shadow_dual"},
        "general": {"TICK_SIZE": 0.03125, "TICK_VALUE": 31.25},
        "config_horaire": {"path": str(tmp_path / "optimizer.json")},
    }

    # --- 2) patch load_config pour renvoyer fake_cfg
    import signals.utils.config_reader as cfg_reader
    monkeypatch.setattr(cfg_reader, "load_config", lambda *a, **k: fake_cfg)

    # --- 3) patch optimizer_rules.load_optimizer_config (pas d'accès FS)
    import signals.optimizer.optimizer_rules as rules
    monkeypatch.setattr(rules, "load_optimizer_config", lambda p: {"CONFIGURATIONS_BY_SCHEDULE": {}})

    # --- 4) patch start_prometheus_server appelé par init_context (no-op)
    import signals.runner.live.context as ctx_mod
    monkeypatch.setattr(ctx_mod, "start_prometheus_server", lambda **kw: None)

    cfg, logger, tracker, optimizer_cfg, mode, shadow_logger, shadow_tracker = ctx.init_context()

    assert mode == "shadow_dual"
    assert logger is not None and tracker is not None
    # en shadow, on doit avoir les objets shadow
    assert shadow_logger is not None and shadow_tracker is not None

    # le fichier de logs JSON doit exister après init (setup_json_logging a loggé une ligne d'info)
    assert (tmp_path / "app.ndjson").exists()
