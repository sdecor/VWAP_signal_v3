# signals/logic/decider_live.py
from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import pandas as pd

import signals.utils.config_reader as cfg_reader
import signals.optimizer.optimizer_rules as rules

from signals.features.feature_schema import select_required_features
from signals.features.feature_adapter import get_feature_vector_for_prediction
from signals.logic.optimizer_parity import (
    get_active_schedule,
    decide_entry_from_features,
    enrich_signal_with_session_and_qty,
)
from signals.logic.predictor import predict_proba


def process_signal_from_enriched(
    *,
    enriched_df: pd.DataFrame,
    row_index: Optional[int] = None,
    now: Optional[datetime] = None,
    tracker: Optional[Any] = None,
    model: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Version 'live' : prend un DataFrame enrichi (features déjà calculées),
    prépare X avec les features exactes attendues (ordre strict), appelle le modèle,
    applique la logique d'entrée (optimizer parity) et enrichit le signal (session + qty).

    Args:
      enriched_df: DataFrame contenant au moins 'normalized_dist_to_vwap', 'close', ... et toutes les features producibles.
      row_index:   index de la ligne à prédire (par défaut, dernière).
      now:         datetime UTC courante (injectable en test).
      tracker:     (optionnel) objet de tracking si besoin (non utilisé ici; le guard DD est géré dans decider.py version features-dict).
      model:       Booster XGBoost déjà chargé (si None, on suppose que l'appelant gère la prédiction ailleurs).

    Returns:
      dict signal {action, prob, features{normalized_dist_to_vwap}, session, qty} ou None si pas de signal.
    """
    if enriched_df is None or enriched_df.empty:
        return None

    app_cfg = cfg_reader.load_config()
    opt_path = (app_cfg.get("config_horaire", {}) or {}).get("path")
    optimizer_root = rules.load_optimizer_config(opt_path)
    by_schedule = optimizer_root["CONFIGURATIONS_BY_SCHEDULE"]

    now = now or datetime.now(timezone.utc)
    hour = now.hour

    # ✅ FIX: déterminer le schedule actif avant d'y accéder
    active = get_active_schedule(hour_utc=hour, optimizer_cfg_by_schedule=by_schedule)
    if not active:
        return None
    session_label, cfg_now = active

    # 1) Features attendues (schedule.priority > model.features)
    feats = select_required_features(app_cfg, cfg_now)

    # 2) Construire X (1 ligne, ordre strict, valeurs numériques, fallback=0.0)
    X, feats_used, errs = get_feature_vector_for_prediction(
        enriched_df=enriched_df, cfg=app_cfg, cfg_now=cfg_now, row_index=row_index
    )
    if errs:
        # si les features sont invalides, on refuse le signal
        return None

    # 3) Proba via le modèle (monkeypatchable via signals.logic.predictor.predict_proba)
    if model is None:
        # L'appelant devrait injecter le modèle ; ici on ne force pas le chargement
        return None
    prob = predict_proba(model, X)

    # 4) Construire la vue 'features' pour decide_entry (doit contenir normalized_dist_to_vwap)
    idx = row_index if row_index is not None else (len(enriched_df) - 1)
    row = enriched_df.iloc[idx]
    features_view = {}
    if "normalized_dist_to_vwap" in row.index:
        try:
            features_view["normalized_dist_to_vwap"] = float(row["normalized_dist_to_vwap"])
        except Exception:
            features_view["normalized_dist_to_vwap"] = 0.0
    else:
        # si non disponible, pas de décision MR
        return None

    sig = decide_entry_from_features(features=features_view, prob=prob, cfg_now=cfg_now)
    if not sig:
        return None

    # 5) Ajoute session + qty depuis FIXED_LOTS
    sig = enrich_signal_with_session_and_qty(sig, session_label=session_label, cfg_now=cfg_now)
    return sig
