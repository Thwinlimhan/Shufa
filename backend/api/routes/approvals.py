from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.data.storage import fetch_all, fetch_one, get_sqlite

router = APIRouter()


@router.get("")
def list_approvals() -> list[dict]:
    rows = fetch_all("SELECT * FROM promotion_decisions ORDER BY decided_at DESC")
    return [dict(row) for row in rows]


@router.post("/{decision_id}/approve")
def approve(decision_id: str, user: dict = Depends(require_role("admin"))) -> dict:
    row = fetch_one("SELECT * FROM promotion_decisions WHERE decision_id=?", [decision_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    con = get_sqlite()
    con.execute(
        """
        UPDATE promotion_decisions
        SET passed=1, approved_by='operator'
        WHERE decision_id=?
        """,
        [decision_id],
    )
    con.execute(
        """
        UPDATE strategy_specs
        SET status='promoted'
        WHERE spec_id=?
        """,
        [row["spec_id"]],
    )
    con.commit()
    return {"ok": True, "decision_id": decision_id}
