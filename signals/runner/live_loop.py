# signals/runner/live_loop.py

import os
import json
import logging
from datetime import datetime

# ✅ Exposé pour les tests (monkeypatch possible)
CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", "checkpoint.json")


def save_checkpoint(timestamp: str, path: str | None = None) -> None:
    """
    Sauvegarde un checkpoint JSON avec le dernier timestamp traité.
    """
    cp_path = path or CHECKPOINT_PATH
    checkpoint = {"last_timestamp": timestamp, "status": "OK"}
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f)
    logging.info(f"[Checkpoint] Sauvegardé : {timestamp} -> {cp_path}")


def load_checkpoint(path: str | None = None) -> str | None:
    """
    Charge le dernier timestamp depuis le checkpoint JSON, si présent.
    """
    cp_path = path or CHECKPOINT_PATH
    if os.path.exists(cp_path):
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            ts = checkpoint.get("last_timestamp")
            logging.info(f"[Checkpoint] Reprise depuis {ts} ({cp_path})")
            return ts
        except Exception as e:
            logging.warning(f"[Checkpoint] Échec de lecture {cp_path} : {e}")
    return None


def run_live_loop():
    logging.info("🚀 Boucle live démarrée")
    last_processed = load_checkpoint()

    while True:
        try:
            # TODO: implémente tes fonctions de flux réel
            next_candle = get_next_candle()  # doit renvoyer {"timestamp": "...", ...}
            timestamp = next_candle["timestamp"]

            if last_processed and timestamp <= last_processed:
                continue

            process_signal(next_candle)  # ta logique métier

            save_checkpoint(timestamp)
            last_processed = timestamp

        except KeyboardInterrupt:
            logging.info("🛑 Arrêt manuel détecté")
            break
        except Exception as e:
            logging.exception(f"[LiveLoop] Erreur dans la boucle : {e}")
            break
