from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .models import Action, Candle, FVG, MarketSnapshot, StructureState, TradePlan


@dataclass(frozen=True)
class Pivot:
    side: str
    price: float
    index: int


def _pivot_highs(candles: list[Candle], width: int = 2) -> list[Pivot]:
    out: list[Pivot] = []
    for i in range(width, len(candles) - width):
        h = candles[i].high
        if all(h > candles[j].high for j in range(i - width, i)) and all(
            h >= candles[j].high for j in range(i + 1, i + width + 1)
        ):
            out.append(Pivot("high", h, i))
    return out


def _pivot_lows(candles: list[Candle], width: int = 2) -> list[Pivot]:
    out: list[Pivot] = []
    for i in range(width, len(candles) - width):
        low = candles[i].low
        if all(low < candles[j].low for j in range(i - width, i)) and all(
            low <= candles[j].low for j in range(i + 1, i + width + 1)
        ):
            out.append(Pivot("low", low, i))
    return out


def _trend_bias(candles: list[Candle]) -> str:
    if len(candles) < 8:
        return "neutral"
    recent = candles[-8:]
    first = mean(c.close for c in recent[:3])
    last = mean(c.close for c in recent[-3:])
    highs = _pivot_highs(candles)
    lows = _pivot_lows(candles)
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1].price > highs[-2].price
        hl = lows[-1].price > lows[-2].price
        lh = highs[-1].price < highs[-2].price
        ll = lows[-1].price < lows[-2].price
        if hh and hl:
            return "bullish"
        if lh and ll:
            return "bearish"
    delta = last - first
    if delta > 0.8:
        return "bullish"
    if delta < -0.8:
        return "bearish"
    return "neutral"


def _latest_fvg(candles: list[Candle], not_before_ts: int | None = None) -> FVG | None:
    for i in range(len(candles) - 1, 1, -1):
        left, right = candles[i - 2], candles[i]
        if not_before_ts is not None and right.ts < not_before_ts:
            continue
        if left.high < right.low:
            return FVG(side="bullish", low=left.high, high=right.low, created_at=right.ts)
        if left.low > right.high:
            return FVG(side="bearish", low=right.high, high=left.low, created_at=right.ts)
    return None


def _recent_sweep(candles: list[Candle], lookback: int = 8) -> tuple[str, float | None, int | None]:
    if len(candles) < lookback + 2:
        return "none", None, None
    start = max(lookback, len(candles) - 4)
    for i in range(len(candles) - 1, start - 1, -1):
        reference = candles[i - lookback : i]
        c = candles[i]
        prior_high = max(x.high for x in reference)
        prior_low = min(x.low for x in reference)
        if c.low < prior_low and c.close > prior_low:
            return "sell_side", c.low, c.ts
        if c.high > prior_high and c.close < prior_high:
            return "buy_side", c.high, c.ts
    return "none", None, None


def _structure_break(candles: list[Candle]) -> tuple[str, str, float | None, float | None]:
    highs = _pivot_highs(candles)
    lows = _pivot_lows(candles)
    last_high = highs[-1].price if highs else None
    last_low = lows[-1].price if lows else None
    if len(candles) < 2:
        return "none", "none", last_high, last_low

    close = candles[-1].close
    previous_bias = _trend_bias(candles[:-1])
    bos = "none"
    choch = "none"
    if last_high is not None and close > last_high:
        bos = "bullish"
        if previous_bias == "bearish":
            choch = "bullish"
    elif last_low is not None and close < last_low:
        bos = "bearish"
        if previous_bias == "bullish":
            choch = "bearish"
    return choch, bos, last_high, last_low


