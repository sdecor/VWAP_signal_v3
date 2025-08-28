# signals/loaders/config_loader.py

import os
import json
import logging

def load_json_config(path: str) -> dict:
    """
    Charge un fichier JSON (ex: modèle, config horaire) avec erreurs explicites.
    """
    if not os.path.exists(path):
        logging.error(f"[Config] Fichier introuvable : {path}")
        raise FileNotFoundError(f"Fichier de configuration manquant : {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.info(f"[Config] JSON chargé : {path}")
            return data
    except json.JSONDecodeError as e:
        logging.error(f"[Config] JSON invalide ({path}) : {e}")
        raise ValueError(f"Format JSON invalide dans {path}")
