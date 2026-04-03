"""Agent F — Scout Agent.

Identifies gaps in the knowledge base: orphan knowledge, stub concepts,
dead-end hypotheses, and suggests new research directions.
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from pathlib import Path

import structlog

from backend.research.llm_client import llm_json
from backend.research.results_log import read_results
from backend.research.search import reindex, search
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_report

log = structlog.get_logger()


def _all_md_stems(directory: Path) -> set[str]:
    """Get all .md file stems from a directory."""
    return {
        Path(p).stem
        for p in glob.glob(str(directory / "*.md"))
    }


def _extract_related_from_file(path: Path) -> list[str]:
    """Extract [[wikilinks]] from a file."""
    import re
    content = path.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def find_orphan_summaries() -> list[str]:
    """Summaries not linked from any concept article."""
    summary_stems = _all_md_stems(vault_cfg.summaries_dir)

    # Collect all wikilinks from concept files
    linked: set[str] = set()
    for path in vault_cfg.concepts_dir.glob("*.md"):
        linked.update(_extract_related_from_file(path))

    return sorted(summary_stems - linked)


def find_stub_concepts(min_sources: int = 3) -> list[dict]:
    """Concepts with fewer than min_sources references."""
    stubs: list[dict] = []
    for path in vault_cfg.concepts_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Count wikilinks to summaries
        links = _extract_related_from_file(path)
        if len(links) < min_sources:
            stubs.append({"concept": path.stem, "link_count": len(links)})
    return stubs


def find_dead_end_hypotheses() -> list[dict]:
    """Supported hypotheses whose further_questions haven't been explored."""
    dead_ends: list[dict] = []
    supported_dir = vault_cfg.hypotheses_dir / "supported"
    if not supported_dir.exists():
        return dead_ends

    results = read_results()
    tested_titles = {r.get("description", "").lower() for r in results}

    for path in supported_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Extract further questions
        in_questions = False
        questions: list[str] = []
        for line in content.split("\n"):
            if line.strip().startswith("## Further Questions"):
                in_questions = True
                continue
            if in_questions:
                if line.startswith("## "):
                    break
                if line.strip().startswith("- "):
                    questions.append(line.strip()[2:])

        # Check if any question has been explored
        unexplored = [
            q for q in questions
            if not any(q.lower()[:30] in t for t in tested_titles)
        ]
        if unexplored:
            dead_ends.append({
                "hypothesis": path.stem,
                "unexplored_questions": unexplored,
            })

    return dead_ends


async def scout_gaps(vault_root: str | None = None) -> Path:
    """Run a full gap detection pass and write a scout report."""
    if vault_root:
        os.environ["VAULT_ROOT"] = vault_root

    log.info("scout: starting gap detection")

    orphans = find_orphan_summaries()
    stubs = find_stub_concepts()
    dead_ends = find_dead_end_hypotheses()

    # Build context for LLM to suggest next steps
    context_parts = []
    if orphans:
        context_parts.append(
            f"Orphan summaries (not linked to any concept): {', '.join(orphans[:20])}"
        )
    if stubs:
        stub_text = ", ".join(f"{s['concept']} ({s['link_count']} links)" for s in stubs[:20])
        context_parts.append(f"Stub concepts (few sources): {stub_text}")
    if dead_ends:
        for de in dead_ends[:10]:
            qs = "; ".join(de["unexplored_questions"][:3])
            context_parts.append(f"Dead-end: {de['hypothesis']} — unexplored: {qs}")

    context_text = "\n".join(context_parts) if context_parts else "No gaps detected."

    # Ask LLM to prioritize and suggest
    system_prompt = """\
You are a research scout agent.  You are given gaps in a crypto research
knowledge base.  Prioritize the gaps and suggest concrete next steps.

Return JSON:
{
  "priority_topics": ["topic to research next", ...],
  "concept_gaps": ["concepts that need deeper coverage", ...],
  "suggested_hypotheses": ["specific hypothesis to test next", ...],
  "overall_health": "healthy" | "needs_attention" | "critical"
}
"""
    try:
        suggestions = await llm_json(system_prompt, context_text)
    except Exception:
        log.exception("scout: LLM suggestions failed")
        suggestions = {}

    # Build the report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_sections = [
        f"**Generated**: {now}\n",
        f"## Overall Health: {suggestions.get('overall_health', 'unknown')}\n",
    ]

    report_sections.append("## Orphan Summaries (not linked to any concept)\n")
    if orphans:
        report_sections.append("\n".join(f"- [[{o}]]" for o in orphans))
    else:
        report_sections.append("_None — all summaries are linked._")

    report_sections.append("\n## Stub Concepts (insufficient sources)\n")
    if stubs:
        report_sections.append("\n".join(
            f"- **{s['concept']}**: only {s['link_count']} links" for s in stubs
        ))
    else:
        report_sections.append("_None — all concepts are well-sourced._")

    report_sections.append("\n## Dead-End Hypotheses (unexplored follow-ups)\n")
    if dead_ends:
        for de in dead_ends:
            qs = "\n".join(f"  - {q}" for q in de["unexplored_questions"])
            report_sections.append(f"- **{de['hypothesis']}**:\n{qs}")
    else:
        report_sections.append("_None — all follow-up questions explored._")

    report_sections.append("\n## LLM Suggestions\n")
    if suggestions:
        for key in ("priority_topics", "concept_gaps", "suggested_hypotheses"):
            items = suggestions.get(key, [])
            if items:
                report_sections.append(f"### {key.replace('_', ' ').title()}")
                report_sections.append("\n".join(f"- {item}" for item in items))

    report_content = "\n\n".join(report_sections)
    report_path = write_report(f"scout_report_{now}", report_content)

    # Rebuild index
    rebuild_index()
    reindex()

    log.info(
        "scout: report written",
        path=str(report_path),
        orphans=len(orphans),
        stubs=len(stubs),
        dead_ends=len(dead_ends),
    )
    return report_path
