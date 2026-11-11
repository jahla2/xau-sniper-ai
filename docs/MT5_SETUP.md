# MT5 Expert Advisor Setup

The MT5 execution layer lives at:

`mt5/Experts/XAU_Sniper_AI.mq5`

It is **demo-first**. On a real account it will analyze but refuse to execute unless `AllowLiveTrading=true` is explicitly set.

## Behavior

1. Runs on a timer and only analyzes once per newly closed M1 candle.
2. Collects **closed candles only** from M1, M5, M15 and H1.
3. POSTs the market/account snapshot to `http://127.0.0.1:8765/analyze`.
4. If the API returns `WAIT` or `approved=false`, it does nothing.
5. If approved, it risk-sizes the position from the entry/SL distance.
6. Supports `MARKET` and `LIMIT` entries.
7. Places the final TP at the API's `take_profit_2`.
8. When price reaches TP1 (default 2R), on a hedging account it attempts to close 50% and moves the remaining SL to break-even.
9. Cancels its pending orders after a configurable number of M1 bars.
10. Blocks duplicate exposure: one bot position/order per symbol/magic number.

## MT5 installation

1. Start the Python service:

   ```bash
   uvicorn xau_sniper_ai.api:app --host 127.0.0.1 --port 8765
   ```

2. In MT5 open **Tools -> Options -> Expert Advisors**.
3. Enable **Allow WebRequest for listed URL** and add:

   `http://127.0.0.1:8765`

4. Copy `mt5/Experts/XAU_Sniper_AI.mq5` into the terminal's `MQL5/Experts/XAU-Sniper-AI/` folder.
5. Open the file in MetaEditor and compile it.
6. Attach the resulting EA to the broker's XAUUSD chart. The EA itself gathers all required timeframes, so the chart timeframe does not control the analysis.
7. Enable Algo Trading.
8. Use a **demo account first**. Keep `AllowLiveTrading=false` during development/forward testing.

## Recommended initial inputs

- `EnableAutoTrading=true`
- `AllowLiveTrading=false`
- `UseClaude=false` until the deterministic flow is stable
- `RiskPercent=0.25`
- `MinRiskReward=2.0`
- `MaxSpreadPrice=0.50`
- `MaxOpenPositions=1`
- `MaxDailyLossPct=2.0`
- `PendingExpiryBars=3`
- `Tp1RR=2.0`
- `PartialClosePercent=50`

## Important implementation details

- The API key for Claude stays in the Python service environment; the EA never contains it.
- MT5 `WebRequest` is synchronous and the URL must be allow-listed.
- MT5 does not execute `WebRequest` in Strategy Tester. Backtesting therefore uses the deterministic Python engine / replay harness rather than live API calls from the tester.
- Partial close through `CTrade.PositionClosePartial` is intended for hedging accounts. On a non-hedging account the EA skips the partial close but can still move SL to break-even.
- Trade method return values are followed by `ResultRetcode()` checks; a successful method call alone is not treated as proof of server execution.

## Not yet implemented

- Obsidian/SQLite journal persistence
- economic-news filter
- Python historical replay/backtest runner
- live-account release gate based on forward-test statistics
