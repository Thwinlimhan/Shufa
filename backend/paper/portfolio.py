from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from backend.core.types import Instrument, PaperPosition, Venue, VenueMode
from backend.data.storage import fetch_all
from backend.paper.broker import update_unrealized_pnl


def _instrument_from_json(raw: str) -> Instrument:
    data = json.loads(raw)
    return Instrument(symbol=data["symbol"], venue=Venue(data["venue"]), mode=VenueMode(data["mode"]), quote=data.get("quote", "USDT"))


def list_open_positions() -> list[PaperPosition]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    positions: list[PaperPosition] = []
    for row in rows:
        positions.append(
            PaperPosition(
                position_id=row["position_id"],
                spec_id=row["spec_id"],
                instrument=_instrument_from_json(row["instrument_json"]),
                direction=row["direction"],
                opened_at=datetime.fromisoformat(row["opened_at"]),
                entry_price=Decimal(row["entry_price"]),
                size_usd=row["size_usd"],
                unrealized_pnl_usd=row["unrealized_pnl_usd"],
                accrued_funding_usd=row["accrued_funding_usd"],
                entry_fees_usd=float(row["entry_fees_usd"] or 0.0),
            )
        )
    return positions


def mark_to_market(symbol: str, venue: str, price: float) -> int:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC", [])
    updated = 0
    for row in rows:
        inst = _instrument_from_json(row["instrument_json"])
        if inst.symbol != symbol or inst.venue.value != venue:
            continue
        entry = float(row["entry_price"])
        raw_pnl = ((price - entry) / entry) * float(row["size_usd"]) if entry else 0.0
        if row["direction"] == "short":
            raw_pnl = -raw_pnl
        unrealized = raw_pnl + float(row["accrued_funding_usd"] or 0.0) - float(row["entry_fees_usd"] or 0.0)
        update_unrealized_pnl(row["position_id"], unrealized)
        updated += 1
    return updated
