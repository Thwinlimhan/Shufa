from __future__ import annotations

import json

import httpx

from backend.core.config import settings

SYSTEM_MARKET_STRUCTURE = """
You are a market structure analyst for BTC and ETH perpetual futures.
Return JSON only with keys:
regime, confidence, funding_bias, key_observations, suggested_regime_filter_adjustments.
"""


async def run_market_structure_analysis(feature_summary: dict) -> dict:
    if not settings.openrouter_api_key:
        return {
            "regime": "unknown",
            "confidence": 0.0,
            "funding_bias": "neutral",
            "key_observations": ["OPENROUTER_API_KEY is not configured."],
            "suggested_regime_filter_adjustments": [],
        }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_MARKET_STRUCTURE},
                    {"role": "user", "content": json.dumps(feature_summary)},
                ],
                "temperature": 0.1,
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"]
    return json.loads(message)
