from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.ops.audit import list_audit_events, list_paper_cycle_events
from backend.ops.backup import backup_datastores
from backend.ops.readiness import readiness_snapshot
from backend.research.service import research_digest
from backend.worker.service import worker_health

router = APIRouter()


@router.get("/readiness")
def readiness() -> dict:
    return readiness_snapshot()


@router.get("/audit")
def audit(limit: int = 50, user: dict = Depends(require_role("operator"))) -> list[dict]:
    return list_audit_events(limit=limit)


@router.get("/paper-events")
def paper_events(limit: int = 100, user: dict = Depends(require_role("operator"))) -> list[dict]:
    return list_paper_cycle_events(limit=limit)


@router.get("/worker-health")
def worker_status(user: dict = Depends(require_role("operator"))) -> dict:
    return worker_health()


@router.post("/backup")
def create_backup(user: dict = Depends(require_role("admin"))) -> dict:
    return backup_datastores()


@router.get("/research-digest")
async def get_research_digest(user: dict = Depends(require_role("operator"))) -> dict:
    return await research_digest()
