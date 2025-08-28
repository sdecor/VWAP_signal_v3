import logging
from signals.utils.config_reader import load_config
from signals.logging.signal_logger import SignalLogger
from signals.metrics.perf_tracker import PerformanceTracker, FuturesSpec
from signals.optimizer.optimizer_rules import load_optimizer_config

def init_context():
    cfg = load_config()

    log_cfg = cfg.get("logging", {}) or {}
    sig_csv = log_cfg.get("signal_csv", "logs/signals_log.csv")
    perf_csv = log_cfg.get("performance_csv", "logs/performance_log.csv")
    logger = SignalLogger(sig_csv, perf_csv)

    gen = cfg.get("general", {}) or {}
    spec = FuturesSpec(
        tick_size=float(gen.get("TICK_SIZE", 0.03125)),
        tick_value=float(gen.get("TICK_VALUE", 31.25)),
    )
    tracker = PerformanceTracker(spec)

    opt_path = (cfg.get("config_horaire", {}) or {}).get("path")
    if not opt_path:
        raise RuntimeError("config_horaire.path manquant dans config.yaml")
    optimizer_cfg = load_optimizer_config(opt_path)

    return cfg, logger, tracker, optimizer_cfg
