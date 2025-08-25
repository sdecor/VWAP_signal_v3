# signals/loaders/config_validator.py

from typing import Any, Dict, List
from signals.loaders.config_loader import get_config


def validate_config_values() -> None:
    """
    Valide la structure et les valeurs de config.yaml (présence, types, domaines).
    Soulève ValueError avec un message agrégé si la config est invalide.
    """
    cfg = get_config()
    errors: List[str] = []

    # ---- general ----
    general = cfg.get("general", {})
    _require_keys("general", general, [
        "TICK_SIZE",
        "TICK_VALUE",
        "ATR_PERIOD",
        "DEFAULT_VWAP_PERIOD",
        "DEFAULT_ENTRY_THRESHOLD",
        "DEFAULT_EXIT_TYPE",
        "DEFAULT_EXIT_THRESHOLD",
        "DEFAULT_TP_TYPE",
        "DEFAULT_TP_TICKS",
        "DEFAULT_FIXED_LOTS",
        "ATR_MULTIPLIER_FOR_SL",
        "MAX_EQUITY_DD_USD",
        "timezone",
    ], errors)

    _require_type("general.TICK_SIZE", general.get("TICK_SIZE"), (int, float), errors, positive=True)
    _require_type("general.TICK_VALUE", general.get("TICK_VALUE"), (int, float), errors, positive=True)
    _require_type("general.ATR_PERIOD", general.get("ATR_PERIOD"), int, errors, min_value=1)
    _require_type("general.DEFAULT_VWAP_PERIOD", general.get("DEFAULT_VWAP_PERIOD"), int, errors, min_value=1)
    _require_type("general.DEFAULT_ENTRY_THRESHOLD", general.get("DEFAULT_ENTRY_THRESHOLD"), (int, float), errors, min_value=0)
    _require_type("general.DEFAULT_EXIT_TYPE", general.get("DEFAULT_EXIT_TYPE"), str, errors, non_empty=True)
    _require_type("general.DEFAULT_EXIT_THRESHOLD", general.get("DEFAULT_EXIT_THRESHOLD"), (int, float), errors, min_value=0)
    _require_type("general.DEFAULT_TP_TYPE", general.get("DEFAULT_TP_TYPE"), str, errors, non_empty=True)
    _require_type("general.DEFAULT_TP_TICKS", general.get("DEFAULT_TP_TICKS"), int, errors, min_value=0)
    _require_type("general.DEFAULT_FIXED_LOTS", general.get("DEFAULT_FIXED_LOTS"), int, errors, min_value=1)
    _require_type("general.ATR_MULTIPLIER_FOR_SL", general.get("ATR_MULTIPLIER_FOR_SL"), (int, float), errors, positive=True)
    _require_type("general.MAX_EQUITY_DD_USD", general.get("MAX_EQUITY_DD_USD"), (int, float), errors, positive=True)
    _require_type("general.timezone", general.get("timezone"), str, errors, non_empty=True)

    # ---- data ----
    data = cfg.get("data", {})
    _require_keys("data", data, ["data_path", "input_5m", "tf_files"], errors)
    _require_type("data.data_path", data.get("data_path"), str, errors, non_empty=True)
    _require_type("data.input_5m", data.get("input_5m"), str, errors, non_empty=True)

    tf_files = data.get("tf_files")
    if not isinstance(tf_files, dict) or not tf_files:
        errors.append("data.tf_files doit être un dict non vide (ex: { '15min': 'UB_15min.csv', ... }).")
    else:
        for tf, rel_path in tf_files.items():
            if not isinstance(tf, str) or not tf:
                errors.append(f"data.tf_files: clé TF invalide: {tf!r}")
            if not isinstance(rel_path, str) or not rel_path:
                errors.append(f"data.tf_files[{tf}]: chemin invalide: {rel_path!r}")

    # ---- model ----
    model = cfg.get("model", {})
    _require_keys("model", model, ["path", "features"], errors)
    _require_type("model.path", model.get("path"), str, errors, non_empty=True)

    features = model.get("features")
    if not isinstance(features, list) or not features:
        errors.append("model.features doit être une liste non vide (colonnes utilisées par le modèle).")
    else:
        for i, f in enumerate(features):
            if not isinstance(f, str) or not f:
                errors.append(f"model.features[{i}] doit être une chaîne non vide.")

    # ---- config_horaire ----
    ch = cfg.get("config_horaire", {})
    _require_keys("config_horaire", ch, ["path"], errors)
    _require_type("config_horaire.path", ch.get("path"), str, errors, non_empty=True)

    if errors:
        raise ValueError("❌ Configuration invalide :\n- " + "\n- ".join(errors))


# -------------------------
# Helpers
# -------------------------

def _require_keys(section: str, obj: Dict[str, Any], keys: List[str], errors: List[str]) -> None:
    for k in keys:
        if k not in obj:
            errors.append(f"{section}.{k} manquant.")


def _require_type(name: str, value: Any, expected_type, errors: List[str],
                  non_empty: bool = False, positive: bool = False,
                  min_value: float | int | None = None) -> None:
    if not isinstance(value, expected_type):
        errors.append(f"{name} doit être de type {expected_type} (actuel: {type(value).__name__}).")
        return
    if non_empty and isinstance(value, str) and not value.strip():
        errors.append(f"{name} ne doit pas être vide.")
    if positive and isinstance(value, (int, float)) and value <= 0:
        errors.append(f"{name} doit être > 0.")
    if min_value is not None and isinstance(value, (int, float)) and value < min_value:
        errors.append(f"{name} doit être ≥ {min_value}.")
