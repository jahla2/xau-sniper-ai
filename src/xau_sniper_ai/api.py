from __future__ import annotations

from fastapi import FastAPI

from .analysis import analyze_market
from .claude import ClaudeReviewError, review_plan
from .models import Action, AnalyzeRequest, AnalyzeResponse
from .risk import validate_plan

app = FastAPI(title="XAU Sniper AI", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "xau-sniper-ai"}


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

    return AnalyzeResponse(
        plan=plan,
        approved=not rejection_reasons,
        rejection_reasons=rejection_reasons,
        ai_review=ai_review,
    )
