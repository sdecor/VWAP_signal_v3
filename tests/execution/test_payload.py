# tests/execution/test_payload.py

import types
import pytest

from signals.logic.execution import payload as pl


@pytest.fixture(autouse=True)
def patch_config_getters(monkeypatch):
    # Mock des getters appelés par payload
    import signals.loaders.config_loader as cfg
    monkeypatch.setattr(cfg, "get_symbol", lambda: "CBOT_UB1!")
    monkeypatch.setattr(cfg, "get_order_type", lambda: "market")
    monkeypatch.setattr(cfg, "get_time_in_force", lambda: "DAY")
    monkeypatch.setattr(cfg, "get_dry_run_mode", lambda: True)
    monkeypatch.setattr(cfg, "get_default_lots", lambda: 3)

    # Mock ACCOUNT_ID
    import signals.utils.env_loader as env
    monkeypatch.setattr(env, "ACCOUNT_ID", "ACC-123")

def test_extract_side_and_qty_from_signal_key():
    side, qty = pl.extract_side_and_qty({"signal": "BUY", "qty": 5})
    assert side == "BUY"
    assert qty == 5.0

def test_extract_side_and_qty_from_action_key_uses_default_lots():
    side, qty = pl.extract_side_and_qty({"action": "SELL"})
    assert side == "SELL"
    assert qty == 3.0  # mock get_default_lots

def test_extract_side_invalid_raises():
    with pytest.raises(ValueError):
        pl.extract_side_and_qty({"signal": "HOLD"})

def test_build_order_payload_fields():
    payload = pl.build_order_payload({"signal": "BUY", "qty": 2})
    assert payload["accountId"] == "ACC-123"
    assert payload["symbol"] == "CBOT_UB1!"
    assert payload["side"] == "BUY"
    assert payload["orderType"] == "market"
    assert payload["timeInForce"] == "DAY"
    assert payload["quantity"] == 2
