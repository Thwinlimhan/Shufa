from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.data.service import ingest_defaults, refresh_health as refresh_health_service
from backend.data.storage import fetch_all
from backend.ops.audit import record_audit_event

router = APIRouter()


@router.get("/health")
def list_health() -> list[dict]:
    rows = fetch_all("SELECT * FROM dataset_health ORDER BY instrument_key, timeframe")
    return [dict(row) for row in rows]


@router.post("/refresh-health")
def refresh_health(user: dict = Depends(require_role("operator"))) -> list[dict]:
    result = refresh_health_service()
    record_audit_event(
        event_type="data.health_refreshed",
        entity_type="dataset_health",
        entity_id="defaults",
        payload={"rows": len(result)},
    )
    return result


@router.post("/ingest")
async def ingest(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 30)
    result = await ingest_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.ingested",
        entity_type="dataset_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result
