"""Agent C — Hypothesis Engine (the autoresearch loop).

This is the core adaptation of karpathy/autoresearch.  Instead of editing
train.py and measuring val_bpb, we generate hypotheses, validate them
against the knowledge base, and file the results.

Usage:
    python -m backend.research.agents.hypothesis --hours 8
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import structlog

from backend.research.llm_client import llm_complete, llm_json
from backend.research.results_log import log_result, next_hypothesis_id, read_results
from backend.research.search import reindex, search
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_hypothesis

log = structlog.get_logger()

# ── Prompts ──────────────────────────────────────────────────────────

SYSTEM_GENERATE = """\
You are an autonomous hypothesis generator for crypto market microstructure
research.  You have access to a knowledge base about funding rates, basis
trading, perpetual futures, on-chain analytics, and order-flow dynamics.

Given:
1. The current wiki index (table of contents)
2. Previous hypothesis results
3. Relevant search snippets

Generate ONE new, specific, falsifiable hypothesis.

Return JSON:
{
  "title": "short descriptive title",
  "claim": "precise falsifiable claim with specific numbers and conditions",
  "related_concepts": ["Concept A", "Concept B"],
  "validation_approach": "how to test this hypothesis",
  "data_required": "what data is needed"
}

Rules:
- MUST be falsifiable and specific (include thresholds, time windows, probabilities)
- MUST NOT duplicate any previously tested hypothesis
- Prefer hypotheses that connect multiple concepts
- Prefer hypotheses testable with existing data
"""

SYSTEM_VALIDATE = """\
You are an autonomous hypothesis validator for crypto research.
You are given a hypothesis and all available evidence from a knowledge base.

Evaluate the hypothesis and return JSON:
{
  "status": "supported" | "refuted" | "open",
  "confidence": 0.0 to 1.0,
  "evidence_for": ["specific evidence point 1", "specific evidence point 2"],
  "evidence_against": ["specific counter-evidence 1"],
  "conclusion": "2-4 sentence analysis",
  "further_questions": ["follow-up question 1", "follow-up question 2"]
}

Rules:
- Be rigorous.  "supported" requires confidence >= 0.6 with multiple evidence points.
- "open" means insufficient data to decide (confidence 0.3-0.6).
- "refuted" means evidence clearly contradicts the claim (confidence < 0.3 *for* the claim).
- Always suggest 2-3 follow-up questions regardless of outcome.
"""


async def _read_context() -> tuple[str, str]:
    """Read the wiki index and previous results as context strings."""
    index_text = ""
    if vault_cfg.index_path.exists():
        index_text = vault_cfg.index_path.read_text(encoding="utf-8")

    results = read_results()
    if results:
        results_text = "\n".join(
            f"- {r['hypothesis_id']}: [{r['status']}] {r['description']}"
            for r in results[-20:]  # last 20
        )
    else:
        results_text = "No previous hypotheses tested."

    return index_text, results_text


async def generate_hypothesis() -> dict:
    """Generate a single new hypothesis."""
    index_text, results_text = await _read_context()

    # Search for recent interesting topics
    interesting_hits = search("funding OR basis OR arbitrage OR liquidation", limit=5)
    snippets = "\n".join(
        f"- [{h['title']}]: {h['snippet']}" for h in interesting_hits
    ) if interesting_hits else "No search results yet — wiki is empty."

    user_prompt = f"""## Current Wiki Index
{index_text[:3000]}

## Previous Hypotheses
{results_text}

## Recent Knowledge Snippets
{snippets}

Generate ONE new hypothesis that hasn't been tested before."""

    result = await llm_json(SYSTEM_GENERATE, user_prompt)
    return result if isinstance(result, dict) else {}


async def validate_hypothesis(hypothesis: dict) -> dict:
    """Validate a hypothesis against the knowledge base."""
    claim = hypothesis.get("claim", "")
    title = hypothesis.get("title", "")

    # Search for evidence
    evidence_hits = search(title, limit=10)
    related = hypothesis.get("related_concepts", [])
    for concept in related:
        evidence_hits.extend(search(concept, limit=5))

    # De-duplicate by filepath
    seen: set[str] = set()
    unique_hits: list[dict] = []
    for h in evidence_hits:
        if h["file"] not in seen:
            seen.add(h["file"])
            unique_hits.append(h)

    evidence_text = "\n\n".join(
        f"### Source: {h['title']}\n{h['snippet']}" for h in unique_hits[:15]
    ) if unique_hits else "No relevant evidence found in the knowledge base."

    user_prompt = f"""## Hypothesis
Title: {title}
Claim: {claim}
Validation Approach: {hypothesis.get('validation_approach', 'N/A')}

## Available Evidence
{evidence_text}

Evaluate this hypothesis against the evidence."""

    result = await llm_json(SYSTEM_VALIDATE, user_prompt)
    return result if isinstance(result, dict) else {}


