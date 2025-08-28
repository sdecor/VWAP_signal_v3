# signals/runner/live_loop.py

import json
import os
from typing import Optional

# Shim legacy pour compatibilité tests
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "checkpoint.json")


def save_checkpoint(ts_iso: str, path: Optional[str] = None) -> None:
    """
    Sauvegarde un timestamp ISO dans le fichier de checkpoint (JSON minimal).
    """
    p = path or CHECKPOINT_PATH
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"last_timestamp": ts_iso}, f)


def load_checkpoint(path: Optional[str] = None) -> Optional[str]:
    """
    Lit le timestamp ISO depuis le checkpoint, ou None si absent/invalide.
    """
    p = path or CHECKPOINT_PATH
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("last_timestamp")
        return str(ts) if ts else None
    except Exception:
        return None
