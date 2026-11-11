# MT5 Setup — XAUUSD M5 Only

The EA is:

`mt5/Experts/XAU_Sniper_AI.mq5`

## Required chart

Attach the EA only to a **Gold / XAUUSD M5 chart**. The EA refuses initialization on other instruments or timeframes.

## Realtime behavior

- Every `InpPollSeconds` (default 5 seconds), the EA sends:
  - current XAUUSD bid/ask/spread
  - recent **closed M5 candles only**
  - account balance/open-position/daily-P&L context
- Python analyzes and logs the M5 structure every poll.
- The chart dashboard is refreshed every poll.
- A fresh order is allowed only when a **new M5 candle closes** and the analysis is approved.

This keeps monitoring realtime while avoiding entries based on an unfinished/repainting M5 candle.

## Strategy gate

A trade requires the M5 setup to align:

`liquidity sweep -> CHoCH/BOS -> fresh FVG -> retest entry`

If confirmation is missing, the answer is `WAIT`.

SL is placed beyond the sweep/invalidation area. TP1 is 2R; the optional remaining runner targets 3R.

## Install

1. Start the API:
   ```powershell
   cd E:\Project\TRADE\xau-sniper-ai
   .venv\Scripts\activate
   python -m uvicorn xau_sniper_ai.api:app --host 127.0.0.1 --port 8765
   ```
2. MT5 -> **Tools -> Options -> Expert Advisors**.
3. Enable **Allow WebRequest for listed URL** and add:
   `http://127.0.0.1:8765`
4. Copy `mt5/Experts/XAU_Sniper_AI.mq5` to your MT5 `MQL5/Experts/XAU-Sniper-AI/` folder.
5. Compile in MetaEditor.
6. Open **XAUUSD, M5**.
7. Attach `XAU_Sniper_AI`.
8. Use demo first and keep `AllowLiveTrading=false`.
9. Turn **Algo Trading** ON only when you want the EA to be able to execute approved demo trades.

## What should appear on the chart

```text
XAU SNIPER AI | GOLD M5 ONLY
API: CONNECTED   Algo Trading: ON/OFF
Bid/Ask: ...
M5 Trend: bullish/bearish/neutral
Sweep: sell_side/buy_side/none
CHoCH: ...
BOS: ...
FVG: ...
ACTION: WAIT/LONG/SHORT
Entry / SL / TP1(2R) / TP2(3R)
Execution candle: NEW CLOSED M5 / MONITOR ONLY
Reason: ...
```

## Python console logs

The API prints one analysis line for every request so you can watch how the bot is reading the chart in realtime.

## Safety defaults

- `AllowLiveTrading=false`
- no martingale
- no grid
- no averaging down
- no stop widening
- max one bot exposure per symbol
- API failure = no trade
- `WAIT` = no trade
