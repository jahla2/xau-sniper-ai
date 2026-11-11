from xau_sniper_ai.analysis import _latest_fvg, _recent_sweep, analyze_market
from xau_sniper_ai.models import Action

from helpers import c, neutral_market, trend


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


def test_detects_sell_side_liquidity_sweep():
    base = [c(i, 100, 101 + i * 0.01, 99, 100) for i in range(10)]
    base.append(c(11, 100, 100.5, 98.5, 99.5))
    sweep, price = _recent_sweep(base, lookback=8)
    assert sweep == "sell_side"
    assert price == 98.5


def test_waits_when_confirmation_missing():
    m1 = trend(100, 16, 0.1)
    market = neutral_market(m1)
    plan = analyze_market(market)
    assert plan.action == Action.WAIT
    assert plan.entry is None


def test_builds_long_plan_after_sell_side_sweep_bos_and_fvg():
    m1 = [
        c(0,100,100.5,99.2,100.1), c(1,100.1,100.7,99.3,100.4),
        c(2,100.4,100.9,99.4,100.6), c(3,100.6,101.1,99.5,100.8),
        c(4,100.8,101.3,99.6,101.0), c(5,101.0,101.6,99.7,101.2),
        c(6,101.2,101.3,99.8,100.9), c(7,100.9,101.1,99.1,100.0),
        c(8,100.0,100.4,98.5,99.4), c(9,99.4,100.2,99.3,100.0),
        c(10,100.0,100.6,99.8,100.5), c(11,101.0,102.5,100.8,102.2),
    ]
    htf = trend(90, 12, 0.4)
    market = neutral_market(m1, bid=102.0, ask=102.2)
    market.m5 = htf
    market.m15 = htf
    market.h1 = htf
    plan = analyze_market(market)
    assert plan.action == Action.LONG
    assert plan.entry == 100.5
    assert plan.stop_loss == 98.4
    assert plan.risk_reward == 2.0


def test_builds_short_plan_after_buy_side_sweep_bos_and_fvg():
    m1 = [
        c(0,100,100.8,99.5,99.9), c(1,99.9,100.7,99.3,99.6),
        c(2,99.6,100.6,99.1,99.4), c(3,99.4,100.5,98.9,99.2),
        c(4,99.2,100.4,98.7,99.0), c(5,99.0,100.3,98.4,98.8),
        c(6,98.8,100.2,98.7,99.1), c(7,99.1,100.9,98.9,100.0),
        c(8,100.0,101.5,99.6,100.4), c(9,100.4,100.7,99.8,100.0),
        c(10,100.0,100.2,99.4,99.5), c(11,99.0,99.2,97.5,97.8),
    ]
    htf = trend(110, 12, -0.4)
    market = neutral_market(m1, bid=97.8, ask=98.0)
    market.m5 = htf
    market.m15 = htf
    market.h1 = htf
    plan = analyze_market(market)
    assert plan.action == Action.SHORT
    assert plan.entry == 99.5
    assert plan.stop_loss == 101.6
    assert plan.risk_reward == 2.0
