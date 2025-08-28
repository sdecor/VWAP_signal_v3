# signals/logging/signal_logger.py

import os
import csv
from typing import Optional, Dict, Any

class SignalLogger:
    """
    Écrit les signaux et la performance dans des CSV append-only.
    - signal: un enregistrement par signal généré (même sans exécution).
    - perf: snapshots réguliers (mark-to-market).
    """

    def __init__(self, signal_csv_path: str, perf_csv_path: str):
        self.signal_csv_path = signal_csv_path
        self.perf_csv_path = perf_csv_path

        # Assure l'existence des dossiers
        os.makedirs(os.path.dirname(signal_csv_path), exist_ok=True)
        os.makedirs(os.path.dirname(perf_csv_path), exist_ok=True)

        # Crée les headers si fichiers absents
        if not os.path.exists(signal_csv_path):
            with open(signal_csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "timestamp", "symbol", "action", "prob", "price",
                    "qty", "reason", "session", "vwap", "spread_to_vwap",
                    "features", "extra"
                ])
                w.writeheader()

        if not os.path.exists(perf_csv_path):
            with open(perf_csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "timestamp", "equity", "realized_pnl", "unrealized_pnl",
                    "drawdown", "max_equity", "n_trades", "position_size",
                    "last_price"
                ])
                w.writeheader()

    def log_signal(
        self,
        *,
        timestamp: str,
        symbol: str,
        action: str,                # "BUY" | "SELL" | "FLAT"
        prob: Optional[float],
        price: Optional[float],
        qty: Optional[float] = None,
        reason: Optional[str] = None,
        session: Optional[str] = None,
        vwap: Optional[float] = None,
        spread_to_vwap: Optional[float] = None,
        features: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        row = {
            "timestamp": timestamp,
            "symbol": symbol,
            "action": action,
            "prob": prob,
            "price": price,
            "qty": qty,
            "reason": reason,
            "session": session,
            "vwap": vwap,
            "spread_to_vwap": spread_to_vwap,
            "features": repr(features) if features is not None else None,
            "extra": repr(extra) if extra is not None else None,
        }
        with open(self.signal_csv_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=row.keys()).writerow(row)

    def log_performance_snapshot(
        self,
        *,
        timestamp: str,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        drawdown: float,
        max_equity: float,
        n_trades: int,
        position_size: float,
        last_price: Optional[float],
    ) -> None:
        row = {
            "timestamp": timestamp,
            "equity": equity,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "drawdown": drawdown,
            "max_equity": max_equity,
            "n_trades": n_trades,
            "position_size": position_size,
            "last_price": last_price,
        }
        with open(self.perf_csv_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=row.keys()).writerow(row)
