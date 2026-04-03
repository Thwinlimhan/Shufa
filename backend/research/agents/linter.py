"""Agent E — Linter Agent.

Health-checks the wiki for broken links, stale sources, contradictions,
orphan files, and missing citations.
"""
from __future__ import annotations

import glob
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import structlog

from backend.research.llm_client import llm_json
from backend.research.search import reindex
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index, write_dispute

log = structlog.get_logger()


def _all_md_files(directory: Path) -> list[Path]:
    """Recursively find all .md files."""
    return sorted(Path(p) for p in glob.glob(str(directory / "**" / "*.md"), recursive=True))


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilink]] references from markdown content."""
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _extract_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML-ish frontmatter as a flat key: value dict."""
    fm: dict[str, str] = {}
    if not content.startswith("---"):
        return fm
    end = content.find("---", 3)
    if end < 0:
        return fm
    for line in content[3:end].split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


# ── Check functions ──────────────────────────────────────────────────

def check_broken_links() -> list[dict]:
    """Find [[wikilinks]] that don't resolve to any file."""
    all_files = _all_md_files(vault_cfg.wiki_dir)
    all_stems = {f.stem for f in all_files}

    issues: list[dict] = []
    for md_file in all_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for link in _extract_wikilinks(content):
            # wikilinks match by stem (filename without extension)
            if link not in all_stems:
                issues.append({
                    "type": "broken_link",
                    "file": str(md_file),
                    "link": link,
                })
    return issues


def check_stale_sources() -> list[dict]:
    """Find summaries whose source_hash no longer matches the raw file."""
    issues: list[dict] = []
    for summary_path in _all_md_files(vault_cfg.summaries_dir):
        content = summary_path.read_text(encoding="utf-8", errors="replace")
        fm = _extract_frontmatter(content)
        source = fm.get("source", "")
        recorded_hash = fm.get("source_hash", "").replace("sha256:", "")

        if not source or not recorded_hash:
            continue

        full_source = vault_cfg.root / source
        if not full_source.exists():
            issues.append({
                "type": "missing_source",
                "summary": str(summary_path),
                "source": source,
            })
            continue

        current_hash = _file_hash(str(full_source))
        if current_hash != recorded_hash:
            issues.append({
                "type": "stale_source",
                "summary": str(summary_path),
                "source": source,
                "recorded_hash": recorded_hash[:12],
                "current_hash": current_hash[:12],
            })
    return issues


def check_orphan_raw_files() -> list[dict]:
    """Find raw/ files with no corresponding summary."""
    # Collect all sources referenced in summaries
    known_sources: set[str] = set()
    for summary_path in _all_md_files(vault_cfg.summaries_dir):
        content = summary_path.read_text(encoding="utf-8", errors="replace")
        fm = _extract_frontmatter(content)
        source = fm.get("source", "")
        if source:
            known_sources.add(source)

    # Check raw files
    issues: list[dict] = []
    exts = ("*.md", "*.txt", "*.csv")
    for ext in exts:
        for raw_file in glob.glob(os.path.join(str(vault_cfg.raw_dir), "**", ext), recursive=True):
            rel = os.path.relpath(raw_file, str(vault_cfg.root))
            if rel not in known_sources:
                issues.append({"type": "orphan_raw", "file": rel})
    return issues


async def check_contradictions() -> list[dict]:
    """Use the LLM to scan concept articles for contradictions."""
    concepts = _all_md_files(vault_cfg.concepts_dir)
    if len(concepts) < 2:
        return []

    # Build a condensed view of all concepts
    concept_summaries: list[str] = []
    for path in concepts[:30]:  # cap to avoid token overflow
        content = path.read_text(encoding="utf-8", errors="replace")
        # Take first 500 chars
        concept_summaries.append(f"### {path.stem}\n{content[:500]}")

    user_prompt = "\n\n---\n\n".join(concept_summaries)

    system_prompt = """\
You are a wiki linter.  Scan these concept articles for contradictions —
cases where two articles make conflicting claims about the same topic.

Return a JSON array of objects, each with:
  - "articles": [article1_stem, article2_stem]
  - "conflict": description of the contradiction
  - "suggested_resolution": how to fix it

If no contradictions found, return an empty array: []
"""
    try:
        result = await llm_json(system_prompt, user_prompt)
    except Exception:
        log.exception("contradiction check failed")
        return []

    contradictions = result if isinstance(result, list) else []

    # Write dispute files
    issues: list[dict] = []
    existing_disputes = len(list(_all_md_files(vault_cfg.disputes_dir)))
    for i, c in enumerate(contradictions):
        dispute_id = f"D{existing_disputes + i + 1:03d}"
        articles = c.get("articles", [])
        conflict = c.get("conflict", "Unknown conflict")
        resolution = c.get("suggested_resolution", "Needs investigation")

        write_dispute(dispute_id, articles, conflict, resolution)
        issues.append({
            "type": "contradiction",
            "dispute_id": dispute_id,
            "articles": articles,
            "conflict": conflict,
        })

    return issues


async def lint_wiki(vault_root: str | None = None) -> dict:
    """Run all lint checks.  Returns a summary of all issues found."""
    if vault_root:
        os.environ["VAULT_ROOT"] = vault_root

    log.info("linter: starting wiki health check")

    broken = check_broken_links()
    stale = check_stale_sources()
    orphans = check_orphan_raw_files()
    contradictions = await check_contradictions()

    all_issues = broken + stale + orphans + contradictions

    # Rebuild index and search after any changes
    rebuild_index()
    reindex()

    summary = {
        "total_issues": len(all_issues),
        "broken_links": len(broken),
        "stale_sources": len(stale),
        "orphan_raw_files": len(orphans),
        "contradictions": len(contradictions),
        "issues": all_issues[:50],  # cap for logging
    }
    log.info("linter: complete", **{k: v for k, v in summary.items() if k != "issues"})
    return summary
