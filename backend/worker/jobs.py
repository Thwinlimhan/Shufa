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
    rows = fetch_all(f"SELECT * FROM job_queue ORDER BY created_at DESC LIMIT {int(limit)}")
    return [hydrate_job(dict(row)) for row in rows]


def claim_next_job(job_type: str | None = None) -> dict | None:
    con = get_sqlite()
    if job_type:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued' AND job_type=?
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            [job_type],
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT * FROM job_queue
            WHERE status='queued'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """
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
