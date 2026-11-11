from fastapi.testclient import TestClient

from xau_sniper_ai.api import app

from helpers import trend

client = TestClient(app)


def candle_dict(c):
    return c.model_dump()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_returns_wait_for_unconfirmed_market():
    bars = trend(100, 16, 0.1)
    payload = {
        "market": {
            "symbol": "XAUUSD",
            "bid": 101.5,
            "ask": 101.7,
            "m1": [candle_dict(c) for c in bars],
            "m5": [candle_dict(c) for c in bars],
            "m15": [candle_dict(c) for c in bars],
            "h1": [candle_dict(c) for c in bars],
        }
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["action"] == "WAIT"
    assert body["approved"] is False
    assert "strategy returned WAIT" in body["rejection_reasons"]
