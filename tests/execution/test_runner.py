# tests/execution/test_runner.py

from dataclasses import dataclass

from signals.logic.execution import runner as rn


@dataclass
class DummyTracker:
    calls: list

    def on_fill(self, *, price: float, qty: float, side: str):
        self.calls.append((price, qty, side))


def test_execute_and_track_order_dry_run(monkeypatch):
    # force dry-run
    from signals.logic.execution import payload as pl
    monkeypatch.setattr(pl, "is_dry_run", lambda: True)

    tracker = DummyTracker(calls=[])
    res = rn.execute_and_track_order(
        symbol="CBOT_UB1!",
        side="BUY",
        qty=2.0,
        limit_price=None,
        market_price=115.5,
        tracker=tracker,
    )
    assert res["status"] == "dry_run"
    assert res["executed"] is True
    assert tracker.calls == [(115.5, 2.0, "BUY")]

def test_execute_and_track_order_prod_ok(monkeypatch):
    # force prod
    from signals.logic.execution import payload as pl
    monkeypatch.setattr(pl, "is_dry_run", lambda: False)

    # API OK
    from signals.logic.execution import api_client as api
    monkeypatch.setattr(api, "place_order", lambda payload: {"status": "ok", "response": {"id": "X"}})

    tracker = DummyTracker(calls=[])
    res = rn.execute_and_track_order(
        symbol="CBOT_UB1!",
        side="SELL",
        qty=1.0,
        limit_price=None,
        market_price=120.0,
        tracker=tracker,
    )
    assert res["status"] == "ok"
    assert res["executed"] is True
    # fallback: fill @ market_price
    assert tracker.calls == [(120.0, 1.0, "SELL")]

def test_execute_and_track_order_prod_error(monkeypatch):
    # force prod
    from signals.logic.execution import payload as pl
    monkeypatch.setattr(pl, "is_dry_run", lambda: False)

    # API error
    from signals.logic.execution import api_client as api
    monkeypatch.setattr(api, "place_order", lambda payload: {"status": "error", "error": "down"})

    tracker = DummyTracker(calls=[])
    res = rn.execute_and_track_order(
        symbol="CBOT_UB1!",
        side="BUY",
        qty=1.0,
        limit_price=None,
        market_price=119.0,
        tracker=tracker,
    )
    assert res["status"] == "error"
    assert res["executed"] is False
    assert tracker.calls == []
