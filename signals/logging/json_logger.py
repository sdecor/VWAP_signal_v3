# signals/logging/json_logger.py

import json
import logging
import os
from typing import Any, Dict, Optional

SENSITIVE_KEYS = {"accountId", "apiKey", "password", "secret", "token"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        # Extra transmis via logger.info(..., extra={"extra": {...}})
        if hasattr(record, "extra") and isinstance(record.extra, dict):  # type: ignore[attr-defined]
            payload.update(self._mask(record.extra))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

    def _mask(self, d: Dict[str, Any]) -> Dict[str, Any]:
        masked = {}
        for k, v in d.items():
            masked[k] = "***" if k in SENSITIVE_KEYS else v
        return masked


def setup_json_logging(
    *,
    enabled: bool,
    path: str,
    level: str = "INFO",
    also_console: bool = False,
) -> Optional[logging.Logger]:
    """
    Configure le root logger pour écrire en NDJSON (ELK/Loki friendly).
    - Garantit la création du fichier (double touch) ou lève une exception explicite si impossible.
    - N'enlève que le FileHandler pointant vers 'path' (pas les autres).
    - Optionnel: ajoute un StreamHandler (console).

    Args:
        enabled: active/désactive le logging JSON.
        path: chemin du fichier NDJSON.
        level: niveau ("DEBUG" / "INFO" / "WARNING" / "ERROR").
        also_console: si True, ajoute un StreamHandler sur la console.

    Returns:
        Logger "app" si activé, sinon None.
    """
    if not enabled:
        return None

    path = os.fspath(path)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    # Touch initial — si ça échoue, on le signale clairement
    try:
        with open(path, "a", encoding="utf-8"):
            pass
    except Exception:
        logging.error("Impossible de créer le fichier de log JSON (touch initial): %s", path, exc_info=True)
        raise

    formatter = JsonFormatter()

    # Configure FileHandler NDJSON
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    # Ne retire QUE le FileHandler qui cible ce même fichier (évite doublons sans casser d'autres fichiers)
    root.handlers = [
        h
        for h in root.handlers
        if not (isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == path)
    ]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(file_handler)

    # Optionnel: handler console
    if also_console:
        console = logging.StreamHandler()
        # Tu peux garder JsonFormatter ou un format humain: logging.Formatter("%(levelname)s | %(message)s")
        console.setFormatter(formatter)
        root.addHandler(console)

    # Petit logger d’app
    logger = logging.getLogger("app")
    logger.info("JSON logging enabled", extra={"extra": {"path": path, "level": level}})

    # Flush + touch final — garantit l’existence même si interception de logs
    try:
        file_handler.flush()
        with open(path, "a", encoding="utf-8"):
            pass
    except Exception:
        logging.error("Impossible de (re)créer le fichier de log JSON (touch final): %s", path, exc_info=True)
        raise

    return logger