async def run_one_cycle() -> str | None:
    """Run a single hypothesis-generate-validate-log cycle.

    Returns the hypothesis ID on success, None on failure.
    """
    # 1. Generate
    log.info("hypothesis_engine: generating hypothesis")
    hypothesis = await generate_hypothesis()
    if not hypothesis or not hypothesis.get("claim"):
        log.warning("hypothesis_engine: generation failed")
        return None

    hid = next_hypothesis_id()
    title = hypothesis.get("title", "Untitled")
    claim = hypothesis.get("claim", "")
    related = hypothesis.get("related_concepts", [])

    log.info("hypothesis_engine: generated", id=hid, title=title)

    # 2. Validate
    try:
        validation = await validate_hypothesis(hypothesis)
    except Exception:
        log.exception("hypothesis_engine: validation crashed", id=hid)
        log_result(hid, "crash", 0.0, 0, f"Validation crashed: {title}")
        return hid

    if not validation:
        log_result(hid, "crash", 0.0, 0, f"Validator returned empty: {title}")
        return hid

    status = validation.get("status", "open")
    confidence = float(validation.get("confidence", 0.5))
    evidence_for = validation.get("evidence_for", [])
    evidence_against = validation.get("evidence_against", [])
    conclusion = validation.get("conclusion", "No conclusion provided.")
    further_questions = validation.get("further_questions", [])
    evidence_count = len(evidence_for) + len(evidence_against)

    # 3. Write hypothesis file
    write_hypothesis(
        hypothesis_id=hid,
        title=title,
        claim=claim,
        status=status,
        confidence=confidence,
        evidence_for=evidence_for,
        evidence_against=evidence_against,
        conclusion=conclusion,
        further_questions=further_questions,
        related_concepts=related,
    )

    # 4. Log to results.tsv
    log_result(hid, status, confidence, evidence_count, title)

    # 5. Rebuild index
    rebuild_index()
    reindex()

    log.info(
        "hypothesis_engine: cycle complete",
        id=hid,
        status=status,
        confidence=confidence,
    )
    return hid


async def run_hypothesis_loop(
    vault_path: str | None = None,
    max_hours: float = 8.0,
    max_cycles: int | None = None,
    cooldown_seconds: float = 10.0,
) -> list[str]:
    """Run the autonomous hypothesis loop (the NEVER STOP loop).

    Returns list of hypothesis IDs generated.
    """
    if vault_path:
        os.environ["VAULT_ROOT"] = vault_path

    start = time.time()
    deadline = start + (max_hours * 3600)
    completed: list[str] = []
    cycle = 0

    log.info(
        "hypothesis_engine: starting loop",
        max_hours=max_hours,
        max_cycles=max_cycles,
    )

    while time.time() < deadline:
        if max_cycles is not None and cycle >= max_cycles:
            break

        cycle += 1
        log.info("hypothesis_engine: cycle", cycle=cycle)

        try:
            hid = await run_one_cycle()
            if hid:
                completed.append(hid)
        except Exception:
            log.exception("hypothesis_engine: cycle failed", cycle=cycle)

        # Brief cooldown between cycles
        await asyncio.sleep(cooldown_seconds)

    elapsed = time.time() - start
    log.info(
        "hypothesis_engine: loop finished",
        cycles=cycle,
        hypotheses=len(completed),
        elapsed_seconds=round(elapsed, 1),
    )
    return completed


# ── CLI entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous hypothesis research loop")
    parser.add_argument("--hours", type=float, default=8.0, help="Max hours to run")
    parser.add_argument("--cycles", type=int, default=None, help="Max cycles (overrides hours)")
    parser.add_argument("--vault", type=str, default=None, help="Vault root path")
    args = parser.parse_args()

    asyncio.run(
        run_hypothesis_loop(
            vault_path=args.vault,
            max_hours=args.hours,
            max_cycles=args.cycles,
        )
    )
