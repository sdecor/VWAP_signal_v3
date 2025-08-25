import pandas as pd
import xgboost as xgb
import numpy as np


def apply(df, model_path, horaire_config, params):
    """Applique un modèle XGBoost pour générer un signal d'achat basé sur un seuil horaire."""
    model = xgb.XGBClassifier()
    model.load_model(model_path)

    # Feature engineering
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute

    # Appliquer les seuils dynamiques en fonction de l'heure
    df['threshold'] = df['hour'].map(
        lambda h: horaire_config.get(str(h), {}).get("min_prob", params.get("min_prob", 0.5))
    )

    # Sélection des colonnes de features
    feature_cols = [col for col in df.columns if col not in ['timestamp', 'threshold']]
    dmatrix = xgb.DMatrix(df[feature_cols])

    # Prédictions
    predicted_probs = model.predict_proba(dmatrix)[:, 1]
    df['predicted_prob'] = predicted_probs
    df['signal'] = np.where(df['predicted_prob'] >= df['threshold'], 'BUY', 'NO_TRADE')

    return df


if __name__ == "__main__":
    print("Ce module doit être utilisé via signal_generator.py ou un autre script.")
