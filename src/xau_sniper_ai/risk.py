from __future__ import annotations

from .models import Action, MarketSnapshot, RiskContext, RiskPolicy, TradePlan


def validate_plan(plan: TradePlan, market: MarketSnapshot, policy: RiskPolicy, risk: RiskContext) -> list[str]:
    reasons: list[str] = []
    if plan.action == Action.WAIT:
        return ["strategy returned WAIT"]
    if market.spread is not None and market.spread > policy.max_spread:
        reasons.append(f"spread {market.spread:.2f} exceeds max {policy.max_spread:.2f}")
    if risk.open_positions >= policy.max_open_positions:
        reasons.append("maximum open positions reached")
    if risk.balance <= 0:
        reasons.append("invalid account balance")
    elif risk.daily_pnl < -(risk.balance * policy.max_daily_loss_pct / 100):
        reasons.append("daily loss limit reached")
    if plan.risk_reward is None or plan.risk_reward < policy.min_rr:
        reasons.append("risk/reward below policy minimum")
    if None in (plan.entry, plan.stop_loss, plan.take_profit_1):
        reasons.append("trade plan is missing entry/SL/TP")
    return reasons


def risk_amount(balance: float, max_risk_pct: float) -> float:
    return round(balance * max_risk_pct / 100, 2)
