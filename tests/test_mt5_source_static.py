from pathlib import Path


EA = Path(__file__).parents[1] / "mt5" / "Experts" / "XAU_Sniper_AI.mq5"


def source() -> str:
    return EA.read_text(encoding="utf-8")


def test_ea_has_demo_live_gate_and_webrequest_contract():
    text = source()
    assert "InpAllowLiveTrading       = false" in text
    assert 'WebRequest("POST"' in text
    assert "ACCOUNT_TRADE_MODE_REAL" in text
    assert "real-account trade blocked" in text


def test_ea_has_entry_sl_tp_and_duplicate_controls():
    text = source()
    assert "trade.BuyLimit" in text
    assert "trade.SellLimit" in text
    assert "trade.Buy(" in text
    assert "trade.Sell(" in text
    assert "HasBotExposure()" in text
    assert "signal.stop_loss" in text
    assert "signal.take_profit_2" in text


def test_ea_has_tp1_partial_close_break_even_and_stale_order_cancel():
    text = source()
    assert "PositionClosePartial" in text
    assert "PositionModify" in text
    assert "InpTp1RR" in text
    assert "CancelStalePendingOrders" in text
    assert "trade.OrderDelete" in text
