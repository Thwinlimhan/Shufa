"""Shared async LLM client via OpenRouter for all vault agents."""
from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from backend.research.vault_config import vault_cfg

log = structlog.get_logger()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def llm_complete(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """Send a chat-completion request and return the assistant message text.

    Returns an empty string (and logs a warning) when the API key is missing
    so callers can gracefully degrade.
    """
    api_key = vault_cfg.openrouter_api_key
    if not api_key:
        log.warning("llm_complete skipped — no OPENROUTER_API_KEY")
        return ""

    body: dict[str, Any] = {
        "model": vault_cfg.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def llm_json(
    system_prompt: str,
    user_prompt: str,
    **kwargs: Any,
) -> dict | list:
    """Convenience: call llm_complete and parse the result as JSON."""
    raw = await llm_complete(system_prompt, user_prompt, json_mode=True, **kwargs)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # LLMs sometimes wrap JSON in markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
