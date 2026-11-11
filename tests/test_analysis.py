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
