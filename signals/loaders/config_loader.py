# signals/loaders/config_loader.py

import os
from signals.utils.config_reader import load_config

# Charge la config YAML une seule fois
CONFIG = load_config("config.yaml")


# -----------------------------
# Getters "simples" (pas de hardcode)
# -----------------------------

def get_config() -> dict:
    """Retourne l'objet de configuration complet (dict)."""
    return CONFIG


def get_general() -> dict:
    """Retourne la section 'general' de la config."""
    return CONFIG.get("general", {})


def get_live_data_path() -> str:
    """
    Retourne le chemin absolu du fichier 5m à surveiller:
    data.data_path + data.input_5m
    """
    data_cfg = CONFIG.get("data", {})
    base = data_cfg.get("data_path")
    fname = data_cfg.get("input_5m")

    if not base or not fname:
        raise ValueError("❌ 'data.data_path' ou 'data.input_5m' manquant dans config.yaml.")

    return os.path.join(base, fname)


def get_tf_files() -> dict:
    """
    Retourne les chemins absolus des fichiers multi-timeframe (dict: tf -> path):
    data.data_path + data.tf_files[tf]
    """
    data_cfg = CONFIG.get("data", {})
    base = data_cfg.get("data_path")
    tf_files_rel = data_cfg.get("tf_files", {})

    if not base:
        raise ValueError("❌ 'data.data_path' manquant dans config.yaml.")

    return {tf: os.path.join(base, rel) for tf, rel in tf_files_rel.items()}


def get_model_path() -> str:
    """
    Chemin vers le modèle ML (XGBoost).
    """
    path = CONFIG.get("model", {}).get("path")
    if not path:
        raise ValueError("❌ Chemin du modèle ML non défini (config.yaml > model.path).")
    return path


def get_optimizer_config_path() -> str:
    """
    Chemin du JSON de configuration horaire (produit par l'optimizer).
    """
    path = CONFIG.get("config_horaire", {}).get("path")
    if not path:
        raise ValueError("❌ Chemin du fichier de configuration horaire non défini (config.yaml > config_horaire.path).")
    return path


def get_timezone() -> str:
    """
    Fuseau horaire (ex: 'UTC', 'Europe/Paris').
    """
    return CONFIG.get("general", {}).get("timezone", "UTC")


def get_evaluation_window_minutes() -> int:
    """
    Fenêtre d'évaluation pour le modèle ML (minutes).
    """
    return int(CONFIG.get("general", {}).get("evaluation_window_minutes", 5))


def get_trading_config() -> dict:
    """Retourne la section 'trading'."""
    return CONFIG.get("trading", {})


def get_symbol() -> str:
    sym = get_trading_config().get("symbol")
    if not sym:
        raise ValueError("❌ 'trading.symbol' manquant dans config.yaml")
    return sym


def get_order_type() -> str:
    return get_trading_config().get("order_type", "market")


def get_time_in_force() -> str:
    return get_trading_config().get("time_in_force", "DAY")


def get_dry_run_mode() -> bool:
    """True = pas d’envoi réel. Géré via YAML."""
    return bool(get_trading_config().get("dry_run", True))


def get_default_lots() -> int:
    """Taille d’ordre par défaut, issue de general.DEFAULT_FIXED_LOTS."""
    lots = CONFIG.get("general", {}).get("DEFAULT_FIXED_LOTS")
    if not isinstance(lots, int) or lots <= 0:
        raise ValueError("❌ 'general.DEFAULT_FIXED_LOTS' doit être un entier > 0.")
    return lots


# -----------------------------
# Validation proactive
# -----------------------------

def validate_config():
    """
    Vérifie que les chemins critiques existent physiquement.
    Soulève une erreur explicite si un chemin est manquant ou invalide.
    """
    paths = {
        "Fichier 5m": get_live_data_path(),
        "Modèle ML": get_model_path(),
        "Config horaire optimizer": get_optimizer_config_path(),
    }

    for tf, path in get_tf_files().items():
        paths[f"TF '{tf}'"] = path

    missing = []
    for label, path in paths.items():
        if not os.path.exists(path):
            missing.append(f"- {label}: '{path}'")

    if missing:
        msg = "❌ Fichiers manquants/introuvables:\n" + "\n".join(missing)
        raise FileNotFoundError(msg)

    print("✅ Configuration validée : tous les fichiers requis sont présents.")
