# signals/logging/signal_logger.py

import csv
import os
from typing import Optional, Dict, Any


class SignalLogger:
    def __init__(self, signal_csv_path: str, performance_csv_path: str):
        self.signal_csv_path = signal_csv_path
        self.performance_csv_path = performance_csv_path
        os.makedirs(os.path.dirname(signal_csv_path) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(performance_csv_path) or ".", exist_ok=True)
        self._ensure_signal_header()
        self._ensure_perf_header()

    def _ensure_signal_header(self):
        if not os.path.exists(self.signal_csv_path):
            with open(self.signal_csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    "timestamp","symbol","action","prob","price","qty","reason","session","vwap","spread_to_vwap","features","extra"
                ])

    def _ensure_perf_header(self):
        if not os.path.exists(self.performance_csv_path):
            with open(self.performance_csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    "timestamp","equity","realized_pnl","unrealized_pnl","drawdown","max_equity","n_trades","position_size","last_price"
                ])

    def log_signal(
        self,
        *,
        timestamp: str,
        symbol: str,
        action: Optional[str],
        prob: Optional[float],
        price: Optional[float],
        qty: Optional[float],
        reason: Optional[str],
        session: Optional[str],
        vwap: Optional[float],
        spread_to_vwap: Optional[float],
        features: Optional[Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        act = (action or "").upper()
        row = [
            timestamp,
            symbol,
            act,  # ✅ "BUY"/"SELL"
            (None if prob is None else f"{prob:.6f}"),
            (None if price is None else f"{price:.6f}"),
            (None if qty is None else f"{qty:.6f}"),
            reason or "",
            session or "",
            (None if vwap is None else f"{vwap:.6f}"),
            (None if spread_to_vwap is None else f"{spread_to_vwap:.6f}"),
            (features if features is not None else ""),
            (extra if extra is not None else ""),
        ]
        with open(self.signal_csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

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
        row = [
            timestamp,
            f"{equity:.6f}",
            f"{realized_pnl:.6f}",
            f"{unrealized_pnl:.6f}",
            f"{drawdown:.6f}",
            f"{max_equity:.6f}",
            n_trades,
            f"{position_size:.6f}",
            (None if last_price is None else f"{last_price:.6f}"),
        ]
        with open(self.performance_csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
