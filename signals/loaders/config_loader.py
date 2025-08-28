# signals/loaders/config_loader.py

import os
import json
import logging
from signals.utils.config_reader import load_config

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

def get_symbol() -> str:
    cfg = load_config()
    return (cfg.get("trading", {}) or {}).get("symbol", "UNKNOWN")


def get_order_type() -> str:
    cfg = load_config()
    return (cfg.get("trading", {}) or {}).get("order_type", "market")


def get_time_in_force() -> str:
    cfg = load_config()
    return (cfg.get("trading", {}) or {}).get("time_in_force", "DAY")


def get_dry_run_mode() -> bool:
    cfg = load_config()
    return (cfg.get("trading", {}) or {}).get("dry_run", True)


def get_default_lots() -> int:
    cfg = load_config()
    # par défaut 1 lot si non défini
    return int((cfg.get("general", {}) or {}).get("DEFAULT_FIXED_LOTS", 1))