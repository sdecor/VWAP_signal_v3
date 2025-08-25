import os
import yaml
from dotenv import load_dotenv

# Charge .env
load_dotenv()

# ----- Variables sensibles -----
BASE_URL = os.getenv("TOPSTEPX_BASE_URL")
if not BASE_URL:
    raise RuntimeError("TOPSTEPX_BASE_URL manquant dans .env")

USERNAME = os.getenv("TOPSTEPX_USERNAME")
API_KEY = os.getenv("TOPSTEPX_API_KEY")
ACCOUNT_ID = os.getenv("TOPSTEPX_ACCOUNT_ID")  # optionnel

# ----- Chargement YAML -----
def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return _normalize_config(cfg)

def _normalize_config(cfg: dict) -> dict:
    """
    Normalise la structure:
    - supporte ancien schéma 'api_endpoints' -> migré vers cfg['api']['endpoints']
    - garantit la présence d'un dict endpoints
    """
    api = cfg.get("api") or {}

    if "api_endpoints" in cfg:
        api["endpoints"] = cfg["api_endpoints"]
    else:
        api.setdefault("endpoints", {})

    cfg["api"] = api
    cfg.setdefault("logging", {"enable_api_logging": False, "dry_run_mode": False})
    return cfg

CONFIG = load_config()

def debug_dump_config():
    """Retourne un dict lisible des infos utiles pour debug global."""
    return {
        "env": {
            "TOPSTEPX_BASE_URL": BASE_URL,
            "TOPSTEPX_USERNAME": USERNAME,
            "TOPSTEPX_ACCOUNT_ID": ACCOUNT_ID,
            "TOPSTEPX_API_KEY_present": bool(API_KEY),
        },
        "config_keys": list(CONFIG.keys()),
        "api_keys": list((CONFIG.get("api") or {}).keys()),
        "endpoints_keys": list(((CONFIG.get("api") or {}).get("endpoints") or {}).keys()),
        "logging": CONFIG.get("logging"),
    }
