from fastapi.testclient import TestClient

from xau_sniper_ai.api import app

from helpers import trend

client = TestClient(app)


def candle_dict(c):
    return c.model_dump()


def test_health_reports_m5_strategy():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["strategy"] == "XAUUSD_M5_SMC_ICT"


def test_analyze_returns_wait_for_unconfirmed_m5_market():
    bars = trend(100, 16, 0.1)
    payload = {
        "market": {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "bid": 101.5,
            "ask": 101.7,
            "m5": [candle_dict(c) for c in bars],
        }
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "XAUUSD_M5_SMC_ICT"
    assert body["plan"]["action"] == "WAIT"
    assert body["plan"]["structure"]["timeframe"] == "M5"
    assert body["approved"] is False
    assert "M5 WAIT" in body["summary"]


def test_rejects_non_gold_symbol():
    bars = trend(100, 16, 0.1)
    payload = {
        "market": {
            "symbol": "EURUSD",
            "timeframe": "M5",
            "bid": 1.1,
            "ask": 1.1002,
            "m5": [candle_dict(c) for c in bars],
        }
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 422


def test_rejects_non_m5_timeframe():
    bars = trend(100, 16, 0.1)
    payload = {
        "market": {
            "symbol": "XAUUSD",
            "timeframe": "M1",
            "bid": 100,
            "ask": 100.2,
            "m5": [candle_dict(c) for c in bars],
        }
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 422
