# xau-sniper-ai

Rule-first **XAUUSD / Gold M5-only** scalping engine for MT5 using SMC/ICT concepts with optional Claude review.

> **Status:** demo/paper-trading development. This software does not guarantee profitable trades.

## Strategy

The trading decision uses **closed 5-minute candles only**:

1. Detect a liquidity sweep of a recent M5 range.
2. Require a confirmed M5 CHoCH/BOS.
3. Require a fresh M5 FVG created after the sweep.
4. Prefer entry on the FVG retest.
5. Put SL beyond the sweep/invalidation area with a spread-aware buffer.
6. TP1 is 2R. The optional runner targets TP2 at 3R.
7. Missing confirmation = `WAIT`.

The EA sends live bid/ask to Python every few seconds for monitoring/logging, but a fresh trade may only execute when a **new M5 candle has closed**.

## What is implemented

- XAUUSD-only validation
- M5-only analyzer and MT5 chart validation
- liquidity sweep detection
- CHoCH/BOS foundation
- fresh FVG detection
- `LONG`, `SHORT`, or `WAIT`
- hard risk gate for spread, RR, position count and daily loss
- optional Claude structured-output review
- realtime Python analysis logs
- MT5 on-chart dashboard showing trend, sweep, CHoCH, BOS, FVG, action, confidence, entry, SL, TP and WAIT reason
- demo-first auto execution with risk sizing
- TP1 partial close + break-even and TP2 runner
- duplicate protection and stale-order cancellation

## Architecture

```text
XAUUSD M5 MT5 EA
      |
      | live bid/ask + closed M5 candles every few seconds
      v
FastAPI /analyze
      |
      v
M5 Liquidity Sweep -> CHoCH/BOS -> fresh FVG -> Risk Gate
      |
      +-> optional Claude review
      |
      v
LONG / SHORT / WAIT
      |
      +-> Python realtime log
      +-> MT5 dashboard
      +-> auto trade only on a newly closed M5 candle
```

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m uvicorn xau_sniper_ai.api:app --host 127.0.0.1 --port 8765
```

You should then see lines similar to:

```text
XAU M5 LIVE | bid=4034.10 ask=4034.45 spread=0.35 ... |
M5 WAIT | trend=bullish sweep=buy_side CHoCH=none BOS=none FVG=none |
no confirmed M5 CHoCH/BOS; no fresh M5 FVG after the sweep
```

## Tests

```powershell
pytest
```

Current local verification for this M5-only update: **19 tests passed**, plus a runtime API/log smoke test.

## Claude

Claude remains optional. Set `ANTHROPIC_API_KEY` in the Python environment and enable `UseClaude` only after the deterministic M5 flow is stable. The API key never goes inside the EA.

See [docs/MT5_SETUP.md](docs/MT5_SETUP.md) for MT5 setup.
