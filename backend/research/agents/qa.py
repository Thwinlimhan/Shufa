"""Agent D — Q&A / Research Agent.

Interactive agent that answers questions against the knowledge base and
writes structured output to outputs/reports/ or outputs/slides/.

Usage:
    python -m backend.research.agents.qa "What is the relationship between funding rates and basis?"
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import structlog

from backend.research.llm_client import llm_complete, llm_json
from backend.research.search import read_file, search
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_report, write_slides

log = structlog.get_logger()

SYSTEM_QA = """\
You are a research assistant with deep expertise in crypto market microstructure.
You have been given relevant articles from a research knowledge base.

Answer the user's question thoroughly, citing specific sources from the wiki
where possible using [[wikilink]] syntax.

Structure your response in clear markdown with:
- An executive summary (2-3 sentences)
- Detailed analysis with sub-headings
- Evidence citations using [[Source Name]]
- Conclusions and open questions
"""

SYSTEM_SLIDE = """\
You are a presentation creator.  Given a research answer, convert it into
5-10 Marp-compatible slides.  Each slide should have:
- A clear title (## heading)
- 3-5 bullet points or a short paragraph
- No slide should exceed 150 words

Return a JSON array of strings, where each string is the markdown for one slide.
"""


async def answer_question(
    query: str,
    *,
    vault_path: str | None = None,
    output_format: str = "report",
) -> Path:
    """Answer a question against the wiki.

    Args:
        query: The user's question.
        vault_path: Override vault root.
        output_format: 'report' for markdown, 'slides' for Marp presentation.

    Returns:
        Path to the generated output file.
    """
    if vault_path:
        os.environ["VAULT_ROOT"] = vault_path

    # 1. Search the knowledge base
    hits = search(query, limit=15)
    log.info("qa_agent: search complete", query=query, hits=len(hits))

    # 2. Read full content of top hits
    evidence_parts: list[str] = []
    for hit in hits[:8]:
        try:
            content = read_file(hit["file"])
            # Truncate to avoid token overflow
            if len(content) > 4000:
                content = content[:4000] + "\n[... truncated ...]"
            evidence_parts.append(f"### Source: {hit['title']} ({hit['file']})\n{content}")
        except Exception:
            log.warning("qa_agent: could not read file", file=hit["file"])

    evidence_text = "\n\n---\n\n".join(evidence_parts) if evidence_parts else (
        "No relevant documents found in the knowledge base."
    )

    # 3. Generate answer
    user_prompt = f"""## Question
{query}

## Relevant Documents from Knowledge Base
{evidence_text}

Answer the question comprehensively, citing sources."""

    answer = await llm_complete(SYSTEM_QA, user_prompt, max_tokens=4096)

    if not answer:
        answer = f"_Could not generate an answer for: {query}_"

    # 4. Write output
    # Clean title from query
    safe_title = query[:60].strip().replace("?", "").replace("/", "_").replace("\\", "_")

    if output_format == "slides":
        slide_result = await llm_json(SYSTEM_SLIDE, answer, max_tokens=4096)
        slides = slide_result if isinstance(slide_result, list) else [answer]
        output_path = write_slides(safe_title, slides)
    else:
        output_path = write_report(safe_title, answer)

    log.info("qa_agent: output written", path=str(output_path), format=output_format)
    return output_path


# ── CLI entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m backend.research.agents.qa <question>")
        print('       python -m backend.research.agents.qa --slides "question"')
        sys.exit(1)

    fmt = "report"
    args = sys.argv[1:]
    if args[0] == "--slides":
        fmt = "slides"
        args = args[1:]

    question = " ".join(args)
    result = asyncio.run(answer_question(question, output_format=fmt))
    print(f"Output written to: {result}")
