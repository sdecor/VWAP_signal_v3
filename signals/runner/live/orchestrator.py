import logging
from signals.runner.live.context import init_context
from signals.runner.live.checkpoint import save_checkpoint, load_checkpoint
from signals.runner.live.pipeline import to_utc_datetime, extract_ts_price, validate_with_optimizer

# 👉 imports opérationnels
from signals.feeds.realtime import get_next_candle
from signals.logic.decider import process_signal
from signals.logic.order_executor import execute_and_track_order

def run_live_loop():
    logging.info("🚀 Boucle live démarrée")
    config, logger, tracker, optimizer_cfg = init_context()
    last_processed = load_checkpoint()

    symbol = (config.get("trading", {}) or {}).get("symbol", "UNKNOWN")
    dry_run = (config.get("trading", {}) or {}).get("dry_run", True)

    while True:
        try:
            candle = get_next_candle()
            ts_raw, price = extract_ts_price(candle)
            dt_utc = to_utc_datetime(ts_raw)
            ts_iso = dt_utc.isoformat()

            if last_processed and ts_iso <= last_processed:
                continue

            decision = process_signal(candle) or {}
            action = (decision.get("action") or "FLAT").upper()
            vwap = decision.get("vwap")
            features = decision.get("features")
            session = decision.get("session")
            prob = decision.get("prob")

            decision = validate_with_optimizer(
                decision=decision,
                optimizer_cfg=optimizer_cfg,
                dt_utc=dt_utc,
                price=price,
                vwap=vwap,
                general_cfg=config.get("general", {}) or {},
            )

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
                },
            )

            if action in ("BUY", "SELL") and decision.get("executed"):
                if dry_run:
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

            if price is not None:
                tracker.on_mark(price=float(price))

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

            save_checkpoint(ts_iso)
            last_processed = ts_iso

        except KeyboardInterrupt:
            logging.info("🛑 Arrêt manuel")
            break
        except Exception as e:
            logging.exception(f"[LiveLoop] Erreur: {e}")
            break
