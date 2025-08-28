# signals/logging/api_audit.py

import json
import os
import time
from typing import Any, Dict, Optional


class APIAuditLogger:
    """
    Écrit un log NDJSON (une ligne JSON par événement) pour chaque requête/réponse API.
    """

    def __init__(self, path: str):
        self.path = path
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)

    def log(self, record: Dict[str, Any]) -> None:
        record = dict(record)
        record.setdefault("ts_epoch_ms", int(time.time() * 1000))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
