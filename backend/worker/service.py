from __future__ import annotations

from backend.execution.service import process_execution_job
from backend.ops.audit import record_audit_event
from backend.worker.jobs import claim_next_job, finish_job, list_jobs


def process_next_job(job_type: str | None = None) -> dict | None:
    job = claim_next_job(job_type)
    if job is None:
        return None
    if job["job_type"] == "execution_submit":
        result = process_execution_job(job["payload"])
        completed = finish_job(job["job_id"], "completed", result)
    else:
        completed = finish_job(job["job_id"], "failed", {"error": "unsupported_job_type"})
    record_audit_event(
        event_type="worker.job_processed",
        entity_type="job_queue",
        entity_id=completed["job_id"],
        payload={"job_type": completed["job_type"], "status": completed["status"]},
    )
    return completed


def job_metrics() -> dict:
    jobs = list_jobs(limit=500)
    return {
        "queued": sum(1 for job in jobs if job["status"] == "queued"),
        "claimed": sum(1 for job in jobs if job["status"] == "claimed"),
        "completed": sum(1 for job in jobs if job["status"] == "completed"),
        "failed": sum(1 for job in jobs if job["status"] == "failed"),
    }
