# signals/runner/live/orchestrator.py

import logging
from typing import Optional

from signals.runner.live.context import init_context
from signals.runner.live.checkpoint import save_checkpoint, load_checkpoint
from signals.runner.live.pipeline import to_utc_datetime, extract_ts_price, validate_with_optimizer

# Data feed & décision
from signals.feeds.realtime import get_next_candle
from signals.logic.decider import process_signal

# Exécution ordres (prod)
from signals.logic.order_executor import execute_and_track_order

# Monitoring
from signals.monitoring.metrics import record_signal, set_perf_gauges


def _log_and_metrics(
    *,
    logger,
    tracker,
    ts_iso: str,
    symbol: str,
    action: str,
    prob: Optional[float],
    price: Optional[float],
    decision: dict,
    vwap: Optional[float],
    features: Optional[dict],
    session: Optional[str],
    is_shadow: bool = False,
):
    # Log signal
    spread_to_vwap = (price - vwap) if (price is not None and vwap is not None) else None
    logger.log_signal(
        timestamp=ts_iso,
        symbol=symbol,
        action=action,
        prob=prob,
        price=price,
        qty=decision.get("qty"),
        reason=decision.get("reason") or decision.get("reject_reason"),
        session=session or decision.get("schedule"),
        vwap=vwap,
        spread_to_vwap=spread_to_vwap,
        features=features,
        extra={
            "schedule": decision.get("schedule"),
            "vwap_config": decision.get("vwap_config"),
            "risk": decision.get("risk"),
            "shadow": is_shadow,
        },
    )

    # Update perf snapshot
    snap = tracker.snapshot()
    logger.log_performance_snapshot(
        timestamp=ts_iso,
        equity=snap["equity"],
        realized_pnl=snap["realized_pnl"],
        unrealized_pnl=snap["unrealized_pnl"],
        drawdown=snap["drawdown"],
        max_equity=snap["max_equity"],
        n_trades=snap["n_trades"],
        position_size=snap["position_size"],
        last_price=snap["last_price"],
    )
    # prom (pour le principal uniquement, shadow non exposé en métriques ici)
    if not is_shadow:
        set_perf_gauges(snap)


def run_live_loop():
    """
    Boucle live :
    - lit les bougies du feed
    - appelle process_signal(candle) pour produire une décision
    - valide contre la config optimizer (horaire + seuil ML + risk)
    - modes:
        - dry_run: simule le fill (tracker principal)
        - prod: envoie ordre réel
        - shadow_dual: envoie ordre réel ET simule en parallèle (shadow tracker/logger)
    - logue signaux + snapshots de perf
    - enregistre checkpoint (dernier timestamp traité)
    """
    logging.info("🚀 Boucle live démarrée")
    config, logger, tracker, optimizer_cfg, mode, shadow_logger, shadow_tracker = init_context()
    last_processed = load_checkpoint()

    symbol = (config.get("trading", {}) or {}).get("symbol", "UNKNOWN")
    is_dry = (mode == "dry_run")
    is_shadow = (mode == "shadow_dual")

    while True:
        try:
            candle = get_next_candle()
            ts_raw, price = extract_ts_price(candle)
            dt_utc = to_utc_datetime(ts_raw)
            ts_iso = dt_utc.isoformat()

            # Idempotence
            if last_processed and ts_iso <= last_processed:
                continue

            # Décision
            decision = process_signal(candle) or {}
            action = (decision.get("action") or "FLAT").upper()
            vwap = decision.get("vwap")
            features = decision.get("features")
            session = decision.get("session")
            prob = decision.get("prob")

            # Validation optimizer
            decision = validate_with_optimizer(
                decision=decision,
                optimizer_cfg=optimizer_cfg,
                dt_utc=dt_utc,
                price=price,
                vwap=vwap,
                general_cfg=config.get("general", {}) or {},
            )

            # Monitoring signal
            record_signal(action, bool(decision.get("executed")), decision.get("schedule"))

            # --- Exécution principale ---
            if action in ("BUY", "SELL") and decision.get("executed"):
                if is_dry:
                    fill_price = decision.get("fill_price", price)
                    qty = float(decision.get("qty") or 0)
                    if fill_price is not None and qty > 0:
                        tracker.on_fill(price=float(fill_price), qty=qty, side=action)
                        logging.info(f"[DryRun] Filled {action} {qty} @ {fill_price}")
                else:
                    exec_result = execute_and_track_order(
                        symbol=symbol,
                        side=action,
                        qty=float(decision.get("qty") or 0),
                        limit_price=None,
                        market_price=float(price) if price is not None else None,
                        tracker=tracker,
                    )
                    decision.update(exec_result or {})

            # Marquage prix pour PnL latent principal
            if price is not None:
                tracker.on_mark(price=float(price))

            # Logs + perf + métriques principal
            _log_and_metrics(
                logger=logger,
                tracker=tracker,
                ts_iso=ts_iso,
                symbol=symbol,
                action=action,
                prob=prob,
                price=price,
                decision=decision,
                vwap=vwap,
                features=features,
                session=session,
                is_shadow=False,
            )

            # --- Exécution SHADOW (si activé) ---
            if is_shadow and shadow_logger is not None and shadow_tracker is not None:
                shadow_decision = dict(decision)  # on log les mêmes infos (qty, schedule, etc.)
                if action in ("BUY", "SELL") and decision.get("executed"):
                    # Simule le fill côté shadow, indépendamment du réel
                    fill_price = decision.get("fill_price", price)
                    qty = float(decision.get("qty") or 0)
                    if fill_price is not None and qty > 0:
                        shadow_tracker.on_fill(price=float(fill_price), qty=qty, side=action)
                        logging.info(f"[Shadow] Filled {action} {qty} @ {fill_price}")

                if price is not None:
                    shadow_tracker.on_mark(price=float(price))

                _log_and_metrics(
                    logger=shadow_logger,
                    tracker=shadow_tracker,
                    ts_iso=ts_iso,
                    symbol=symbol,
                    action=action,
                    prob=prob,
                    price=price,
                    decision=shadow_decision,
                    vwap=vwap,
                    features=features,
                    session=session,
                    is_shadow=True,
                )

            # Checkpoint
            save_checkpoint(ts_iso)
            last_processed = ts_iso

        except KeyboardInterrupt:
            logging.info("🛑 Arrêt manuel")
            break
        except Exception as e:
            logging.exception(f"[LiveLoop] Erreur: {e}")
            break
