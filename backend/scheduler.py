from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from backend.core.types import Timeframe
from backend.data.service import default_instruments, ingest_defaults, latest_feature_bar_async, mark_processed, refresh_health, should_process_bar
from backend.worker.service import process_next_job
from backend.paper.runner import run_bar

log = structlog.get_logger()
scheduler = AsyncIOScheduler()


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
    refresh_health()


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


def setup_scheduler() -> AsyncIOScheduler:
    scheduler.add_job(on_15m_bar_close, CronTrigger(minute="1,16,31,46"), id="bar_15m", replace_existing=True)
    scheduler.add_job(run_quality_checks, CronTrigger(minute=5), id="quality_check", replace_existing=True)
    scheduler.add_job(repair_gaps, CronTrigger(hour="0,4,8,12,16,20", minute=10), id="gap_repair", replace_existing=True)
    scheduler.add_job(process_worker_queue, CronTrigger(minute="*/2"), id="worker_queue", replace_existing=True)
    scheduler.start()
    return scheduler
