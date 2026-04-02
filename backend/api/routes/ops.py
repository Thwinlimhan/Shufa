from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.ops.audit import list_audit_events, list_paper_cycle_events
from backend.ops.readiness import readiness_snapshot

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
