from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Action(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


class Candle(BaseModel):
    ts: int = Field(description="Unix timestamp in seconds")
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Candle":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be >= open/close/low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be <= open/close/high")
        return self


class MarketSnapshot(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: Literal["M5"] = "M5"
    bid: float
    ask: float
    spread: float | None = None
    m5: list[Candle]

    @model_validator(mode="after")
    def validate_market(self) -> "MarketSnapshot":
        if self.ask < self.bid:
            raise ValueError("ask must be >= bid")
        normalized = "".join(ch for ch in self.symbol.upper() if ch.isalnum())
        if not normalized.startswith("XAUUSD"):
            raise ValueError("XAU Sniper AI only accepts gold / XAUUSD symbols")
        if self.spread is None:
            self.spread = self.ask - self.bid
        return self


class FVG(BaseModel):
    side: Literal["bullish", "bearish"]
    low: float
    high: float
    created_at: int

    @property
    def midpoint(self) -> float:
        return round((self.low + self.high) / 2, 2)


class StructureState(BaseModel):
    timeframe: Literal["M5"] = "M5"
    trend: Literal["bullish", "bearish", "neutral"]
    liquidity_sweep: Literal["sell_side", "buy_side", "none"]
    choch: Literal["bullish", "bearish", "none"]
    bos: Literal["bullish", "bearish", "none"]
    fvg: FVG | None = None
    last_swing_high: float | None = None
    last_swing_low: float | None = None
    sweep_price: float | None = None
    sweep_ts: int | None = None


class TradePlan(BaseModel):
    action: Action
    confidence: int = Field(ge=0, le=100)
    entry_type: Literal["LIMIT", "MARKET", "NONE"]
    entry: float | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    risk_reward: float | None = None
    reason: list[str] = Field(default_factory=list)
    invalidation: str | None = None
    structure: StructureState


class RiskPolicy(BaseModel):
    max_risk_pct: float = 0.5
    min_rr: float = 2.0
    max_spread: float = 0.50
    max_open_positions: int = 1
    max_daily_loss_pct: float = 2.0


class RiskContext(BaseModel):
    balance: float = 1000.0
    open_positions: int = 0
    daily_pnl: float = 0.0


class AnalyzeRequest(BaseModel):
    market: MarketSnapshot
    policy: RiskPolicy = Field(default_factory=RiskPolicy)
    risk: RiskContext = Field(default_factory=RiskContext)
    use_claude: bool = False


class AnalyzeResponse(BaseModel):
    strategy: str = "XAUUSD_M5_SMC_ICT"
    summary: str
    plan: TradePlan
    approved: bool
    rejection_reasons: list[str] = Field(default_factory=list)
    ai_review: dict | None = None
