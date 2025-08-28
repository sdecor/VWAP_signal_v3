# signals/features/feature_schema.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import math

import pandas as pd


FALLBACK_FILL_VALUE: float = 0.0


def select_required_features(cfg: Dict[str, Any], cfg_now: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Renvoie la liste des features attendues par priorité :
      1) cfg_now["features"] si définies par l'optimizer pour ce schedule
      2) cfg["model"]["features"] (config.yaml)
    """
    if cfg_now:
        feats = (cfg_now.get("features") or [])
        if feats:
            return list(feats)
    feats = ((cfg.get("model") or {}).get("features") or [])
    return list(feats)


def _ensure_columns(df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
    """
    S'assure que toutes les colonnes existent ; si manquantes, les crée (FALLBACK_FILL_VALUE).
    Conserve uniquement les colonnes de feature_names et dans le bon ordre.
    """
    df2 = df.copy()
    for col in feature_names:
        if col not in df2.columns:
            df2[col] = FALLBACK_FILL_VALUE
    # Ordre strict
    return df2[feature_names].copy()


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Essaie de convertir toutes les colonnes en float (convient aux modèles ML).
    Toute valeur non convertible devient NaN (on gère ensuite).
    """
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def build_feature_frame(enriched_df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
    """
    Construit un DataFrame de features avec l'ordre exact et des valeurs numériques.
    Remplit les colonnes manquantes avec FALLBACK_FILL_VALUE, puis coercion numérique.
    """
    x = _ensure_columns(enriched_df, feature_names)
    x = _coerce_numeric(x)
    # Remplace les NaN par fallback pour éviter échecs de prédiction
    return x.fillna(FALLBACK_FILL_VALUE)


def build_feature_vector_for_row(enriched_df: pd.DataFrame, idx: int, feature_names: List[str]) -> pd.DataFrame:
    """
    Renvoie un DataFrame 1-ligne (mêmes colonnes dans l'ordre) prêt pour le modèle.
    """
    x = build_feature_frame(enriched_df.iloc[[idx]], feature_names)
    # iloc[[idx]] préserve DataFrame 1-ligne ; l’ordre est déjà correct
    return x


def validate_feature_values(row: pd.Series, feature_names: List[str]) -> List[str]:
    """
    Valide une ligne de features :
      - aucune feature manquante
      - valeurs finies (non NaN, non inf)
      - règles simples pour 'hour' et 'minute' si présents
    Renvoie une liste d'erreurs (vide si OK).
    """
    errors: List[str] = []

    for name in feature_names:
        if name not in row.index:
            errors.append(f"missing:{name}")
            continue
        val = row[name]
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            errors.append(f"nan_or_inf:{name}")

    # Règles basiques optionnelles :
    if "hour" in row.index:
        h = row["hour"]
        if not (0 <= float(h) <= 23):
            errors.append("range:hour")
    if "minute" in row.index:
        m = row["minute"]
        if not (0 <= float(m) <= 59):
            errors.append("range:minute")

    return errors


def check_feature_parity(
    enriched_df: pd.DataFrame,
    feature_names: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Construit le frame X et valide la dernière ligne.
    Renvoie (X, errors). X est ordonné et numeric-compat.
    """
    if enriched_df.empty:
        return pd.DataFrame(columns=feature_names), ["empty_enriched_df"]

    X = build_feature_frame(enriched_df, feature_names)
    last = X.iloc[-1]
    errs = validate_feature_values(last, feature_names)
    return X, errs
