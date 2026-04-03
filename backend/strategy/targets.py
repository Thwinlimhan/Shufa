from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, fetch_one, save_json_record

STATUS_PRIORITY = {
    "rejected": 0,
    "proposed": 1,
    "shortlist": 2,
    "candidate": 3,
    "promoted": 4,
}

DEFAULT_TARGET = {
    "spec_id": "builtin-range-breakout",
    "symbol": "ETH",
    "venue": "binance",
    "mode": "perp",
    "timeframe": "1h",
    "status": "candidate",
    "paper_enabled": 0,
    "notes": "Seeded as the first paper candidate based on the strongest early result.",
}


def bootstrap_default_target() -> None:
    row = fetch_one(
        "SELECT target_id FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [DEFAULT_TARGET["spec_id"], DEFAULT_TARGET["symbol"], DEFAULT_TARGET["venue"]],
    )
    if row is None:
        save_target(DEFAULT_TARGET)


def save_target(payload: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    existing = fetch_one(
        "SELECT target_id FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [payload["spec_id"], payload["symbol"], payload["venue"]],
    )
    target_id = payload.get("target_id") or (existing["target_id"] if existing else str(uuid.uuid4()))
    record = {
        "target_id": target_id,
        "spec_id": payload["spec_id"],
        "symbol": payload["symbol"],
        "venue": payload["venue"],
        "mode": payload.get("mode", "perp"),
        "timeframe": payload.get("timeframe", "1h"),
        "status": payload.get("status", "shortlist"),
        "paper_enabled": 1 if payload.get("paper_enabled") else 0,
        "notes": payload.get("notes"),
        "last_backtest_run_id": payload.get("last_backtest_run_id"),
        "updated_at": now,
    }
    save_json_record("strategy_targets", record, "target_id")
    from backend.ops.audit import record_audit_event

    record_audit_event(
        event_type="target.updated",
        entity_type="strategy_target",
        entity_id=record["target_id"],
        payload={
            "spec_id": record["spec_id"],
            "symbol": record["symbol"],
            "venue": record["venue"],
            "status": record["status"],
            "paper_enabled": record["paper_enabled"],
            "last_backtest_run_id": record["last_backtest_run_id"],
            "notes": record["notes"],
        },
    )
    return record


def update_target_state(spec_id: str, symbol: str, venue: str, status: str | None = None, paper_enabled: bool | None = None, notes: str | None = None, last_backtest_run_id: str | None = None) -> dict:
    current = fetch_one(
        "SELECT * FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [spec_id, symbol, venue],
    )
    payload = dict(current) if current else {"spec_id": spec_id, "symbol": symbol, "venue": venue}
    if status is not None:
        payload["status"] = status
    if paper_enabled is not None:
        payload["paper_enabled"] = 1 if paper_enabled else 0
    if notes is not None:
        payload["notes"] = notes
    if last_backtest_run_id is not None:
        payload["last_backtest_run_id"] = last_backtest_run_id
    payload.setdefault("mode", "perp")
    payload.setdefault("timeframe", "1h")
    return save_target(payload)


def list_targets(spec_id: str | None = None) -> list[dict]:
    if spec_id:
        rows = fetch_all("SELECT * FROM strategy_targets WHERE spec_id=? ORDER BY updated_at DESC", [spec_id])
    else:
        rows = fetch_all("SELECT * FROM strategy_targets ORDER BY updated_at DESC", [])
    return [dict(row) for row in rows]


def list_active_paper_targets() -> list[dict]:
    rows = fetch_all(
        """
        SELECT t.*, s.name, s.spec_json
        FROM strategy_targets t
        JOIN strategy_specs s ON s.spec_id = t.spec_id
        WHERE t.paper_enabled = 1
          AND t.status IN ('candidate', 'promoted')
        ORDER BY t.updated_at DESC
        """,
        [],
    )
    return [dict(row) for row in rows]


def instrument_for_target(target: dict) -> Instrument:
    return Instrument(
        symbol=target["symbol"],
        venue=Venue(target["venue"]),
        mode=VenueMode(target.get("mode", "perp")),
    )


def infer_target_status(result: dict, decision: dict) -> tuple[str, str]:
    policy = decision.get("policy", {})
    sharpe = float(result.get("sharpe") or 0.0)
    total_return_pct = float(result.get("total_return_pct") or 0.0)
    total_trades = int(result.get("total_trades") or 0)
    max_drawdown_pct = float(result.get("max_drawdown_pct") or 0.0)
    min_trade_count = int(policy.get("min_trade_count", 30) or 30)

    if decision.get("passed"):
        return "promoted", "Auto-promoted after passing the full promotion policy."

    if (
        sharpe >= 1.0
        and total_return_pct > 0
        and total_trades >= max(20, int(min_trade_count * 0.75))
        and max_drawdown_pct <= 8.0
    ):
        return "promoted", "Auto-promoted on strong Sharpe, positive return, and acceptable drawdown."

    if (
        sharpe >= 0.35
        and total_return_pct >= 0
        and total_trades >= max(12, int(min_trade_count * 0.5))
        and max_drawdown_pct <= 12.0
    ):
        return "candidate", "Auto-marked candidate after a constructive run with enough trades."

    if sharpe >= 0 and total_trades >= 8:
        return "shortlist", "Auto-shortlisted for more tuning before paper promotion."

    return "rejected", "Auto-rejected after the latest run failed the working thresholds."


def sync_target_with_backtest(spec_id: str, symbol: str, venue: str, result: dict, decision: dict) -> dict:
    status, note = infer_target_status(result, decision)
    current = fetch_one(
        "SELECT paper_enabled FROM strategy_targets WHERE spec_id=? AND symbol=? AND venue=?",
        [spec_id, symbol, venue],
    )
    paper_enabled = False if status == "rejected" else (bool(current["paper_enabled"]) if current else None)
    return update_target_state(
        spec_id=spec_id,
        symbol=symbol,
        venue=venue,
        status=status,
        paper_enabled=paper_enabled,
        notes=note,
        last_backtest_run_id=result["run_id"],
    )


def best_target_snapshot() -> dict | None:
    rows = fetch_all(
        """
        SELECT t.*, s.name, b.result_json, b.config_json, b.ran_at
        FROM strategy_targets t
        JOIN strategy_specs s ON s.spec_id = t.spec_id
        LEFT JOIN backtest_runs b ON b.run_id = t.last_backtest_run_id
        WHERE t.last_backtest_run_id IS NOT NULL
        """,
        [],
    )
    snapshots: list[dict] = []
    for row in rows:
        if row["result_json"] is None:
            continue
        result = json.loads(row["result_json"])
        config = json.loads(row["config_json"])
        snapshots.append(
            {
                "target_id": row["target_id"],
                "spec_id": row["spec_id"],
                "name": row["name"],
                "symbol": row["symbol"],
                "venue": row["venue"],
                "status": row["status"],
                "paper_enabled": row["paper_enabled"],
                "notes": row["notes"],
                "last_backtest_run_id": row["last_backtest_run_id"],
                "ran_at": row["ran_at"],
                "config": config,
                "result": result,
            }
        )
    if not snapshots:
        return None
    return max(
        snapshots,
        key=lambda item: (
            STATUS_PRIORITY.get(item["status"], 0),
            float(item["result"].get("sharpe") or 0.0),
            float(item["result"].get("total_return_pct") or 0.0),
            int(item["result"].get("total_trades") or 0),
        ),
    )


def strategy_status_summary(spec_id: str) -> dict:
    rows = list_targets(spec_id)
    if not rows:
        return {"status": "proposed", "paper_enabled_count": 0, "targets": []}
    statuses = [row["status"] for row in rows]
    if "promoted" in statuses:
        status = "promoted"
    elif "candidate" in statuses:
        status = "candidate"
    elif "shortlist" in statuses:
        status = "shortlist"
    elif all(item == "rejected" for item in statuses):
        status = "rejected"
    else:
        status = "proposed"
    return {
        "status": status,
        "paper_enabled_count": sum(int(row["paper_enabled"]) for row in rows),
        "targets": rows,
    }
