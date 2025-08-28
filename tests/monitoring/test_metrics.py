# tests/monitoring/test_metrics.py

from importlib import reload

import types
import pytest

import signals.monitoring.metrics as metrics


@pytest.fixture(autouse=True)
def reset_metrics(monkeypatch):
    # reload pour retomber à un état propre (_metrics_started=False, objets None)
    reload(metrics)

    # monkeypatch pour éviter de démarrer un vrai serveur HTTP
    monkeypatch.setattr(metrics, "start_http_server", lambda port, addr="0.0.0.0": None)


def test_start_and_record_metrics():
    # Démarre les métriques (création des objets)
    metrics.start_prometheus_server(enabled=True, addr="127.0.0.1", port=9999, namespace="test_ns")

    assert metrics.SIGNALS_TOTAL is not None
    assert metrics.API_LATENCY is not None
    assert metrics.ORDERS_TOTAL is not None
    assert metrics.EQUITY_GAUGE is not None
    assert metrics.DRAWDOWN_GAUGE is not None
    assert metrics.N_TRADES_GAUGE is not None

    # Enregistrements de base (ne doivent pas exploser)
    metrics.record_signal("BUY", True, "ASIAN02")
    metrics.observe_api_latency("placeOrder", "200", 0.123)
    metrics.inc_order("ok")
    metrics.set_perf_gauges({"equity": 10000.0, "drawdown": 42.0, "n_trades": 7})

    # Si on rappelle start(), ça ne redémarre pas (idempotent)
    metrics.start_prometheus_server(enabled=True, addr="127.0.0.1", port=9999, namespace="test_ns")
    # Toujours les mêmes objets
    assert metrics.SIGNALS_TOTAL is not None
