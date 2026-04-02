from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.data.storage import fetch_all, save_json_record


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit_event(event_type: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    record = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload_json": json.dumps(payload),
        "created_at": _now_iso(),
    }
    save_json_record("audit_events", record, "event_id")
    return record


def list_audit_events(limit: int = 50) -> list[dict]:
    rows = fetch_all(f"SELECT * FROM audit_events ORDER BY created_at DESC LIMIT {int(limit)}")
    return [
        {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_paper_cycle_event(
    spec_id: str,
    symbol: str,
    venue: str,
    timeframe: str,
    event_type: str,
    reason: str,
    payload: dict,
) -> dict:
    record = {
        "event_id": str(uuid.uuid4()),
        "spec_id": spec_id,
        "symbol": symbol,
        "venue": venue,
        "timeframe": timeframe,
        "event_type": event_type,
        "reason": reason,
        "payload_json": json.dumps(payload),
        "created_at": _now_iso(),
    }
    save_json_record("paper_cycle_events", record, "event_id")
    record_audit_event(
        event_type=f"paper.{event_type}",
        entity_type="paper_target",
        entity_id=f"{spec_id}:{symbol}:{venue}",
        payload={"reason": reason, **payload},
    )
    return record


def list_paper_cycle_events(limit: int = 100) -> list[dict]:
    rows = fetch_all(f"SELECT * FROM paper_cycle_events ORDER BY created_at DESC LIMIT {int(limit)}")
    return [
        {
            "event_id": row["event_id"],
            "spec_id": row["spec_id"],
            "symbol": row["symbol"],
            "venue": row["venue"],
            "timeframe": row["timeframe"],
            "event_type": row["event_type"],
            "reason": row["reason"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
