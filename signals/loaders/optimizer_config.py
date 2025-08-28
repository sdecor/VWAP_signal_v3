# signals/loaders/optimizer_config.py
import json
import os

def load_optimizer_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[OptimizerConfig] introuvable: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
