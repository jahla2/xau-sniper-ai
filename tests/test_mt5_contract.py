from fastapi.testclient import TestClient

from xau_sniper_ai.api import app

from helpers import trend

client = TestClient(app)


def _payload():
    bars = trend(100, 24, 0.1)
    return {
        "market": {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "bid": 102.2,
            "ask": 102.5,
            "spread": 0.3,
            "m5": [x.model_dump() for x in bars],
        },
        "policy": {
            "max_risk_pct": 0.25,
            "min_rr": 2.0,
            "max_spread": 0.5,
            "max_open_positions": 1,
            "max_daily_loss_pct": 2.0,
        },
        "risk": {"balance": 1000.0, "open_positions": 0, "daily_pnl": 0.0},
        "use_claude": False,
    }


def test_mt5_m5_request_contract_is_accepted():
    response = client.post("/analyze", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "XAUUSD_M5_SMC_ICT"
    assert isinstance(body["approved"], bool)
    assert "summary" in body
    plan = body["plan"]
    for key in ("action", "confidence", "entry_type", "entry", "stop_loss", "take_profit_1", "take_profit_2"):
        assert key in plan


def test_mt5_contract_remains_blocked_when_waiting():
    payload = _payload()
    payload["risk"]["open_positions"] = 1
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    assert response.json()["approved"] is False
