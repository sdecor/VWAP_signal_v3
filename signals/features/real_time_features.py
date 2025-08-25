# signals/features/real_time_features.py

import pandas as pd
import ta
from signals.shared.features_utils import (
    add_base_features,
    add_features,
    calculate_vwap,
    load_and_merge_multiframe,
)
from signals.loaders.config_loader import get_general, get_tf_files


def compute_features_for_live_data(df_5m: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Transforme les données 5m brutes en features utilisables par le modèle.
    - Gère la colonne 'time' -> 'datetime'
    - Calcule VWAP, ATR
    - Ajoute les features de base et multi-timeframe (si configuré)
    """
    # 1) Normalisation de la colonne temporelle
    if "time" in df_5m.columns:
        df_5m = df_5m.rename(columns={"time": "datetime"})

    if "datetime" not in df_5m.columns:
        raise ValueError("❌ Colonne 'time' ou 'datetime' manquante dans le CSV 5m.")

    df_5m["datetime"] = pd.to_datetime(df_5m["datetime"])
    df_5m = df_5m.sort_values("datetime").reset_index(drop=True)

    # 2) Paramètres généraux
    general = cfg.get("general", {})
    vwap_period = general.get("DEFAULT_VWAP_PERIOD")
    atr_period = general.get("ATR_PERIOD")

    if atr_period is None or not isinstance(atr_period, int):
        raise ValueError("❌ 'general.ATR_PERIOD' doit être défini (int) dans config.yaml.")

    if not isinstance(vwap_period, int):
        raise ValueError(
            "❌ 'general.DEFAULT_VWAP_PERIOD' doit être un entier en production live."
        )

    # 3) Calculs de base: VWAP, ATR
    df = calculate_vwap(df_5m.copy(), period=vwap_period)

    df["atr"] = ta.volatility.average_true_range(
        high=df["high"], low=df["low"], close=df["close"], window=atr_period
    )

    # 4) Ajout des features de base (utilise TICK_SIZE & co via cfg)
    df = add_base_features(df, _wrap_general_as_obj(general))

    # 5) Ajout des features multi-timeframe (si définies)
    tf_files = get_tf_files()
    if isinstance(tf_files, dict) and len(tf_files) > 0:
        df = load_and_merge_multiframe(df, tf_files, add_features)

    return df


def get_last_row_features(df_full: pd.DataFrame, feature_list: list) -> pd.DataFrame:
    """
    Extrait la dernière ligne de la DataFrame avec les colonnes attendues par le modèle.
    """
    missing = [col for col in feature_list if col not in df_full.columns]
    if missing:
        raise ValueError(f"❌ Colonnes manquantes pour le modèle : {missing}")

    return df_full[feature_list].iloc[[-1]]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

class _GeneralShim:
    """
    Adaptateur pour permettre à add_base_features(df, cfg) d'accéder
    à cfg.TICK_SIZE, cfg.DEFAULT_ENTRY_THRESHOLD à partir de cfg['general'].
    """
    def __init__(self, general: dict):
        self.TICK_SIZE = general.get("TICK_SIZE")
        self.DEFAULT_ENTRY_THRESHOLD = general.get("DEFAULT_ENTRY_THRESHOLD")


def _wrap_general_as_obj(general: dict) -> _GeneralShim:
    return _GeneralShim(general)
