from xau_sniper_ai.models import Action, FVG, MarketSnapshot, RiskContext, RiskPolicy, StructureState, TradePlan
from xau_sniper_ai.risk import risk_amount, validate_plan

from helpers import trend


def plan() -> TradePlan:
    structure = StructureState(
        htf_bias="bullish",
        liquidity_sweep="sell_side",
        choch="bullish",
        bos="bullish",
        fvg=FVG(side="bullish", low=100, high=101, created_at=1),
    )
    return TradePlan(
        action=Action.LONG,
        confidence=80,
        entry_type="LIMIT",
        entry=100.5,
        stop_loss=99.5,
        take_profit_1=102.5,
        take_profit_2=103.5,
        risk_reward=2.0,
        structure=structure,
    )


def market(spread: float) -> MarketSnapshot:
    bars = trend(90, 12, 0.4)
    return MarketSnapshot(symbol="XAUUSD", bid=100, ask=100+spread, m1=bars, m5=bars, m15=bars, h1=bars)


def test_rejects_wide_spread():
    reasons = validate_plan(plan(), market(0.8), RiskPolicy(max_spread=0.5), RiskContext())
    assert any("spread" in reason for reason in reasons)


def test_rejects_second_position():
    reasons = validate_plan(plan(), market(0.2), RiskPolicy(max_open_positions=1), RiskContext(open_positions=1))
    assert "maximum open positions reached" in reasons


def test_risk_amount():
    assert risk_amount(1000, 0.5) == 5.0