def analyze_market(market: MarketSnapshot) -> TradePlan:
    candles = market.m5
    if len(candles) < 12:
        structure = StructureState(
            trend="neutral", liquidity_sweep="none", choch="none", bos="none"
        )
        return _wait(structure, "insufficient M5 candle history")

    trend = _trend_bias(candles)
    sweep, sweep_price, sweep_ts = _recent_sweep(candles)
    choch, bos, swing_high, swing_low = _structure_break(candles)
    fvg = _latest_fvg(candles, not_before_ts=sweep_ts)

    structure = StructureState(
        trend=trend,
        liquidity_sweep=sweep,
        choch=choch,
        bos=bos,
        fvg=fvg,
        last_swing_high=swing_high,
        last_swing_low=swing_low,
        sweep_price=sweep_price,
        sweep_ts=sweep_ts,
    )

    bullish_structure = bos == "bullish" or choch == "bullish"
    bearish_structure = bos == "bearish" or choch == "bearish"
    long_context_ok = trend != "bearish" or choch == "bullish"
    short_context_ok = trend != "bullish" or choch == "bearish"
    buffer = max(0.10, float(market.spread or 0.0))

    if sweep == "sell_side" and bullish_structure and fvg and fvg.side == "bullish" and long_context_ok:
        entry = fvg.midpoint
        invalidation = min(x for x in [sweep_price, swing_low, fvg.low] if x is not None) - buffer
        risk = entry - invalidation
        if risk <= 0:
            return _wait(structure, "bullish setup had invalid stop geometry")
        tp1 = entry + 2 * risk
        tp2 = entry + 3 * risk
        return TradePlan(
            action=Action.LONG,
            confidence=82 if trend == "bullish" else 76,
            entry_type="LIMIT",
            entry=round(entry, 2),
            stop_loss=round(invalidation, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            risk_reward=2.0,
            invalidation=f"M5 close below {round(invalidation, 2)}",
            reason=[
                "M5 sell-side liquidity sweep confirmed",
                "M5 bullish CHoCH/BOS confirmed",
                "fresh bullish M5 FVG available for retest",
                "primary target is 2R; optional runner targets 3R",
            ],
            structure=structure,
        )

    if sweep == "buy_side" and bearish_structure and fvg and fvg.side == "bearish" and short_context_ok:
        entry = fvg.midpoint
        invalidation = max(x for x in [sweep_price, swing_high, fvg.high] if x is not None) + buffer
        risk = invalidation - entry
        if risk <= 0:
            return _wait(structure, "bearish setup had invalid stop geometry")
        tp1 = entry - 2 * risk
        tp2 = entry - 3 * risk
        return TradePlan(
            action=Action.SHORT,
            confidence=82 if trend == "bearish" else 76,
            entry_type="LIMIT",
            entry=round(entry, 2),
            stop_loss=round(invalidation, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            risk_reward=2.0,
            invalidation=f"M5 close above {round(invalidation, 2)}",
            reason=[
                "M5 buy-side liquidity sweep confirmed",
                "M5 bearish CHoCH/BOS confirmed",
                "fresh bearish M5 FVG available for retest",
                "primary target is 2R; optional runner targets 3R",
            ],
            structure=structure,
        )

    missing: list[str] = []
    if sweep == "none":
        missing.append("no confirmed M5 liquidity sweep")
    if bos == "none" and choch == "none":
        missing.append("no confirmed M5 CHoCH/BOS")
    if fvg is None:
        missing.append("no fresh M5 FVG after the sweep")
    if not missing:
        missing.append("M5 setup components are not directionally aligned")
    return _wait(structure, *missing)


def summarize_plan(plan: TradePlan) -> str:
    s = plan.structure
    fvg = "none" if s.fvg is None else f"{s.fvg.side} {s.fvg.low:.2f}-{s.fvg.high:.2f}"
    reasons = "; ".join(plan.reason)
    if plan.action == Action.WAIT:
        return (
            f"M5 WAIT | trend={s.trend} sweep={s.liquidity_sweep} "
            f"CHoCH={s.choch} BOS={s.bos} FVG={fvg} | {reasons}"
        )
    return (
        f"M5 {plan.action.value} | trend={s.trend} sweep={s.liquidity_sweep} "
        f"CHoCH={s.choch} BOS={s.bos} FVG={fvg} | "
        f"entry={plan.entry:.2f} SL={plan.stop_loss:.2f} "
        f"TP1={plan.take_profit_1:.2f} TP2={plan.take_profit_2:.2f}"
    )


def _wait(structure: StructureState, *reasons: str) -> TradePlan:
    return TradePlan(
        action=Action.WAIT,
        confidence=25,
        entry_type="NONE",
        reason=list(reasons),
        structure=structure,
    )
