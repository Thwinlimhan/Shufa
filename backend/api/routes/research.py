"""AutoResearch API routes — vault status, search, agents, and results."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from backend.auth.service import require_role
from backend.research.agents.compiler import compile_wiki
from backend.research.agents.hypothesis import run_hypothesis_loop, run_one_cycle
from backend.research.agents.ingestion import ingest_new_files
from backend.research.agents.linter import lint_wiki
from backend.research.agents.qa import answer_question
from backend.research.agents.scout import scout_gaps
from backend.research.results_log import read_results
from backend.research.search import init_db, reindex, search
from backend.research.vault_config import vault_cfg
from backend.research.vault_writer import rebuild_index

router = APIRouter()


# ── Vault Status ─────────────────────────────────────────────────────

@router.get("/status")
def vault_status(user: dict = Depends(require_role("viewer"))) -> dict:
    """Overview of the research vault."""
    import glob

    cfg = vault_cfg
    concepts = len(glob.glob(str(cfg.concepts_dir / "*.md")))
    summaries = len(glob.glob(str(cfg.summaries_dir / "*.md")))
    hyp_supported = len(glob.glob(str(cfg.hypotheses_dir / "supported" / "*.md")))
    hyp_refuted = len(glob.glob(str(cfg.hypotheses_dir / "refuted" / "*.md")))
    hyp_open = len(glob.glob(str(cfg.hypotheses_dir / "open" / "*.md")))
    disputes = len(glob.glob(str(cfg.disputes_dir / "*.md")))
    raw_files = sum(
        len(glob.glob(str(cfg.raw_dir / "**" / ext), recursive=True))
        for ext in ("*.md", "*.txt", "*.csv")
    )

    return {
        "vault_root": str(cfg.root),
        "raw_files": raw_files,
        "summaries": summaries,
        "concepts": concepts,
        "hypotheses": {
            "supported": hyp_supported,
            "refuted": hyp_refuted,
            "open": hyp_open,
            "total": hyp_supported + hyp_refuted + hyp_open,
        },
        "disputes": disputes,
    }


# ── Search ───────────────────────────────────────────────────────────

@router.get("/search")
def search_wiki(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_role("viewer")),
) -> list[dict]:
    """Full-text search over the wiki with BM25 ranking."""
    return search(q, limit=limit)


@router.post("/search/reindex")
def trigger_reindex(user: dict = Depends(require_role("operator"))) -> dict:
    """Rebuild the FTS5 search index."""
    init_db()
    count = reindex()
    return {"indexed": count}


# ── Results Log ──────────────────────────────────────────────────────

@router.get("/results")
def get_results(
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(require_role("viewer")),
) -> list[dict]:
    """Return hypothesis experiment results from results.tsv."""
    rows = read_results()
    return rows[-limit:]


# ── Agent Triggers ───────────────────────────────────────────────────

@router.post("/agents/ingest")
async def trigger_ingest(
    bg: BackgroundTasks,
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Trigger the Ingestion Agent to process new raw files."""
    bg.add_task(_run_async, ingest_new_files())
    return {"status": "ingestion started"}


@router.post("/agents/compile")
async def trigger_compile(
    bg: BackgroundTasks,
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Trigger the Compiler Agent."""
    bg.add_task(_run_async, compile_wiki())
    return {"status": "compilation started"}


@router.post("/agents/hypothesis")
async def trigger_hypothesis(
    bg: BackgroundTasks,
    cycles: int = Query(1, ge=1, le=100, description="Number of hypothesis cycles"),
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Run the Hypothesis Engine for N cycles."""
    bg.add_task(
        _run_async,
        run_hypothesis_loop(max_hours=24, max_cycles=cycles),
    )
    return {"status": f"hypothesis engine started for {cycles} cycle(s)"}


@router.post("/agents/lint")
async def trigger_lint(
    bg: BackgroundTasks,
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Trigger the Linter Agent."""
    bg.add_task(_run_async, lint_wiki())
    return {"status": "linter started"}


@router.post("/agents/scout")
async def trigger_scout(
    bg: BackgroundTasks,
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Trigger the Scout Agent for gap detection."""
    bg.add_task(_run_async, scout_gaps())
    return {"status": "scout started"}


# ── Q&A ──────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask_question(
    payload: dict,
    user: dict = Depends(require_role("viewer")),
) -> dict:
    """Ask a question against the knowledge base. Returns the report path."""
    question = payload.get("question", "")
    fmt = payload.get("format", "report")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    output_path = await answer_question(question, output_format=fmt)
    return {"output": str(output_path)}


# ── Index ────────────────────────────────────────────────────────────

@router.post("/index/rebuild")
def trigger_index_rebuild(
    user: dict = Depends(require_role("operator")),
) -> dict:
    """Rebuild the wiki index.md."""
    path = rebuild_index()
    return {"path": str(path)}


# ── Helpers ──────────────────────────────────────────────────────────

async def _run_async(coro: Any) -> None:
    """Run an async coroutine in a background task (FastAPI compatibility)."""
    await coro
