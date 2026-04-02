from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.service import require_role
from backend.core.types import Timeframe
from backend.data.service import default_instruments, latest_feature_bar_async, mark_processed, should_process_bar
from backend.data.storage import get_sqlite
from backend.ops.audit import record_audit_event
from backend.paper.activity import list_recent_orders, portfolio_snapshot
from backend.paper.runner import run_bar

router = APIRouter()


@router.get("/portfolio")
def portfolio() -> dict:
    return portfolio_snapshot()


@router.get("/orders")
def orders() -> list[dict]:
    return list_recent_orders(limit=100)


@router.post("/kill")
def kill_switch(user: dict = Depends(require_role("admin"))) -> dict:
    con = get_sqlite()
    updated = con.execute(
        """
        UPDATE paper_positions
        SET closed_at=datetime('now'), realized_pnl_usd=COALESCE(realized_pnl_usd, 0)
        WHERE closed_at IS NULL
        """
    ).rowcount
    con.commit()
    record_audit_event(
        event_type="paper.kill_switch",
        entity_type="paper_portfolio",
        entity_id="global",
        payload={"closed_positions": updated},
    )
    return {"closed_positions": updated}


@router.post("/run-once")
async def run_once(user: dict = Depends(require_role("operator"))) -> dict:
    processed: list[dict] = []
    for instrument in default_instruments():
        for timeframe in (Timeframe.M15, Timeframe.H1, Timeframe.H4):
            bar = await latest_feature_bar_async(instrument, timeframe)
            if not bar:
                continue
            job_name = f"paper:{instrument.key}:{timeframe.value}"
            if should_process_bar(job_name, bar["ts"]):
                run_bar(bar)
                mark_processed(job_name, bar["ts"])
                processed.append(
                    {
                        "instrument_key": instrument.key,
                        "timeframe": timeframe.value,
                        "ts": bar["ts"].isoformat(),
                    }
                )
    record_audit_event(
        event_type="paper.run_once",
        entity_type="paper_runner",
        entity_id="manual",
        payload={"processed": processed},
    )
    return {"processed": processed}
