# tests/test_api_client.py

import pytest
from signals.api import client
import requests

def test_safe_post_success(monkeypatch):
    class MockResponse:
        def raise_for_status(self): pass
        status_code = 200
        def json(self): return {"ok": True}

    def mock_post(url, json, headers=None):
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    result = client.safe_post("http://fake.url", {"data": 1})
    assert result.status_code == 200

def test_safe_post_failure(monkeypatch):
    def mock_post(url, json, headers=None):
        raise requests.exceptions.RequestException("Erreur API")

    monkeypatch.setattr(requests, "post", mock_post)

    with pytest.raises(Exception, match="Échec API"):
        client.safe_post("http://fail.url", {"data": 1})
