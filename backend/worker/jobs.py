from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.data.storage import fetch_all, fetch_one, get_sqlite, save_json_record


def enqueue_job(job_type: str, payload: dict, priority: int = 100) -> dict:
    record = {
        "job_id": str(uuid.uuid4()),
        "job_type": job_type,
        "status": "queued",
        "payload_json": json.dumps(payload),
        "result_json": None,
        "priority": priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claimed_at": None,
        "finished_at": None,
        "attempt_count": 0,
        "last_error": None,
        "next_attempt_at": None,
    }
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def hydrate_job(row: dict) -> dict:
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json"))
    item["result"] = json.loads(item["result_json"]) if item.get("result_json") else None
    item.pop("result_json", None)
    return item


def list_jobs(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM job_queue ORDER BY created_at DESC LIMIT ?", [int(limit)])
    return [hydrate_job(dict(row)) for row in rows]


def claim_next_job(job_type: str | None = None) -> dict | None:
    con = get_sqlite()
    if job_type:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued' AND job_type=?
              AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            [job_type, datetime.now(timezone.utc).isoformat()],
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued'
              AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            [datetime.now(timezone.utc).isoformat()],
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["status"] = "claimed"
    record["claimed_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def finish_job(job_id: str, status: str, result: dict) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = status
    record["result_json"] = json.dumps(result)
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def requeue_job(job_id: str, *, next_attempt_at: datetime, error: str) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = "queued"
    record["claimed_at"] = None
    record["attempt_count"] = int(record.get("attempt_count") or 0) + 1
    record["last_error"] = error
    record["next_attempt_at"] = next_attempt_at.isoformat()
    save_json_record("job_queue", record, "job_id")
    return hydrate_job(record)


def dead_letter_job(job_id: str, error: str) -> dict:
    row = fetch_one("SELECT * FROM job_queue WHERE job_id=?", [job_id])
    if row is None:
        raise ValueError("job_not_found")
    record = dict(row)
    record["status"] = "failed"
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["last_error"] = error
    save_json_record("job_queue", record, "job_id")
    dead_letter = {
        "dead_letter_id": str(uuid.uuid4()),
        "job_id": record["job_id"],
        "job_type": record["job_type"],
        "payload_json": record["payload_json"],
        "last_error": error,
        "failed_at": record["finished_at"],
    }
    save_json_record("job_dead_letters", dead_letter, "dead_letter_id")
    return hydrate_job(record)


def list_dead_letters(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM job_dead_letters ORDER BY failed_at DESC LIMIT ?", [int(limit)])
    return [dict(row) for row in rows]
