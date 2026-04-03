"""Agent B — Compiler Agent.

Scans summaries, identifies or updates concepts, injects backlinks,
and rebuilds the index.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import structlog

from backend.research.llm_client import llm_json
from backend.research.search import reindex, search
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_concept

log = structlog.get_logger()

SYSTEM_COMPILER = """\
You are a knowledge compiler agent.  You are given a batch of document summaries
from a research wiki.  Your job is to identify overarching CONCEPTS and produce
structured concept articles.

For each concept you identify, return a JSON array of objects, each with:
  - "title": concept name (e.g. "Funding Rate Arbitrage")
  - "content": 150-300 word article body in markdown
  - "tags": list of 3-6 lowercase tags
  - "related_concepts": list of other concept titles this connects to
  - "confidence": "high" | "medium" | "low" | "speculative"
  - "action": "CREATE" | "MERGE" | "UPDATE"
  - "merge_target": if action is MERGE, the existing concept title to merge into (else null)

IMPORTANT:
- Before creating a new concept, check the existing concept list provided.
- If an existing concept covers the same ground, use MERGE or UPDATE instead of CREATE.
- Prefer fewer, richer concepts over many thin ones.
- Return a JSON array (even if only one concept).
"""


def _read_summaries() -> list[dict]:
    """Read all summary files and return metadata + content."""
    summaries = []
    pattern = str(vault_cfg.summaries_dir / "*.md")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        name = Path(path).stem
        summaries.append({"name": name, "path": path, "content": content})
    return summaries


def _existing_concepts() -> list[dict]:
    """Read existing concept titles and tags."""
    concepts = []
    pattern = str(vault_cfg.concepts_dir / "*.md")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        name = Path(path).stem
        title = name.replace("_", " ")
        # Extract tags from frontmatter
        tags: list[str] = []
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                for line in content[3:fm_end].split("\n"):
                    if line.strip().startswith("tags:"):
                        raw = line.split(":", 1)[1].strip().strip("[]")
                        tags = [t.strip() for t in raw.split(",") if t.strip()]
        concepts.append({"title": title, "tags": tags, "path": path})
    return concepts


async def compile_wiki(vault_root: str | None = None) -> int:
    """Run a full compilation pass. Returns count of concepts created/updated."""
    if vault_root:
        os.environ["VAULT_ROOT"] = vault_root

    summaries = _read_summaries()
    if not summaries:
        log.info("no summaries to compile")
        return 0

    existing = _existing_concepts()
    existing_titles = [c["title"] for c in existing]

    # Build the prompt
    summary_text = "\n\n---\n\n".join(
        f"### {s['name']}\n{s['content'][:2000]}" for s in summaries
    )
    existing_text = (
        "Existing concepts: " + json.dumps(existing_titles)
        if existing_titles
        else "No existing concepts yet."
    )

    user_prompt = f"""{existing_text}

Here are the current summaries in the wiki:

{summary_text}

Analyze these summaries and produce concept articles. Use MERGE/UPDATE for
existing concepts when appropriate. Return a JSON array."""

    result = await llm_json(SYSTEM_COMPILER, user_prompt, max_tokens=8000)
    if not result:
        log.warning("compiler got empty LLM response")
        return 0

    # Normalize to list
    concepts = result if isinstance(result, list) else [result]

    created = 0
    for concept in concepts:
        try:
            title = concept.get("title", "Untitled")
            content = concept.get("content", "")
            tags = concept.get("tags", [])
            related = concept.get("related_concepts", [])
            confidence = concept.get("confidence", "medium")
            action = concept.get("action", "CREATE")

            if action == "MERGE":
                merge_target = concept.get("merge_target")
                if merge_target:
                    title = merge_target

            # Count how many summaries reference this concept
            hits = search(title, limit=20)
            source_count = len(hits)

            write_concept(
                title=title,
                content=content,
                tags=tags,
                related_links=related,
                source_count=max(source_count, 1),
                confidence=confidence,
                action=action,
            )
            created += 1
            log.info("concept written", title=title, action=action)
        except Exception:
            log.exception("failed to write concept", concept=concept)

    # Rebuild index and search
    rebuild_index()
    reindex()
    log.info("compilation complete", concepts_written=created)
    return created
