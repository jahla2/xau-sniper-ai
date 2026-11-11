from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI

from .analysis import analyze_market, summarize_plan
from .claude import ClaudeReviewError, review_plan
from .models import Action, AnalyzeRequest, AnalyzeResponse
from .risk import validate_plan

app = FastAPI(title="XAU Sniper AI", version="0.2.0")
logger = logging.getLogger("uvicorn.error")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "xau-sniper-ai", "strategy": "XAUUSD_M5_SMC_ICT"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    plan = analyze_market(request.market)
    rejection_reasons = validate_plan(plan, request.market, request.policy, request.risk)
    ai_review = None

    if request.use_claude and plan.action != Action.WAIT and not rejection_reasons:
        try:
            ai_review = await review_plan(plan)
            if ai_review.get("decision") != "APPROVE":
                rejection_reasons.append(f"Claude review: {ai_review.get('decision', 'UNKNOWN')}")
        except ClaudeReviewError as exc:
            rejection_reasons.append(str(exc))

    summary = summarize_plan(plan)
    last = request.market.m5[-1] if request.market.m5 else None
    last_closed = "n/a" if last is None else datetime.fromtimestamp(last.ts, tz=timezone.utc).isoformat()
    approved = not rejection_reasons
    logger.info(
        "XAU M5 LIVE | bid=%.2f ask=%.2f spread=%.2f last_closed=%s | %s | approved=%s%s",
        request.market.bid,
        request.market.ask,
        float(request.market.spread or 0.0),
        last_closed,
        summary,
        approved,
        "" if not rejection_reasons else " | blocked=" + "; ".join(rejection_reasons),
    )

    return AnalyzeResponse(
        summary=summary,
        plan=plan,
        approved=approved,
        rejection_reasons=rejection_reasons,
        ai_review=ai_review,
    )
