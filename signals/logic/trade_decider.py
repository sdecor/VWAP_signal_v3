# signals/logic/trade_decider.py

import pandas as pd
import xgboost as xgb
from datetime import datetime
import pytz
import json

from signals.features.real_time_features import (
    compute_features_for_live_data,
    get_last_row_features,
)
from signals.loaders.config_loader import (
    get_live_data_path,
    get_model_path,
    get_optimizer_config_path,
    get_timezone,
)
from signals.utils.time_utils import get_current_hour_label
from signals.utils.config_reader import load_config

cfg = load_config("config.yaml")


def load_best_configurations() -> dict:
    """
    Charge la configuration horaire optimale générée par l'optimizer.
    """
    config_path = get_optimizer_config_path()
    with open(config_path, "r") as f:
        return json.load(f)


def load_model():
    """
    Charge le modèle XGBoost (entraîné).
    """
    model_path = get_model_path()
    return xgb.Booster(model_file=model_path)


def is_session_active(config_for_now: dict, current_hour: int) -> bool:
    """
    Vérifie si l’heure actuelle est dans la session définie.
    """
    h_start = config_for_now["heure_debut"]
    h_end = config_for_now["heure_fin"]
    return h_start <= current_hour < h_end


def decide_trade(data_path: str = None):
    """
    Déclenchée à chaque nouvelle barre.
    Applique les features, fait une prédiction, et retourne un signal si pertinent.
    """
    data_path = data_path or get_live_data_path()
    df = pd.read_csv(data_path)
    if df.empty:
        print("⚠️ Données vides, impossible de décider.")
        return None

    optimizer_configs = load_best_configurations()
    model = load_model()

    # Heure actuelle avec fuseau
    tz = pytz.timezone(get_timezone())
    now = datetime.now(tz)
    hour_label = get_current_hour_label(now.hour, optimizer_configs)

    if hour_label is None:
        print(f"⏳ Aucune session active à {now.hour}h.")
        return None

    config_now = optimizer_configs[hour_label]

    if not is_session_active(config_now, now.hour):
        print(f"🕒 Hors session ({config_now['heure_debut']}h-{config_now['heure_fin']}h).")
        return None

    # Appliquer la logique optimizer : enrichir les données
    enriched_df = compute_features_for_live_data(df.copy(), cfg)

    # Extraire la ligne pour prédiction
    try:
        X = get_last_row_features(enriched_df, config_now["features"])
    except ValueError as e:
        print(str(e))
        return None

    # Prédiction
    dmatrix = xgb.DMatrix(X)
    prob = float(model.predict(dmatrix)[0])

    seuil = config_now["seuil_proba"]
    if prob >= seuil:
        print(f"✅ Signal confirmé : proba={prob:.2f} ≥ seuil={seuil}")
        return {
            "timestamp": now.isoformat(),
            "signal": "BUY" if prob >= config_now.get("seuil_proba_buy", seuil) else "SELL",
            "probability": prob,
            "features": X.to_dict(orient="records")[0],
            "config_used": hour_label
        }
    else:
        print(f"❌ Pas de signal : proba={prob:.2f} < seuil={seuil}")
        return None
