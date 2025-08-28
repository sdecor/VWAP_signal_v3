# signals/features/feature_adapter.py
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import pandas as pd

from signals.features.feature_schema import (
    select_required_features,
    build_feature_vector_for_row,
    validate_feature_values,
)


def get_feature_vector_for_prediction(
    *,
    enriched_df: pd.DataFrame,
    cfg: Dict[str, Any],
    cfg_now: Optional[Dict[str, Any]] = None,
    row_index: Optional[int] = None,
) -> Tuple[pd.DataFrame, list[str], list[str]]:
    """
    Prépare X (1-ligne, ordre exact) + liste des features + erreurs de validation (si any).
    - feature_names = schedule.features si dispo sinon cfg["model"]["features"]
    - row_index = index de la ligne à extraire (par défaut dernière)
    """
    feats = select_required_features(cfg, cfg_now)
    if row_index is None:
        row_index = len(enriched_df) - 1
    X = build_feature_vector_for_row(enriched_df, row_index, feats)
    errors = validate_feature_values(X.iloc[0], feats)
    return X, feats, errors
