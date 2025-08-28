# tests/logging/test_json_logger.py

import json
import logging
from pathlib import Path

from signals.logging.json_logger import setup_json_logging


def test_setup_json_logging_writes_ndjson(tmp_path):
    log_path = tmp_path / "app.ndjson"

    # active le logger JSON et logue un message simple
    logger = setup_json_logging(enabled=True, path=str(log_path), level="INFO")
    assert logger is not None

    logging.getLogger("app").info("hello", extra={"extra": {"foo": "bar", "password": "secret"}})

    # le fichier est créé et contient du JSON
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) >= 2  # une ligne pour "JSON logging enabled" + une pour "hello"

    # vérifier masquage des clés sensibles
    # Cherche la dernière ligne (celle du "hello")
    rec = json.loads(content[-1])
    assert rec["msg"] == "hello"
    assert rec.get("foo") == "bar"
    assert rec.get("password") == "***"  # masqué par le formatter
