# signals/backtest/compare_optimizer.py
from __future__ import annotations
import json
import pandas as pd
from typing import Tuple


def load_backtest_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True, errors="coerce")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    return df


def load_optimizer_trades(path: str) -> pd.DataFrame:
    """
    Selon ton format optimizer: si c'est un JSON de configs, remonter à ses sorties trade-level si disponibles.
    Ici on gère deux cas:
      - JSON de configurations (pas de trades → renvoie DF vide informatif)
      - CSV de trades simulés par l'optimizer (colonnes time, action, price, exit_time, exit_price, pnl...)
    """
    if path.endswith(".csv"):
        df = pd.read_csv(path)
        for c in ("time", "exit_time"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
        if "pnl" in df.columns:
            df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
        return df

    # JSON: configs only (no trades)
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return pd.DataFrame([])  # pas de trades disponibles dans le JSON configs


def compare_summaries(bt: pd.DataFrame, opt: pd.DataFrame) -> pd.DataFrame:
    """
    Compare des métriques macro: nb trades, P&L cumulé, pnl/trade moyen.
    """
    def summary(df: pd.DataFrame) -> pd.Series:
        n = len(df)
        pnl_sum = float(df["pnl"].sum()) if "pnl" in df.columns else 0.0
        pnl_mean = (pnl_sum / n) if n else 0.0
        return pd.Series({"n_trades": n, "pnl_sum": pnl_sum, "pnl_mean": pnl_mean})

    return pd.DataFrame({
        "backtest": summary(bt),
        "optimizer": summary(opt)
    })


def compare_by_hour(bt: pd.DataFrame, opt: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    def add_hour(df: pd.DataFrame) -> pd.DataFrame:
        if "time" not in df.columns or df.empty:
            return df.assign(hour=[])
        d = df.copy()
        d["hour"] = pd.to_datetime(d["time"], utc=True).dt.hour
        return d

    bth = add_hour(bt)
    oph = add_hour(opt)

    gb_bt = bth.groupby("hour")["pnl"].sum().rename("bt_pnl").reset_index() if "pnl" in bth.columns else pd.DataFrame()
    gb_op = oph.groupby("hour")["pnl"].sum().rename("opt_pnl").reset_index() if "pnl" in oph.columns else pd.DataFrame()

    merged = pd.merge(gb_bt, gb_op, on="hour", how="outer").fillna(0.0)
    return merged, gb_bt
