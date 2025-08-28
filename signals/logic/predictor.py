# signals/logic/predictor.py
from __future__ import annotations
from typing import Any
import xgboost as xgb


def predict_proba(model: Any, X_df) -> float:
    """
    Calcule la proba avec Booster XGBoost.
    Isolé pour être facilement monkeypatché dans les tests, et
    pour centraliser la création du DMatrix.
    """
    dmx = xgb.DMatrix(X_df)
    out = model.predict(dmx)
    # on assume une seule ligne (1 proba)
    return float(out[0])
