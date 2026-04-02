from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.execution.service import (
    approve_execution_ticket,
    create_execution_ticket,
    list_execution_tickets,
    list_reconciliation,
    live_secrets_status,
    reconcile_venue,
    reject_execution_ticket,
)
from backend.worker.jobs import list_jobs
from backend.worker.service import job_metrics, process_next_job

router = APIRouter()


@router.get("/tickets")
def tickets(limit: int = 100) -> list[dict]:
    return list_execution_tickets(limit=limit)


@router.post("/tickets")
def create_ticket(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return create_execution_ticket(
        spec_id=payload["spec_id"],
        symbol=payload["symbol"],
        venue=payload["venue"],
        direction=payload["direction"],
        action=payload.get("action", "open"),
        size_usd=float(payload.get("size_usd", 1000.0)),
        requested_by=payload.get("requested_by", user["display_name"]),
        rationale=payload.get("rationale"),
    )


@router.post("/tickets/{ticket_id}/approve")
def approve_ticket(ticket_id: str, payload: dict | None = None, user: dict = Depends(require_role("admin"))) -> dict:
    approved_by = (payload or {}).get("approved_by", user["display_name"])
    return approve_execution_ticket(ticket_id, approved_by=approved_by)


@router.post("/tickets/{ticket_id}/reject")
def reject_ticket(ticket_id: str, payload: dict | None = None, user: dict = Depends(require_role("admin"))) -> dict:
    reason = (payload or {}).get("reason", "operator_rejected")
    rejected_by = (payload or {}).get("rejected_by", user["display_name"])
    return reject_execution_ticket(ticket_id, reason=reason, rejected_by=rejected_by)


@router.get("/secrets")
def secrets() -> dict:
    return live_secrets_status()


@router.get("/reconciliation")
def reconciliation(limit: int = 50) -> list[dict]:
    return list_reconciliation(limit=limit)


@router.post("/reconciliation/run")
def run_reconciliation(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> dict:
    venue = (payload or {}).get("venue", "binance")
    return reconcile_venue(venue)


@router.get("/jobs")
def jobs(limit: int = 100) -> list[dict]:
    return list_jobs(limit=limit)


@router.get("/jobs/metrics")
def metrics() -> dict:
    return job_metrics()


@router.post("/jobs/process")
def process_job(payload: dict | None = None, user: dict = Depends(require_role("admin"))) -> dict:
    job_type = (payload or {}).get("job_type")
    result = process_next_job(job_type=job_type)
    return {"job": result}
