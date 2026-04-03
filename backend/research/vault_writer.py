"""Markdown file writers for the vault — concepts, hypotheses, summaries, slides."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from backend.research.vault_config import vault_cfg


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_full() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Summary Writer ───────────────────────────────────────────────────

def write_summary(
    filename: str,
    source_path: str,
    source_hash: str,
    entities: list[str],
    body: str,
) -> Path:
    """Write a summary for an ingested raw document."""
    safe = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    if not safe.endswith("_summary"):
        safe = safe.rsplit(".", 1)[0] + "_summary"
    filepath = vault_cfg.summaries_dir / f"{safe}.md"

    entities_str = "[" + ", ".join(entities) + "]"
    md = f"""---
source: {source_path}
source_hash: "sha256:{source_hash}"
ingested_at: {_now_full()}
entities: {entities_str}
---
{body}
"""
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(md, encoding="utf-8")
    return filepath


# ── Concept Writer ───────────────────────────────────────────────────

def write_concept(
    title: str,
    content: str,
    tags: list[str],
    related_links: list[str],
    source_count: int,
    confidence: str = "medium",
    action: str = "CREATE",
) -> Path:
    """Create or overwrite a concept article with strict schema."""
    safe = title.replace(" ", "_")
    filepath = vault_cfg.concepts_dir / f"{safe}.md"

    tags_str = "[" + ", ".join(tags) + "]"
    links_str = "\n".join([f"- [[{l}]]" for l in related_links])
    now = _now_iso()

    md = f"""---
title: "{title}"
tags: {tags_str}
created: {now}
last_updated: {now}
source_count: {source_count}
confidence_level: {confidence}
last_compiler_action: {action}
---
# {title}

{content}

## Related Concepts
{links_str}
"""
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(md, encoding="utf-8")
    return filepath


# ── Hypothesis Writer ────────────────────────────────────────────────

def write_hypothesis(
    hypothesis_id: str,
    title: str,
    claim: str,
    status: str,
    confidence: float,
    evidence_for: list[str],
    evidence_against: list[str],
    conclusion: str,
    further_questions: list[str],
    related_concepts: list[str],
) -> Path:
    """Write a full hypothesis result file."""
    subdir = vault_cfg.hypotheses_dir / status
    filepath = subdir / f"{hypothesis_id}.md"

    concepts_str = "[" + ", ".join(related_concepts) + "]"
    ev_for = "\n".join(f"{i+1}. {e}" for i, e in enumerate(evidence_for))
    ev_against = "\n".join(f"{i+1}. {e}" for i, e in enumerate(evidence_against))
    questions = "\n".join(f"- {q}" for q in further_questions)
    now = _now_iso()

    md = f"""---
id: {hypothesis_id}
title: "{title}"
status: {status}
confidence: {confidence:.2f}
created: {now}
validated_at: {now}
evidence_for: {len(evidence_for)}
evidence_against: {len(evidence_against)}
related_concepts: {concepts_str}
---
# {hypothesis_id}: {title}

## Claim
{claim}

## Evidence For
{ev_for}

## Evidence Against
{ev_against}

## Conclusion
{conclusion}

## Further Questions
{questions}
"""
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(md, encoding="utf-8")
    return filepath


# ── Dispute Writer ───────────────────────────────────────────────────

def write_dispute(
    dispute_id: str,
    articles: list[str],
    conflict_description: str,
    suggested_resolution: str,
) -> Path:
    """Write a contradiction dispute for human review."""
    filepath = vault_cfg.disputes_dir / f"{dispute_id}.md"
    articles_str = "[" + ", ".join(articles) + "]"
    now = _now_iso()

    md = f"""---
id: {dispute_id}
created: {now}
status: unresolved
articles: {articles_str}
---
# Dispute {dispute_id}

## Conflict
{conflict_description}

## Suggested Resolution
{suggested_resolution}
"""
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(md, encoding="utf-8")
    return filepath


# ── Marp Slide Writer ────────────────────────────────────────────────

def write_slides(title: str, slides: list[str]) -> Path:
    """Generate a Marp-compatible presentation."""
    safe = title.replace(" ", "_")
    filepath = vault_cfg.outputs_dir / "slides" / f"{safe}_presentation.md"
    header = "---\nmarp: true\ntheme: default\npaginate: true\n---\n\n"
    body = "\n\n---\n\n".join(slides)
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(header + body, encoding="utf-8")
    return filepath


# ── Report Writer ────────────────────────────────────────────────────

def write_report(title: str, content: str) -> Path:
    """Write an analysis/Q&A report to outputs/reports/."""
    safe = title.replace(" ", "_")
    filepath = vault_cfg.outputs_dir / "reports" / f"{safe}.md"
    now = _now_full()
    md = f"""---
title: "{title}"
generated_at: {now}
---
# {title}

{content}
"""
    os.makedirs(filepath.parent, exist_ok=True)
    filepath.write_text(md, encoding="utf-8")
    return filepath


# ── Index Updater ────────────────────────────────────────────────────

def rebuild_index() -> Path:
    """Regenerate wiki/index.md from the current vault state."""
    import glob

    now = _now_full()

    # Gather files
    concepts = sorted(glob.glob(str(vault_cfg.concepts_dir / "*.md")))
    summaries = sorted(glob.glob(str(vault_cfg.summaries_dir / "*.md")))
    hyp_supported = sorted(glob.glob(str(vault_cfg.hypotheses_dir / "supported" / "*.md")))
    hyp_refuted = sorted(glob.glob(str(vault_cfg.hypotheses_dir / "refuted" / "*.md")))
    hyp_open = sorted(glob.glob(str(vault_cfg.hypotheses_dir / "open" / "*.md")))
    disputes = sorted(glob.glob(str(vault_cfg.disputes_dir / "*.md")))

    def _link_list(paths: list[str]) -> str:
        if not paths:
            return "_None yet._\n"
        lines = []
        for p in paths:
            name = Path(p).stem
            lines.append(f"- [[{name}]]")
        return "\n".join(lines) + "\n"

    md = f"""# Research Vault — Master Index

> Auto-maintained by the Compiler Agent. Do not edit manually.

**Last updated**: {now}
**Total concepts**: {len(concepts)}
**Total summaries**: {len(summaries)}
**Total hypotheses**: {len(hyp_supported) + len(hyp_refuted) + len(hyp_open)}

---

## Concepts
{_link_list(concepts)}
## Hypotheses — Supported
{_link_list(hyp_supported)}
## Hypotheses — Refuted
{_link_list(hyp_refuted)}
## Hypotheses — Open
{_link_list(hyp_open)}
## Summaries
{_link_list(summaries)}
## Disputes
{_link_list(disputes)}
"""
    vault_cfg.index_path.write_text(md, encoding="utf-8")
    return vault_cfg.index_path
