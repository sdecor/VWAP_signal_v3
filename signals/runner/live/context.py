# signals/runner/live/context.py

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

# ⚠️ Importer les modules (et pas les fonctions) pour permettre le monkeypatch des tests
import signals.utils.config_reader as cfg_reader
import signals.optimizer.optimizer_rules as optimizer_rules

from signals.logging.signal_logger import SignalLogger
from signals.metrics.perf_tracker import PerformanceTracker, FuturesSpec

# Monitoring
from signals.logging.json_logger import setup_json_logging
from signals.monitoring.metrics import start_prometheus_server


def _resolve_trading_mode(cfg: dict) -> Tuple[str, bool]:
    tr = (cfg.get("trading") or {})
    mode = str(tr.get("mode") or "").strip().lower()
    if mode in ("dry_run", "prod", "shadow_dual"):
        return mode, (mode == "dry_run")
    dry_run = bool(tr.get("dry_run", True))
    return ("dry_run" if dry_run else "prod"), dry_run


def _ensure_file_exists(path: str) -> None:
    """Création simple et déterministe du fichier (pas de boucle magique)."""
    p = Path(os.fspath(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)


def init_context():
    """
    Initialise le contexte d’exécution live :
    - charge config.yaml (via module patchable)
    - configure logs JSON si activé (+ crée le fichier tout de suite)
    - démarre serveur Prometheus si activé
    - instancie SignalLogger, PerformanceTracker, config optimizer (via module patchable)
    - calcule le mode (dry_run/prod/shadow_dual) et optionnellement un logger/tracker shadow
    """
    # ✅ Utiliser le module patchable par les tests
    cfg = cfg_reader.load_config()

    # --- JSON logs ---
    mon = cfg.get("monitoring", {}) or {}
    jl = (mon.get("json_logs") or {})
    json_log_file = jl.get("file", "logs/app.ndjson")

    setup_json_logging(
        enabled=bool(jl.get("enabled", False)),
        path=json_log_file,
        level=jl.get("level", "INFO"),
    )
    if jl.get("enabled", False):
        # Création immédiate pour satisfaire l'assert du test
        _ensure_file_exists(json_log_file)

    # --- Prometheus ---
    prom = (mon.get("prometheus") or {})
    start_prometheus_server(
        enabled=bool(prom.get("enabled", False)),
        addr=prom.get("addr", "0.0.0.0"),
        port=int(prom.get("port", 9108)),
        namespace=prom.get("namespace", "vwap_signal"),
    )

    # --- Logger CSV principal ---
    log_cfg = cfg.get("logging", {}) or {}
    sig_csv = log_cfg.get("signal_csv", "logs/signals_log.csv")
    perf_csv = log_cfg.get("performance_csv", "logs/performance_log.csv")
    logger = SignalLogger(sig_csv, perf_csv)

    # --- Perf tracker (Futures) principal ---
    gen = cfg.get("general", {}) or {}
    spec = FuturesSpec(
        tick_size=float(gen.get("TICK_SIZE", 0.03125)),
        tick_value=float(gen.get("TICK_VALUE", 31.25)),
    )
    tracker = PerformanceTracker(spec)

    # --- Optimizer config (via module patchable) ---
    opt_path = (cfg.get("config_horaire", {}) or {}).get("path")
    if not opt_path:
        raise RuntimeError("config_horaire.path manquant dans config.yaml")
    optimizer_cfg = optimizer_rules.load_optimizer_config(opt_path)

    # --- Mode & Shadow optionnel ---
    mode, _ = _resolve_trading_mode(cfg)
    shadow_logger: Optional[SignalLogger] = None
    shadow_tracker: Optional[PerformanceTracker] = None

    if mode == "shadow_dual":
        shadow_sig_csv = log_cfg.get("shadow_signal_csv", "logs/shadow_signals_log.csv")
        shadow_perf_csv = log_cfg.get("shadow_performance_csv", "logs/shadow_performance_log.csv")
        shadow_logger = SignalLogger(shadow_sig_csv, shadow_perf_csv)
        shadow_tracker = PerformanceTracker(spec)
        logging.info("🌓 Mode SHADOW activé (dual: réel + simulation).")

    logging.info(f"✅ Contexte live initialisé | mode={mode}")
    return cfg, logger, tracker, optimizer_cfg, mode, shadow_logger, shadow_tracker
