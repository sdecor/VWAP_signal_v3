# tests/test_order_executor_shim.py

from signals.logic import order_executor as oe


def test_execute_signal_shim_delegates(monkeypatch):
    calls = {}

    def fake_legacy(signal, *, tracker=None, market_price=None, limit_price=None):
        calls["args"] = (signal, tracker, market_price, limit_price)
        return {"ok": True, "executed": True}

    # remplace le legacy par un fake
    import signals.logic.execution.runner as rn
    monkeypatch.setattr(rn, "execute_signal_legacy", fake_legacy)

    out = oe.execute_signal({"action": "BUY", "qty": 2}, tracker=None, market_price=115.4)
    assert out["ok"] is True
    assert calls["args"][0]["action"] == "BUY"
    assert calls["args"][2] == 115.4

def test_execute_and_track_order_shim_delegates(monkeypatch):
    calls = {}

    def fake_exec(**kwargs):
        calls["kwargs"] = kwargs
        return {"status": "ok", "executed": True}

    import signals.logic.execution.runner as rn
    monkeypatch.setattr(rn, "execute_and_track_order", fake_exec)

    out = oe.execute_and_track_order(
        symbol="CBOT_UB1!",
        side="SELL",
        qty=3.0,
        limit_price=None,
        market_price=116.0,
        tracker=None,
    )
    assert out["status"] == "ok"
    assert calls["kwargs"]["side"] == "SELL"
    assert calls["kwargs"]["qty"] == 3.0
    assert calls["kwargs"]["market_price"] == 116.0
