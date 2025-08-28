# signals/monitoring/metrics.py

from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server

_metrics_started = False

# Objets de métriques (initialisés au premier start())
SIGNALS_TOTAL: Optional[Counter] = None          # labels: action, executed, schedule
API_LATENCY: Optional[Histogram] = None          # labels: endpoint, status
ORDERS_TOTAL: Optional[Counter] = None           # labels: status
EQUITY_GAUGE: Optional[Gauge] = None
DRAWDOWN_GAUGE: Optional[Gauge] = None
N_TRADES_GAUGE: Optional[Gauge] = None


def start_prometheus_server(*, enabled: bool, addr: str, port: int, namespace: str = "vwap_signal") -> None:
    global _metrics_started, SIGNALS_TOTAL, API_LATENCY, ORDERS_TOTAL, EQUITY_GAUGE, DRAWDOWN_GAUGE, N_TRADES_GAUGE
    if not enabled or _metrics_started:
        return

    start_http_server(port, addr=addr)  # expose /metrics
    # Counters / Gauges / Histograms
    SIGNALS_TOTAL = Counter(f"{namespace}_signals_total", "Total des signaux", ["action", "executed", "schedule"])
    API_LATENCY = Histogram(f"{namespace}_api_latency_seconds", "Latence des appels API", ["endpoint", "status"])
    ORDERS_TOTAL = Counter(f"{namespace}_orders_total", "Total des ordres envoyés", ["status"])
    EQUITY_GAUGE = Gauge(f"{namespace}_equity", "Equity courante")
    DRAWDOWN_GAUGE = Gauge(f"{namespace}_drawdown", "Drawdown courant")
    N_TRADES_GAUGE = Gauge(f"{namespace}_n_trades", "Nombre de trades exécutés")

    _metrics_started = True


def record_signal(action: str, executed: bool, schedule: Optional[str]) -> None:
    if SIGNALS_TOTAL is None:
        return
    SIGNALS_TOTAL.labels(action=action or "FLAT", executed=str(bool(executed)).lower(), schedule=schedule or "NA").inc()


def observe_api_latency(endpoint: str, status: str, seconds: float) -> None:
    if API_LATENCY is None:
        return
    API_LATENCY.labels(endpoint=endpoint, status=status).observe(max(0.0, seconds))


def inc_order(status: str) -> None:
    if ORDERS_TOTAL is None:
        return
    ORDERS_TOTAL.labels(status=status or "unknown").inc()


def set_perf_gauges(snapshot: Dict[str, Any]) -> None:
    if EQUITY_GAUGE is not None and "equity" in snapshot:
        EQUITY_GAUGE.set(float(snapshot["equity"]))
    if DRAWDOWN_GAUGE is not None and "drawdown" in snapshot:
        DRAWDOWN_GAUGE.set(float(snapshot["drawdown"]))
    if N_TRADES_GAUGE is not None and "n_trades" in snapshot:
        N_TRADES_GAUGE.set(float(snapshot["n_trades"]))
