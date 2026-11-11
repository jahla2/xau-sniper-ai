from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .models import TradePlan


class ClaudeReviewError(RuntimeError):
    pass


async def review_plan(plan: TradePlan) -> dict[str, Any]:
    """Optional second-opinion filter. It never executes trades and never changes hard risk limits."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ClaudeReviewError("ANTHROPIC_API_KEY is not configured")
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

    schema = {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["APPROVE", "WAIT", "REJECT"]},
            "confidence": {"type": "integer"},
            "reason": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["decision", "confidence", "reason"],
        "additionalProperties": False,
    }
    payload = {
        "model": model,
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Review this deterministic XAUUSD scalp plan. Do not invent market data. "
                    "Approve only when liquidity sweep, CHoCH/BOS, FVG and invalidation are internally consistent. "
                    "Return WAIT when confirmation is incomplete. Plan: " + plan.model_dump_json()
                ),
            }
        ],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    if response.status_code >= 400:
        raise ClaudeReviewError(f"Claude API returned HTTP {response.status_code}")
    body = response.json()
    try:
        text_value = next(block["text"] for block in body["content"] if block.get("type") == "text")
        return json.loads(text_value)
    except (KeyError, StopIteration, json.JSONDecodeError) as exc:
        raise ClaudeReviewError("Claude response was not valid structured output") from exc
