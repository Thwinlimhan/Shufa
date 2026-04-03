from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from backend.core.config import settings
from backend.data.storage import fetch_all, save_json_record
from backend.execution.service import process_execution_job
from backend.ops.metrics import WORKER_QUEUE_GAUGE
from backend.ops.audit import record_audit_event
from backend.worker.jobs import claim_next_job, dead_letter_job, finish_job, list_jobs, requeue_job


def process_next_job(job_type: str | None = None) -> dict | None:
    job = claim_next_job(job_type)
    if job is None:
        return None
    attempts = int(job.get("attempt_count") or 0)
    try:
        if job["job_type"] == "execution_submit":
            result = process_execution_job(job["payload"])
            completed = finish_job(job["job_id"], "completed", result)
        else:
            completed = dead_letter_job(job["job_id"], "unsupported_job_type")
    except Exception as exc:  # pragma: no cover - runtime failure handling
        error = f"{type(exc).__name__}:{exc}"
        if attempts + 1 < settings.worker_max_retries:
            backoff_seconds = settings.worker_retry_backoff_seconds * (2 ** attempts)
            completed = requeue_job(
                job["job_id"],
                next_attempt_at=datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds),
                error=error,
            )
            completed["status"] = "retry_scheduled"
        else:
            completed = dead_letter_job(job["job_id"], error)
    record_audit_event(
        event_type="worker.job_processed",
        entity_type="job_queue",
        entity_id=completed["job_id"],
        payload={"job_type": completed["job_type"], "status": completed["status"]},
    )
    return completed


def job_metrics() -> dict:
    jobs = list_jobs(limit=500)
    dead_letters = fetch_all("SELECT COUNT(*) AS count FROM job_dead_letters", [])[0]["count"]
    queued = sum(1 for job in jobs if job["status"] == "queued")
    WORKER_QUEUE_GAUGE.set(queued)
    return {
        "queued": queued,
        "claimed": sum(1 for job in jobs if job["status"] == "claimed"),
        "completed": sum(1 for job in jobs if job["status"] == "completed"),
        "failed": sum(1 for job in jobs if job["status"] == "failed"),
        "retry_scheduled": sum(1 for job in jobs if job.get("next_attempt_at") and job["status"] == "queued"),
        "dead_letters": int(dead_letters),
    }


def update_worker_heartbeat(worker_id: str, status: str, details: dict | None = None) -> None:
    save_json_record(
        "worker_heartbeat",
        {
            "worker_id": worker_id,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "details_json": json.dumps(details or {}),
        },
        "worker_id",
    )


def worker_health() -> dict:
    now = datetime.now(timezone.utc)
    rows = [dict(row) for row in fetch_all("SELECT * FROM worker_heartbeat ORDER BY last_seen DESC", [])]
    ttl = timedelta(seconds=settings.worker_heartbeat_ttl_seconds)
    workers = []
    for row in rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        workers.append(
            {
                "worker_id": row["worker_id"],
                "last_seen": row["last_seen"],
                "status": row["status"],
                "healthy": (now - last_seen) <= ttl,
                "details": json.loads(row["details_json"] or "{}"),
            }
        )
    return {
        "generated_at": now.isoformat(),
        "ttl_seconds": settings.worker_heartbeat_ttl_seconds,
        "workers": workers,
        "healthy": bool(workers) and all(item["healthy"] for item in workers),
    }
