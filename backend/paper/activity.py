from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data.storage import fetch_all, get_mark_price
from backend.ops.metrics import PAPER_POSITION_GAUGE
from backend.strategy.targets import list_active_paper_targets


def _decode_instrument(raw_json: str) -> dict:
    inst = json.loads(raw_json)
    return {
        "symbol": inst["symbol"],
        "venue": inst["venue"],
        "mode": inst.get("mode", "perp"),
        "quote": inst.get("quote", "USDT"),
    }


def list_open_positions() -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    positions: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        instrument = Instrument(symbol=item["symbol"], venue=Venue(item["venue"]), mode=VenueMode(item.get("mode", "perp")))
        mark = get_mark_price(instrument.key)
        if mark:
            item["mark_price"] = mark["price"]
            item["mark_ts"] = mark["ts"]
        positions.append(item)
    return positions


def list_recent_positions(limit: int = 100) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions ORDER BY COALESCE(closed_at, opened_at) DESC LIMIT ?", [int(limit)])
    positions: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        positions.append(item)
    return positions


def list_recent_orders(limit: int = 50) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_orders ORDER BY COALESCE(filled_at, triggered_at) DESC LIMIT ?", [int(limit)])
    orders: list[dict] = []
    for row in rows:
        item = dict(row)
        item.update(_decode_instrument(item.pop("instrument_json")))
        orders.append(item)
    return orders


def summarize_target_activity(limit: int = 50) -> tuple[list[dict], list[dict], list[dict]]:
    active_targets = [
        {
            "spec_id": row["spec_id"],
            "name": row["name"],
            "symbol": row["symbol"],
            "venue": row["venue"],
            "status": row["status"],
            "paper_enabled": row["paper_enabled"],
            "last_backtest_run_id": row["last_backtest_run_id"],
        }
        for row in list_active_paper_targets()
    ]
    open_positions = list_open_positions()
    recent_positions = list_recent_positions(limit)
    recent_orders = list_recent_orders(limit)

    activity: list[dict] = []
    for target in active_targets:
        key = (target["spec_id"], target["symbol"], target["venue"])
        target_open_positions = [
            row for row in open_positions if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        target_positions = [
            row for row in recent_positions if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        target_orders = [
            row for row in recent_orders if (row["spec_id"], row["symbol"], row["venue"]) == key
        ]
        last_order = target_orders[0] if target_orders else None
        event_times = [
            row["filled_at"] or row["triggered_at"]
            for row in target_orders
            if row.get("filled_at") or row.get("triggered_at")
        ]
        event_times.extend(
            row["closed_at"] or row["opened_at"]
            for row in target_positions
            if row.get("closed_at") or row.get("opened_at")
        )
        last_event_at = max(event_times) if event_times else None
        realized_pnl_usd = sum(float(row.get("realized_pnl_usd") or 0.0) for row in target_positions)
        activity.append(
            {
                **target,
                "open_positions": len(target_open_positions),
                "recent_orders": len(target_orders),
                "last_event_at": last_event_at,
                "last_order_action": last_order["action"] if last_order else None,
                "last_order_status": last_order["status"] if last_order else None,
                "last_direction": last_order["direction"] if last_order else None,
                "last_fill_price": last_order["fill_price"] if last_order else None,
                "realized_pnl_usd": realized_pnl_usd,
            }
        )
    activity.sort(
        key=lambda item: (
            datetime.fromisoformat(item["last_event_at"])
            if item["last_event_at"]
            else datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )
    return active_targets, activity, recent_orders


def portfolio_snapshot(limit: int = 50) -> dict:
    positions = list_open_positions()
    PAPER_POSITION_GAUGE.set(len(positions))
    active_targets, target_activity, recent_orders = summarize_target_activity(limit=limit)
    total_unrealized = sum(float(position["unrealized_pnl_usd"]) for position in positions)
    return {
        "positions": positions,
        "orders": recent_orders,
        "active_targets": active_targets,
        "target_activity": target_activity,
        "total_unrealized_pnl_usd": total_unrealized,
    }
