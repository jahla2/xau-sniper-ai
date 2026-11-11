# xau-sniper-ai

Rule-first XAUUSD scalping engine for MT5 using SMC/ICT concepts with optional Claude review.

> **Status:** v0.1 foundation. Use demo/paper trading only. This software does not guarantee profitable trades.

## What v0.1 includes

- Liquidity sweep detection
- CHoCH/BOS foundation from swing structure
- Fair Value Gap (FVG) detection
- Higher-timeframe bias from M15/H1
- `LONG`, `SHORT`, or `WAIT` trade plans
- Hard risk gate for spread, RR, position count and daily loss
- Optional Claude structured-output review
- FastAPI endpoint for future MT5 Expert Advisor integration
- Automated tests + GitHub Actions CI

## Architecture

```text
MT5 EA -> FastAPI -> SMC/ICT engine -> hard risk gate -> optional Claude review -> approved signal
```

Claude is deliberately a **review layer**, not the risk authority. A failed API call, missing confirmation, or failed risk rule results in no trade.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn xau_sniper_ai.api:app --host 127.0.0.1 --port 8765
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

## Tests

```bash
pytest
```

## Claude integration

Copy `.env.example` values into your environment and set `ANTHROPIC_API_KEY`. The default model is `claude-sonnet-5-5`. Never put a real API key in Git.

## MT5 note

The EA will communicate with the local service using MQL5 `WebRequest`. MT5 must explicitly allow the service URL under **Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URL**. The MT5 Strategy Tester does not execute `WebRequest`, so deterministic strategy testing is kept separate from the optional AI review.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the staged implementation and acceptance criteria.
