from __future__ import annotations

import json
from decimal import Decimal

from backend.core.types import Instrument, PaperPosition, Venue, VenueMode
from backend.data.storage import fetch_all


def _instrument_from_json(raw: str) -> Instrument:
    data = json.loads(raw)
    return Instrument(symbol=data["symbol"], venue=Venue(data["venue"]), mode=VenueMode(data["mode"]), quote=data.get("quote", "USDT"))


def list_open_positions() -> list[PaperPosition]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE closed_at IS NULL ORDER BY opened_at DESC")
    positions: list[PaperPosition] = []
    for row in rows:
        positions.append(
            PaperPosition(
                position_id=row["position_id"],
                spec_id=row["spec_id"],
                instrument=_instrument_from_json(row["instrument_json"]),
                direction=row["direction"],
                opened_at=row["opened_at"],
                entry_price=Decimal(row["entry_price"]),
                size_usd=row["size_usd"],
                unrealized_pnl_usd=row["unrealized_pnl_usd"],
                accrued_funding_usd=row["accrued_funding_usd"],
            )
        )
    return positions
