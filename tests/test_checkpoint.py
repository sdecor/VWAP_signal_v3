# tests/test_checkpoint.py

import os
import json
from signals.runner import live_loop

def test_save_and_load_checkpoint(tmp_path, monkeypatch):
    test_path = tmp_path / "checkpoint.json"

    monkeypatch.setattr(live_loop, "CHECKPOINT_PATH", str(test_path))

    live_loop.save_checkpoint("2025-08-28T14:25:00")
    assert test_path.exists()

    timestamp = live_loop.load_checkpoint()
    assert timestamp == "2025-08-28T14:25:00"
