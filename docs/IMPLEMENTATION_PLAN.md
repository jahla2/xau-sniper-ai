# XAU Sniper AI — Implementation Plan

## Goal
Build a rule-first XAUUSD scalping system for MT5 that detects SMC/ICT setups, returns `LONG`, `SHORT`, or `WAIT`, applies hard risk limits, optionally asks Claude for a second opinion, and only then allows the MT5 EA to execute.

## Non-negotiable rules
- No martingale, grid, averaging down, or stop widening.
- `WAIT` is a valid output whenever confirmation is incomplete.
- Strategy engine must work without Claude so it can be tested deterministically.
- Claude is a review/filter layer; it never bypasses the hard risk engine.
- Start on MT5 demo. Live mode is a separate explicit switch.

## Architecture
1. **MT5 EA** collects M1/M5/M15/H1 OHLC and account state.
2. **FastAPI service** accepts the snapshot at `/analyze`.
3. **SMC/ICT engine** detects liquidity sweep, CHoCH/BOS, FVG, swings and HTF bias.
4. **Risk gate** validates spread, open-position count, daily loss and minimum RR.
5. **Claude reviewer (optional)** returns APPROVE/WAIT/REJECT using structured JSON.
6. **MT5 execution layer** creates/cancels orders and applies SL/TP only when approved.
7. **Journal** stores every input, decision and trade result for later evaluation.

## Phase 1 — Tested analysis service (this PR)
- FastAPI `/health` and `/analyze`.
- Deterministic candle models and validation.
- Liquidity sweep detection.
- Pivot-based structure/BOS/CHoCH foundation.
- FVG detection.
- Rule-first `LONG` / `SHORT` / `WAIT` plans.
- Risk gate.
- Optional Claude structured-output reviewer.
- Unit/API tests and GitHub Actions.

## Phase 2 — MT5 EA integration (implemented foundation)
- `mt5/Experts/XAU_Sniper_AI.mq5` Expert Advisor.
- Collects closed candles only; avoids decisions on incomplete candles.
- POSTs snapshot to `http://127.0.0.1:8765/analyze` via `WebRequest`.
- Parses approved `LONG` / `SHORT` / `WAIT` responses.
- Demo-first default; real-account execution requires an explicit opt-in.
- One bot position/order per symbol via magic number and duplicate protection.
- Risk-based volume sizing from entry-to-SL distance.
- Auto MARKET/LIMIT entry, SL, TP2, TP1 partial close + break-even, and stale-order cancellation.
- Remaining: richer on-chart dashboard and MetaEditor compile/terminal forward validation on the target Windows MT5 install.

## Phase 3 — Backtest harness
Because MT5 `WebRequest` is unavailable in Strategy Tester, export/replay historical candles through the deterministic Python engine and separately implement/reuse the same core rules in the EA test mode. Track win rate, expectancy, profit factor, maximum drawdown, MAE/MFE, session and setup subtype.

## Phase 4 — Paper/demo forward test
- Minimum 100–300 trades before considering live deployment.
- Compare rules-only vs Claude-filtered signals.
- Reject Claude if it worsens out-of-sample expectancy or drawdown.

## Phase 5 — Controlled live rollout
- Tiny risk only after passing acceptance thresholds.
- Kill switch, max daily loss, max trades/session, health-check failure = no trade.

## Acceptance criteria for v1
- All automated tests pass.
- `/health` returns HTTP 200.
- `/analyze` always returns schema-valid output.
- Missing confirmation returns `WAIT`.
- Risk gate can veto a valid-looking strategy signal.
- Claude API key is optional and never stored in the repository.
