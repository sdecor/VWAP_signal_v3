# features_utils.py

import pandas as pd
import numpy as np
import ta


def calculate_vwap(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calcule une version simplifiée du VWAP sur n périodes glissantes.
    """
    pv = df["close"] * df["volume"]
    df["vwap"] = pv.rolling(window=period).sum() / df["volume"].rolling(window=period).sum()
    return df


def add_base_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """
    Ajoute les features de base utilisées dans la stratégie VWAP Mean Reversion.
    """
    df["dist_to_vwap"] = df["close"] - df["vwap"]
    df["dist_to_vwap_atr"] = df["dist_to_vwap"] / (df["atr"] * cfg.TICK_SIZE)
    df["normalized_dist_to_vwap"] = df["dist_to_vwap_atr"]

    df["signal"] = 0
    df.loc[df["normalized_dist_to_vwap"] < -cfg.DEFAULT_ENTRY_THRESHOLD, "signal"] = 1
    df.loc[df["normalized_dist_to_vwap"] > cfg.DEFAULT_ENTRY_THRESHOLD, "signal"] = -1

    for period in [3, 6, 12]:
        df[f"ret_{period}"] = df["close"].pct_change(period)

    df["volatility_6"] = df["close"].rolling(6).std()
    df["volatility_12"] = df["close"].rolling(12).std()
    df["range_6"] = df["high"].rolling(6).max() - df["low"].rolling(6).min()
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["vwap_slope_5"] = df["vwap"].diff(5)
    df["volume_relative_10"] = df["volume"] / df["volume"].rolling(10).mean()

    return df


def add_features(df: pd.DataFrame, prefix='', ema_span=21, rsi_period=14, vol_period=12) -> pd.DataFrame:
    """
    Ajoute des indicateurs techniques génériques (EMA, RSI, vol).
    """
    df[f"{prefix}ema{ema_span}"] = df["close"].ewm(span=ema_span).mean()
    df[f"{prefix}rsi{rsi_period}"] = ta.momentum.rsi(df["close"], window=rsi_period)
    df[f"{prefix}vol{vol_period}"] = df["close"].rolling(vol_period).std()
    return df


def load_and_merge_multiframe(df: pd.DataFrame, tf_files: dict, add_features_func) -> pd.DataFrame:
    """
    Fusionne les données multi-timeframe avec la 5m.
    """
    for tf, path in tf_files.items():
        if not isinstance(path, str) or not path.endswith(".csv") or not tf:
            continue

        try:
            dftf = pd.read_csv(path)
            dftf["datetime"] = pd.to_datetime(dftf["time"]) if "time" in dftf.columns else pd.to_datetime(dftf.iloc[:, 0])
            dftf = dftf.sort_values("datetime").reset_index(drop=True)
            dftf = add_features_func(dftf, prefix=f"{tf}_", ema_span=21, rsi_period=14, vol_period=12)

            tfcols = [f"{tf}_ema21", f"{tf}_rsi14", f"{tf}_vol12"]
            dftf_subset = dftf[["datetime"] + tfcols].copy()

            df = df.sort_values("datetime").reset_index(drop=True)
            dftf_subset = dftf_subset.sort_values("datetime").reset_index(drop=True)

            df = pd.merge_asof(df, dftf_subset, on="datetime", direction="backward")

        except Exception as e:
            print(f"❌ Erreur lors de la fusion MTF pour {tf}: {e}")
            continue

    return df
