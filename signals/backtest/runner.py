# signals/backtest/runner.py
from __future__ import annotations

import os
import csv
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Iterable

import pandas as pd

from signals.utils.config_reader import load_config
from signals.optimizer.optimizer_rules import load_optimizer_config
from signals.features.real_time_features import compute_features_for_live_data, get_last_row_features
from signals.utils.time_utils import get_current_hour_label
from signals.logic.trade_decider import load_model  # XGBoost Booster
from signals.metrics.perf_tracker import PerformanceTracker, FuturesSpec


@dataclass
class Trade:
    time: str
    action: str
    price: float
    qty: float
    reason: str
    session: Optional[str]
    prob: float
    vwap: Optional[float]
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None


class BacktestEngine:
    def __init__(self, cfg: dict, optimizer_cfg: dict):
        self.cfg = cfg
        self.optimizer_cfg = optimizer_cfg["CONFIGURATIONS_BY_SCHEDULE"]
        gen = cfg.get("general", {}) or {}
        self.spec = FuturesSpec(
            tick_size=float(gen.get("TICK_SIZE", 0.03125)),
            tick_value=float(gen.get("TICK_VALUE", 31.25)),
        )
        self.tracker = PerformanceTracker(self.spec)
        # modèle ML (XGBoost Booster)
        self.model = load_model()

    def _load_5m(self) -> pd.DataFrame:
        data_root = self.cfg["data"]["data_path"]
        file_5m = os.path.join(data_root, self.cfg["data"]["input_5m"])
        df = pd.read_csv(file_5m)
        # tri + index propre
        df = df.sort_values("time").reset_index(drop=True)
        return df

    def _prepare_features(self, df5: pd.DataFrame) -> pd.DataFrame:
        # Recalcule les features à la volée avec la même pipeline que le live
        enriched = compute_features_for_live_data(df5.copy(), self.cfg)
        return enriched

    def _select_session_config(self, dt_hour_utc: int) -> Optional[tuple[str, dict]]:
        # identique à la logique live (basée sur optimizer)
        label = get_current_hour_label(dt_hour_utc, {"CONFIGURATIONS_BY_SCHEDULE": self.optimizer_cfg})
        if not label:
            return None
        return label, self.optimizer_cfg[label]

    def _ml_prob_for_row(self, X_row_df: pd.DataFrame) -> float:
        import xgboost as xgb
        dmx = xgb.DMatrix(X_row_df)
        return float(self.model.predict(dmx)[0])

    def _qty_from_config(self, cfg_now: dict) -> float:
        rm = cfg_now.get("RISK_MANAGEMENT", {}) or {}
        return float(rm.get("FIXED_LOTS", 1))

    def simulate(self) -> List[Trade]:
        df = self._load_5m()
        if df.empty:
            return []

        enriched = self._prepare_features(df)
        trades: List[Trade] = []
        position: Optional[Trade] = None

        # colonnes minimales
        if "time" not in enriched.columns or "close" not in enriched.columns:
            raise RuntimeError("Colonnes 'time'/'close' manquantes dans les données enrichies.")

        for i in range(len(enriched)):
            row = enriched.iloc[i]
            # heure UTC (les CSV sont en Z)
            hour = pd.to_datetime(row["time"]).hour
            sel = self._select_session_config(hour)
            if not sel:
                continue
            label, cfg_now = sel

            features_list: List[str] = cfg_now.get("features") or []  # si présent dans ton optimizer
            if not features_list:
                # fallback: utilise le set de features du model de config.yaml (optionnel)
                features_list = (self.cfg.get("model", {}).get("features") or [])

            # extrait la dernière ligne de features pour le modèle
            try:
                X = get_last_row_features(enriched.iloc[: i + 1], features_list)
            except Exception:
                continue

            prob = self._ml_prob_for_row(X)
            seuil = float(cfg_now.get("ML_THRESHOLD", 0.5))
            if prob < seuil:
                # aucune entrée
                # mais si en position : gérer la sortie (exit_type=cross / vwap_level / fixed_ticks)
                if position:
                    exited = self._maybe_exit(position, row, cfg_now)
                    if exited:
                        self._close_position(position, row)
                        trades.append(position)
                        position = None
                continue

            # entrée si pas en position
            if not position:
                side = "BUY"  # (tu peux dériver BUY/SELL selon signal/base VWAP MR; ici BUY par simplicité)
                qty = self._qty_from_config(cfg_now)
                entry = Trade(
                    time=row["time"],
                    action=side,
                    price=float(row["close"]),
                    qty=qty,
                    reason=f"ML≥{seuil} ({prob:.2f}) | {label}",
                    session=label,
                    prob=prob,
                    vwap=float(row["vwap"]) if "vwap" in row else None,
                )
                position = entry
                continue

            # déjà en position : vérifier sortie
            exited = self._maybe_exit(position, row, cfg_now)
            if exited:
                self._close_position(position, row)
                trades.append(position)
                position = None

        # force une clôture à la fin si besoin (marque à marché)
        if position:
            self._close_position(position, enriched.iloc[-1])
            trades.append(position)

        return trades

    def _maybe_exit(self, pos: Trade, row: pd.Series, cfg_now: dict) -> bool:
        # Exemples d'exit basiques alignés avec optimizer (simplifiés)
        tp_type = (cfg_now.get("RISK_MANAGEMENT", {}) or {}).get("TP_TYPE", "vwap_level")
        if tp_type == "fixed_ticks":
            ticks = float(cfg_now["RISK_MANAGEMENT"].get("TP_TICKS", 4))
            target = pos.price + (ticks * self.spec.tick_size) * (1 if pos.action == "BUY" else -1)
            if (pos.action == "BUY" and float(row["high"]) >= target) or (pos.action == "SELL" and float(row["low"]) <= target):
                return True
            return False
        # vwap_level / cross (simplifié) → sortie si close repasse vwap
        if "vwap" in row:
            vwap = float(row["vwap"])
            close = float(row["close"])
            if pos.action == "BUY" and close <= vwap:
                return True
            if pos.action == "SELL" and close >= vwap:
                return True
        return False

    def _close_position(self, pos: Trade, row: pd.Series) -> None:
        exit_price = float(row["close"])
        pos.exit_time = row["time"]
        pos.exit_price = exit_price
        # PnL en $ (futures): ticks * tick_value
        dir_ = 1 if pos.action == "BUY" else -1
        pnl_ticks = (exit_price - pos.price) / self.spec.tick_size * dir_
        pnl_usd = pnl_ticks * self.spec.tick_value * pos.qty
        pos.pnl = pnl_usd
        # alimente le tracker (optionnel selon ton usage)
        self.tracker.on_fill_simulated(
            side=pos.action, fill_price=pos.price, qty=pos.qty, mode="entry"
        )
        self.tracker.on_fill_simulated(
            side=("SELL" if pos.action == "BUY" else "BUY"),
            fill_price=exit_price,
            qty=pos.qty,
            mode="exit",
        )


def run_backtest_to_csv(output_path: str) -> None:
    cfg = load_config()
    optimizer_cfg = load_optimizer_config(cfg["config_horaire"]["path"])
    engine = BacktestEngine(cfg, optimizer_cfg)
    trades = engine.simulate()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time","action","price","qty","prob","session","reason","exit_time","exit_price","pnl"])
        for t in trades:
            w.writerow([
                t.time, t.action, f"{t.price:.6f}", f"{t.qty:.2f}", f"{t.prob:.6f}",
                t.session or "", t.reason, t.exit_time or "", f"{(t.exit_price or 0):.6f}", f"{(t.pnl or 0):.2f}"
            ])
