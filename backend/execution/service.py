from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.core.config import settings
from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.execution.adapters import adapter_for_venue
from backend.ops.audit import record_audit_event
from backend.secrets.vault import secret_or_env
from backend.worker.jobs import enqueue_job


def create_execution_ticket(
    spec_id: str,
    symbol: str,
    venue: str,
    direction: str,
    action: str,
    size_usd: float,
    requested_by: str | None = "operator",
    rationale: str | None = None,
) -> dict:
    instrument = Instrument(symbol=symbol, venue=Venue(venue), mode=VenueMode.PERP)
    adapter = adapter_for_venue(venue)
    preview = adapter.preview_order(instrument, direction, action, size_usd)
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "spec_id": spec_id,
        "symbol": symbol,
        "venue": venue,
        "direction": direction,
        "action": action,
        "size_usd": size_usd,
        "status": "pending_approval",
        "approval_mode": "manual" if settings.live_approval_mode else "direct",
        "requested_by": requested_by,
        "rationale": rationale,
        "preview_json": json.dumps(preview.__dict__),
        "broker_order_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": None,
        "submitted_at": None,
    }
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_created",
        entity_type="execution_ticket",
        entity_id=ticket["ticket_id"],
        payload={
            "spec_id": spec_id,
            "symbol": symbol,
            "venue": venue,
            "direction": direction,
            "action": action,
            "size_usd": size_usd,
        },
    )
    return hydrate_ticket(ticket)


def hydrate_ticket(row: dict) -> dict:
    item = dict(row)
    item["preview"] = json.loads(item.pop("preview_json"))
    return item


def list_execution_tickets(limit: int = 100) -> list[dict]:
    rows = fetch_all(f"SELECT * FROM execution_tickets ORDER BY created_at DESC LIMIT {int(limit)}")
    return [hydrate_ticket(dict(row)) for row in rows]


def approve_execution_ticket(ticket_id: str, approved_by: str = "operator") -> dict:
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    if ticket["status"] not in {"pending_approval", "blocked"}:
        return hydrate_ticket(ticket)

    preview = json.loads(ticket["preview_json"])
    if not preview["notional_limit_ok"]:
        ticket["status"] = "blocked"
    elif not settings.live_trading_enabled:
        ticket["status"] = "blocked"
    elif not live_secrets_status()["all_present"]:
        ticket["status"] = "blocked"
    else:
        job = enqueue_job(
            "execution_submit",
            {
                "ticket_id": ticket_id,
                "spec_id": ticket["spec_id"],
                "symbol": ticket["symbol"],
                "venue": ticket["venue"],
                "direction": ticket["direction"],
                "action": ticket["action"],
                "size_usd": float(ticket["size_usd"]),
            },
            priority=10,
        )
        ticket["status"] = "queued"
        ticket["broker_order_id"] = job["job_id"]

    ticket["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_approved",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"approved_by": approved_by, "status": ticket["status"]},
    )
    return hydrate_ticket(ticket)


def reject_execution_ticket(ticket_id: str, reason: str, rejected_by: str = "operator") -> dict:
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    ticket["status"] = "rejected"
    ticket["rationale"] = reason
    ticket["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_rejected",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"rejected_by": rejected_by, "reason": reason},
    )
    return hydrate_ticket(ticket)


def live_secrets_status() -> dict:
    per_venue = {
        "binance": bool(secret_or_env("binance_api_key") and secret_or_env("binance_api_secret")),
        "hyperliquid": bool(secret_or_env("hyperliquid_private_key") and secret_or_env("hyperliquid_account_address")),
    }
    return {"all_present": all(per_venue.values()), "venues": per_venue}


def reconcile_venue(venue: str) -> dict:
    adapter = adapter_for_venue(venue)
    summary = adapter.reconcile()
    record = {
        "reconciliation_id": str(uuid.uuid4()),
        "venue": venue,
        "status": summary["status"],
        "summary_json": json.dumps(summary),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json_record("execution_reconciliation", record, "reconciliation_id")
    record_audit_event(
        event_type="execution.reconciled",
        entity_type="execution_reconciliation",
        entity_id=record["reconciliation_id"],
        payload=summary,
    )
    return {
        "reconciliation_id": record["reconciliation_id"],
        "venue": venue,
        "status": summary["status"],
        "summary": summary,
        "created_at": record["created_at"],
    }


def process_execution_job(payload: dict) -> dict:
    ticket_id = payload["ticket_id"]
    row = fetch_one("SELECT * FROM execution_tickets WHERE ticket_id=?", [ticket_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Execution ticket not found")
    ticket = dict(row)
    instrument = Instrument(symbol=ticket["symbol"], venue=Venue(ticket["venue"]), mode=VenueMode.PERP)
    adapter = adapter_for_venue(ticket["venue"])
    submitted = adapter.submit_order(instrument, ticket["direction"], ticket["action"], float(ticket["size_usd"]))
    ticket["status"] = "submitted"
    ticket["broker_order_id"] = submitted["broker_order_id"]
    ticket["submitted_at"] = submitted["submitted_at"]
    save_json_record("execution_tickets", ticket, "ticket_id")
    record_audit_event(
        event_type="execution.ticket_submitted",
        entity_type="execution_ticket",
        entity_id=ticket_id,
        payload={"broker_order_id": ticket["broker_order_id"], "transport": submitted.get("transport", "unknown")},
    )
    return {"ticket_id": ticket_id, "submission": submitted}


def list_reconciliation(limit: int = 50) -> list[dict]:
    rows = fetch_all(f"SELECT * FROM execution_reconciliation ORDER BY created_at DESC LIMIT {int(limit)}")
    return [
        {
            "reconciliation_id": row["reconciliation_id"],
            "venue": row["venue"],
            "status": row["status"],
            "summary": json.loads(row["summary_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
