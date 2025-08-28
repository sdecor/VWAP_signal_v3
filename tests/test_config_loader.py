# tests/test_config_loader.py

import pytest
import os
import json
from signals.loaders import config_loader

def test_load_valid_config(tmp_path):
    path = tmp_path / "valid_config.json"
    data = {"hello": "world"}
    with open(path, "w") as f:
        json.dump(data, f)

    result = config_loader.load_json_config(str(path))
    assert result["hello"] == "world"

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        config_loader.load_json_config("non_existant_file.json")

def test_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    with open(path, "w") as f:
        f.write("{ invalid json }")

    with pytest.raises(ValueError):
        config_loader.load_json_config(str(path))
