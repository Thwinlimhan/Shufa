from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from backend.core.config import settings
from backend.core.types import Timeframe
from backend.data.service import (
    default_instruments,
    ingest_defaults,
    ingest_funding_defaults,
    ingest_mark_price,
    ingest_market_context_defaults,
    latest_feature_bar_async,
    mark_processed,
    refresh_health,
    should_process_bar,
)
from backend.data.streams import binance_ws, hyperliquid_ws
from backend.ops.alerts import notify_event
from backend.ops.backup import backup_datastores
from backend.ops.readiness import readiness_snapshot
from backend.research.service import research_digest
from backend.worker.service import process_next_job
from backend.paper.runner import run_bar

# AutoResearch agent imports (lazy to avoid circular imports)
_vault_agents_imported = False


def _ensure_vault_imports():
    global _vault_agents_imported
    if _vault_agents_imported:
        return
    _vault_agents_imported = True

log = structlog.get_logger()
scheduler = AsyncIOScheduler()
_stream_tasks: list[asyncio.Task] = []


async def on_15m_bar_close() -> None:
    log.info("15m bar close tick")
    await ingest_defaults(lookback_days=3)
    processed = 0
    for instrument in default_instruments():
        for timeframe in (Timeframe.M15, Timeframe.H1, Timeframe.H4):
            bar = await latest_feature_bar_async(instrument, timeframe)
            if not bar:
                continue
            job_name = f"paper:{instrument.key}:{timeframe.value}"
            if should_process_bar(job_name, bar["ts"]):
                run_bar(bar)
                mark_processed(job_name, bar["ts"])
                processed += 1
    log.info("paper cycle finished", processed=processed)


async def run_quality_checks() -> None:
    log.info("quality check tick")
    snapshot = refresh_health()
    issues = [row for row in snapshot if row["quality"] != "healthy"]
    if issues:
        notify_event("health_degraded", "Dataset health degraded", {"issues": issues[:10], "issue_count": len(issues)})
    readiness = readiness_snapshot()
    if readiness["summary"]["blockers"]:
        notify_event(
            "health_degraded",
            "Readiness blockers detected",
            {"blockers": readiness["summary"]["blockers"][:10], "generated_at": readiness["generated_at"]},
        )


async def repair_gaps() -> None:
    log.info("gap repair tick")
    await ingest_defaults(lookback_days=10)


async def process_worker_queue() -> None:
    log.info("worker queue tick")
    processed = 0
    while True:
        job = process_next_job()
        if job is None:
            break
        processed += 1
    log.info("worker queue finished", processed=processed)


def run_backup() -> None:
    summary = backup_datastores()
    log.info("backup completed", **summary)


async def mark_to_market_refresh() -> None:
    # Keep unrealized PnL fresh even if streams are disabled or disconnected.
    instruments = default_instruments()
    for inst in instruments:
        bar = await latest_feature_bar_async(inst, Timeframe.M15, lookback_bars=50)
        if not bar:
            continue
        ingest_mark_price(inst.venue.value, inst.symbol, float(bar["close"]))


async def ingest_funding_updates() -> None:
    summaries = await ingest_funding_defaults(lookback_days=3)
    log.info("funding ingestion tick", updated=len(summaries))


async def ingest_market_context_updates() -> None:
    summaries = await ingest_market_context_defaults(lookback_days=7)
    log.info("market context ingestion tick", updated=len(summaries))


async def run_research_digest() -> None:
    digest = await research_digest()
    log.info("research digest", analysis=digest.get("analysis", {}))


# ── AutoResearch Scheduled Jobs ──────────────────────────────────────

async def vault_ingestion_check() -> None:
    """Watch raw/ for un-ingested files and trigger ingestion agent."""
    from backend.research.agents.ingestion import ingest_new_files
    results = await ingest_new_files()
    log.info("vault ingestion check", ingested=len(results))


async def vault_compiler_daily() -> None:
    """Daily concept compilation pass."""
    from backend.research.agents.compiler import compile_wiki
    count = await compile_wiki()
    log.info("vault compiler", concepts_written=count)


async def vault_linter_weekly() -> None:
    """Weekly wiki health check."""
    from backend.research.agents.linter import lint_wiki
    summary = await lint_wiki()
    log.info("vault linter", issues=summary.get("total_issues", 0))


async def vault_scout_weekly() -> None:
    """Weekly gap detection."""
    from backend.research.agents.scout import scout_gaps
    report = await scout_gaps()
    log.info("vault scout", report=str(report))


async def _stream_loop(venue: str, symbols: list[str]) -> None:
    async def callback(payload: dict) -> None:
        ingest_mark_price(payload["venue"], payload["symbol"], float(payload["price"]), payload.get("ts"))

    while True:
        try:
            if venue == "binance":
                await binance_ws.stream_mark_prices(symbols, callback)
            else:
                await hyperliquid_ws.stream_mark_prices(symbols, callback)
        except Exception as exc:  # pragma: no cover - network runtime
            log.warning("market stream disconnected", venue=venue, error=str(exc))
            await asyncio.sleep(2)


def _ensure_stream_tasks() -> None:
    if not settings.market_streams_enabled:
        return
    if _stream_tasks:
        return
    symbols = sorted({inst.symbol for inst in default_instruments()})
    _stream_tasks.append(asyncio.create_task(_stream_loop("binance", symbols)))
    _stream_tasks.append(asyncio.create_task(_stream_loop("hyperliquid", symbols)))
    log.info("market streams started", symbols=symbols)


def setup_scheduler() -> AsyncIOScheduler:
    if scheduler.running:
        return scheduler
    scheduler.add_job(on_15m_bar_close, CronTrigger(minute="1,16,31,46"), id="bar_15m", replace_existing=True)
    scheduler.add_job(run_quality_checks, CronTrigger(minute=5), id="quality_check", replace_existing=True)
    scheduler.add_job(repair_gaps, CronTrigger(hour="0,4,8,12,16,20", minute=10), id="gap_repair", replace_existing=True)
    scheduler.add_job(process_worker_queue, CronTrigger(minute="*/2"), id="worker_queue", replace_existing=True)
    scheduler.add_job(run_backup, CronTrigger(hour=0, minute=30), id="backup_job", replace_existing=True)
    scheduler.add_job(mark_to_market_refresh, IntervalTrigger(seconds=5), id="mark_to_market_refresh", replace_existing=True)
    scheduler.add_job(ingest_funding_updates, CronTrigger(minute=7), id="funding_hourly", replace_existing=True)
    scheduler.add_job(ingest_market_context_updates, CronTrigger(minute=9), id="market_context_hourly", replace_existing=True)
    scheduler.add_job(run_research_digest, CronTrigger(hour=9, minute=0), id="research_digest", replace_existing=True)
    # AutoResearch vault jobs
    scheduler.add_job(vault_ingestion_check, IntervalTrigger(minutes=5), id="vault_ingestion", replace_existing=True)
    scheduler.add_job(vault_compiler_daily, CronTrigger(hour=3, minute=0), id="vault_compiler", replace_existing=True)
    scheduler.add_job(vault_linter_weekly, CronTrigger(hour=4, minute=0, day_of_week="sun"), id="vault_linter", replace_existing=True)
    scheduler.add_job(vault_scout_weekly, CronTrigger(hour=5, minute=0, day_of_week="sun"), id="vault_scout", replace_existing=True)
    scheduler.start()
    _ensure_stream_tasks()
    return scheduler
