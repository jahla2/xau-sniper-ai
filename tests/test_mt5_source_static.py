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


def test_ea_is_gold_m5_only_and_analyzes_realtime():
    text = source()
    assert "IsGoldSymbol()" in text
    assert "_Period != PERIOD_M5" in text
    assert 'payload += "\"timeframe\":\"M5\",";' in text
    assert "PERIOD_M1" not in text
    assert "PERIOD_M15" not in text
    assert "PERIOD_H1" not in text
    assert "AnalyzeAndMaybeTrade(new_closed_m5)" in text
    assert "Only a newly closed M5 candle may execute" in text


def test_ea_has_visible_chart_dashboard():
    text = source()
    assert "UpdateDashboard" in text
    assert "XAU SNIPER AI | GOLD M5 ONLY" in text
    assert "M5 Trend:" in text
    assert "Sweep:" in text
    assert "CHoCH:" in text
    assert "BOS:" in text
    assert "FVG:" in text
    assert "Reason:" in text


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
