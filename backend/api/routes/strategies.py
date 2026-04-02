from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.core.types import dataclass_to_dict, strategy_spec_from_dict
from backend.data.storage import fetch_one, save_json_record
from backend.ops.audit import record_audit_event
from backend.strategy.registry import list_specs
from backend.strategy.targets import list_targets, update_target_state
from backend.strategy.validator import validate_spec

router = APIRouter()

@router.get("")
def list_strategies() -> list[dict]:
    return list_specs()


@router.get("/{spec_id}")
def get_strategy(spec_id: str) -> dict:
    row = fetch_one("SELECT * FROM strategy_specs WHERE spec_id=?", [spec_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return dict(row)


@router.post("")
def create_strategy(spec_payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec = strategy_spec_from_dict(spec_payload)
    validation = validate_spec(spec)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.errors)
    save_json_record(
        "strategy_specs",
        {
            "spec_id": spec.spec_id,
            "name": spec.name,
            "version": spec.version,
            "parent_id": spec.parent_id,
            "status": "proposed",
            "spec_json": json.dumps(dataclass_to_dict(spec)),
            "created_at": spec.created_at.isoformat(),
        },
        "spec_id",
    )
    record_audit_event(
        event_type="strategy.created",
        entity_type="strategy_spec",
        entity_id=spec.spec_id,
        payload={"name": spec.name, "version": spec.version, "hypothesis": spec.hypothesis},
    )
    return {"ok": True, "spec_id": spec.spec_id}


@router.get("/{spec_id}/targets")
def get_targets(spec_id: str) -> list[dict]:
    return list_targets(spec_id)


@router.post("/{spec_id}/targets")
def upsert_target(spec_id: str, payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    symbol = payload["symbol"]
    venue = payload["venue"]
    return update_target_state(
        spec_id=spec_id,
        symbol=symbol,
        venue=venue,
        status=payload.get("status"),
        paper_enabled=payload.get("paper_enabled"),
        notes=payload.get("notes"),
        last_backtest_run_id=payload.get("last_backtest_run_id"),
    )
