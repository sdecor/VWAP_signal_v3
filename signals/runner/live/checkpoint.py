import os, json, logging
from typing import Optional

CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", "checkpoint.json")

def save_checkpoint(timestamp: str, path: Optional[str] = None) -> None:
    cp = path or CHECKPOINT_PATH
    os.makedirs(os.path.dirname(cp) or ".", exist_ok=True)
    with open(cp, "w", encoding="utf-8") as f:
        json.dump({"last_timestamp": timestamp, "status": "OK"}, f)
    logging.info(f"[Checkpoint] {timestamp} -> {cp}")

def load_checkpoint(path: Optional[str] = None) -> Optional[str]:
    cp = path or CHECKPOINT_PATH
    try:
        with open(cp, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("last_timestamp")
    except Exception as e:
        logging.warning(f"[Checkpoint] lecture échouée {cp}: {e}")
        return None
