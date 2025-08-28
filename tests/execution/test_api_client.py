# tests/execution/test_api_client.py

from signals.logic.execution import api_client as api


def test_place_order_ok(monkeypatch):
    class FakeClient:
        def post(self, name, payload, debug=False):
            assert name == "placeOrder"
            assert "symbol" in payload
            return {"ok": True, "echo": payload}

    # Retourne la classe FakeClient plutôt que d'importer la vraie
    monkeypatch.setattr(api, "import_api_client", lambda: FakeClient)

    res = api.place_order({"symbol": "CBOT_UB1!", "quantity": 1})
    assert res["status"] == "ok"
    assert res["response"]["ok"] is True

def test_place_order_import_fail(monkeypatch):
    monkeypatch.setattr(api, "import_api_client", lambda: None)
    res = api.place_order({"symbol": "X"})
    assert res["status"] == "error"
    assert "APIClient" in res["error"]
