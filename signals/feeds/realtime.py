# signals/feeds/realtime.py

import os
import csv
from typing import Iterator, Optional, TypedDict

from signals.utils.config_reader import load_config


class Candle(TypedDict):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


_feed_iter: Optional[Iterator[Candle]] = None
_csv_file_handle = None


def _build_csv_iterator() -> Iterator[Candle]:
    """
    Itère sur le CSV 5m configuré.
    Format attendu:
      time,open,high,low,close,volume
      2025-07-14T14:35:00Z,115.46875,115.46875,115.40625,115.40625,2233
    """
    global _csv_file_handle

    cfg = load_config()
    base = (cfg.get("data", {}) or {}).get("data_path")
    fn = (cfg.get("data", {}) or {}).get("input_5m")

    if not base or not fn:
        raise RuntimeError("Chemins data invalides (data.data_path / data.input_5m)")

    path = os.path.join(base, fn)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier CSV introuvable: {path}")

    _csv_file_handle = open(path, "r", newline="", encoding="utf-8")
    reader = csv.DictReader(_csv_file_handle)
    for row in reader:
        yield Candle(
            time=row["time"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume") or 0.0),
        )


def get_next_candle() -> Candle:
    """
    Retourne la prochaine bougie (5m) depuis le CSV configuré.
    """
    global _feed_iter, _csv_file_handle

    if _feed_iter is None:
        _feed_iter = _build_csv_iterator()

    try:
        return next(_feed_iter)
    except StopIteration:
        if _csv_file_handle:
            try:
                _csv_file_handle.close()
            except Exception:
                pass
        _feed_iter = None
        _csv_file_handle = None
        raise


def reset_feed() -> None:
    """Réinitialise l'itérateur (utile pour tests)."""
    global _feed_iter, _csv_file_handle
    _feed_iter = None
    if _csv_file_handle:
        try:
            _csv_file_handle.close()
        except Exception:
            pass
    _csv_file_handle = None
