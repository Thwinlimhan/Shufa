"""Agent A — Ingestion Agent.

Watches `raw/` for new files, generates summaries with provenance tracking,
and updates the search index.
"""
from __future__ import annotations

import glob
import hashlib
import os
from pathlib import Path

import structlog

from backend.research.llm_client import llm_json
from backend.research.search import reindex
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_summary

log = structlog.get_logger()

SYSTEM_INGEST = """\
You are an expert research ingestion agent.  You are given the full text of a
source document.  Produce a JSON object with these keys:
  - "title": a concise title for the document
  - "entities": list of 3-8 key entities/concepts mentioned
  - "summary": a thorough 200-400 word summary capturing all important claims,
    data points, and conclusions.  Use markdown.  Include any specific numbers.
  - "tags": list of 3-6 lowercase single-word tags
"""


def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _known_sources() -> set[str]:
    """Collect all source paths already referenced in summary frontmatter."""
    sources: set[str] = set()
    pattern = str(vault_cfg.summaries_dir / "*.md")
    for summary_path in glob.glob(pattern):
        with open(summary_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("source:"):
                    sources.add(stripped.split(":", 1)[1].strip())
                if stripped == "---" and sources:
                    break  # past frontmatter
    return sources


def _raw_files() -> list[str]:
    """All .md, .txt, and .csv files in raw/."""
    exts = ("*.md", "*.txt", "*.csv")
    files: list[str] = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(str(vault_cfg.raw_dir), "**", ext), recursive=True))
    return sorted(files)


async def ingest_file(filepath: str) -> Path | None:
    """Ingest a single raw file into the wiki. Returns summary path or None."""
    rel = os.path.relpath(filepath, str(vault_cfg.root))
    log.info("ingesting", file=rel)

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if len(content.strip()) < 50:
        log.warning("file too short, skipping", file=rel)
        return None

    # Truncate very large files to avoid token limits
    if len(content) > 60_000:
        content = content[:60_000] + "\n\n[... truncated ...]"

    result = await llm_json(SYSTEM_INGEST, content)
    if not result:
        log.warning("LLM returned empty result", file=rel)
        return None

    title = result.get("title", Path(filepath).stem)
    entities = result.get("entities", [])
    summary_body = result.get("summary", "")
    if not summary_body:
        return None

    # Build the summary body with title
    body = f"# {title}\n\n{summary_body}"

    fhash = _file_hash(filepath)
    summary_path = write_summary(
        filename=Path(filepath).stem,
        source_path=rel,
        source_hash=fhash,
        entities=entities,
        body=body,
    )
    log.info("summary written", path=str(summary_path))
    return summary_path


async def ingest_new_files(vault_root: str | None = None) -> list[Path]:
    """Scan raw/ and ingest any files that don't have summaries yet."""
    if vault_root:
        # Allow override for testing
        os.environ["VAULT_ROOT"] = vault_root

    known = _known_sources()
    raw = _raw_files()
    new_files = [
        f for f in raw
        if os.path.relpath(f, str(vault_cfg.root)) not in known
    ]

    if not new_files:
        log.info("no new raw files to ingest")
        return []

    log.info("found new raw files", count=len(new_files))
    results: list[Path] = []
    for filepath in new_files:
        try:
            path = await ingest_file(filepath)
            if path:
                results.append(path)
        except Exception:
            log.exception("ingest failed", file=filepath)

    # Rebuild index and search after batch
    if results:
        rebuild_index()
        reindex()
        log.info("ingestion batch complete", ingested=len(results))

    return results
