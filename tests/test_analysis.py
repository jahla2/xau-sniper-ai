from xau_sniper_ai.analysis import _latest_fvg, _recent_sweep, analyze_market
from xau_sniper_ai.models import Action

from helpers import c, market, trend


def test_detects_bullish_fvg():
    bars = [
        c(1, 100, 101, 99, 100),
        c(2, 100, 103, 100, 102),
        c(3, 103, 105, 102, 104),
    ]
    fvg = _latest_fvg(bars)
    assert fvg is not None
    assert fvg.side == "bullish"
    assert fvg.low == 101
    assert fvg.high == 102


def test_detects_sell_side_liquidity_sweep_on_m5():
    base = [c(i * 300, 100, 101 + i * 0.01, 99, 100) for i in range(10)]
    base.append(c(11 * 300, 100, 100.5, 98.5, 99.5))
    sweep, price, ts = _recent_sweep(base, lookback=8)
    assert sweep == "sell_side"
    assert price == 98.5
    assert ts == 11 * 300


def test_waits_when_m5_confirmation_missing():
    m5 = trend(100, 16, 0.1)
    plan = analyze_market(market(m5))
    assert plan.action == Action.WAIT
    assert plan.entry is None
    assert plan.structure.timeframe == "M5"


def test_builds_long_plan_from_m5_only():
    m5 = [
        c(0,100,100.5,99.2,100.1), c(300,100.1,100.7,99.3,100.4),
        c(600,100.4,100.9,99.4,100.6), c(900,100.6,101.1,99.5,100.8),
        c(1200,100.8,101.3,99.6,101.0), c(1500,101.0,101.6,99.7,101.2),
        c(1800,101.2,101.3,99.8,100.9), c(2100,100.9,101.1,99.1,100.0),
        c(2400,100.0,100.4,98.5,99.4), c(2700,99.4,100.2,99.3,100.0),
        c(3000,100.0,100.6,99.8,100.5), c(3300,101.0,102.5,100.8,102.2),
    ]
    plan = analyze_market(market(m5, bid=102.0, ask=102.2))
    assert plan.action == Action.LONG
    assert plan.entry == 100.5
    assert plan.risk_reward == 2.0
    assert plan.take_profit_1 > plan.entry
    assert plan.take_profit_2 > plan.take_profit_1


def test_builds_short_plan_from_m5_only():
    m5 = [
        c(0,100,100.8,99.5,99.9), c(300,99.9,100.7,99.3,99.6),
        c(600,99.6,100.6,99.1,99.4), c(900,99.4,100.5,98.9,99.2),
        c(1200,99.2,100.4,98.7,99.0), c(1500,99.0,100.3,98.4,98.8),
        c(1800,98.8,100.2,98.7,99.1), c(2100,99.1,100.9,98.9,100.0),
        c(2400,100.0,101.5,99.6,100.4), c(2700,100.4,100.7,99.8,100.0),
        c(3000,100.0,100.2,99.4,99.5), c(3300,99.0,99.2,97.5,97.8),
    ]
    plan = analyze_market(market(m5, bid=97.8, ask=98.0))
    assert plan.action == Action.SHORT
    assert plan.entry == 99.5
    assert plan.risk_reward == 2.0
    assert plan.take_profit_1 < plan.entry
    assert plan.take_profit_2 < plan.take_profit_1
