from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.schemas import (
    BarIngestSummaryResponse,
    DatasetHealthRow,
    FundingIngestSummaryResponse,
    MarketContextIngestSummaryResponse,
    MarketMarkResponse,
)
from backend.auth.service import require_role
from backend.data.service import (
    ingest_defaults,
    ingest_funding_defaults,
    ingest_market_context_defaults,
    refresh_health as refresh_health_service,
)
from backend.data.storage import fetch_all
from backend.ops.audit import record_audit_event

router = APIRouter()


@router.get("/health", response_model=list[DatasetHealthRow], summary="Dataset health snapshot")
def list_health() -> list[dict]:
    rows = fetch_all("SELECT * FROM dataset_health ORDER BY instrument_key, timeframe", [])
    return [dict(row) for row in rows]


@router.post("/refresh-health", response_model=list[DatasetHealthRow], summary="Run and persist health checks")
def refresh_health(user: dict = Depends(require_role("operator"))) -> list[dict]:
    result = refresh_health_service()
    record_audit_event(
        event_type="data.health_refreshed",
        entity_type="dataset_health",
        entity_id="defaults",
        payload={"rows": len(result)},
    )
    return result


@router.post("/ingest", response_model=list[BarIngestSummaryResponse], summary="Ingest default OHLCV bars")
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


@router.post("/funding/ingest", response_model=list[FundingIngestSummaryResponse], summary="Ingest funding rates")
async def ingest_funding(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 14)
    result = await ingest_funding_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.funding_ingested",
        entity_type="funding_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result


@router.post(
    "/market-context/ingest",
    response_model=list[MarketContextIngestSummaryResponse],
    summary="Ingest market context (OI, taker flow, liquidations)",
)
async def ingest_market_context(payload: dict | None = None, user: dict = Depends(require_role("operator"))) -> list[dict]:
    lookback_days = (payload or {}).get("lookback_days", 14)
    result = await ingest_market_context_defaults(lookback_days=lookback_days)
    record_audit_event(
        event_type="data.market_context_ingested",
        entity_type="market_context_batch",
        entity_id=f"defaults:{lookback_days}",
        payload={"lookback_days": lookback_days, "rows": len(result)},
    )
    return result


@router.get("/marks", response_model=list[MarketMarkResponse], summary="Latest mark prices")
def latest_marks(limit: int = 50, user: dict = Depends(require_role("operator"))) -> list[dict]:
    rows = fetch_all("SELECT * FROM market_marks ORDER BY ts DESC LIMIT ?", [int(limit)])
    return [dict(row) for row in rows]
