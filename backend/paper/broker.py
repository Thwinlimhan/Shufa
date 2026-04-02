from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from backend.core.config import settings
from backend.core.types import Instrument, PaperOrder, PaperPosition, StrategySpec
from backend.data.storage import get_sqlite
from backend.ops.audit import record_audit_event


def submit_order(spec: StrategySpec, inst: Instrument, direction: str, action: str, size_usd: float, triggered_at: datetime) -> PaperOrder:
    order = PaperOrder(
        order_id=str(uuid.uuid4()),
        spec_id=spec.spec_id,
        instrument=inst,
        direction=direction,
        action=action,
        triggered_at=triggered_at,
        size_usd=size_usd,
    )
    con = get_sqlite()
    con.execute(
        """
        INSERT INTO paper_orders (
            order_id, spec_id, instrument_json, direction, action,
            triggered_at, size_usd, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order.order_id,
            order.spec_id,
            json.dumps({"symbol": inst.symbol, "venue": inst.venue.value, "mode": inst.mode.value, "quote": inst.quote}),
            order.direction,
            order.action,
            order.triggered_at.isoformat(),
            order.size_usd,
            order.status,
        ),
    )
    con.commit()
    record_audit_event(
        event_type="paper.order_submitted",
        entity_type="paper_order",
        entity_id=order.order_id,
        payload={
            "spec_id": order.spec_id,
            "symbol": inst.symbol,
            "venue": inst.venue.value,
            "direction": order.direction,
            "action": order.action,
            "size_usd": order.size_usd,
        },
    )
    return order


def fill_order(order: PaperOrder, bar_close_price: float) -> PaperOrder:
    slip_mult = settings.paper_slippage_bps / 10_000
    if order.action == "open" and order.direction == "long":
        fill = bar_close_price * (1 + slip_mult)
    elif order.action == "open" and order.direction == "short":
        fill = bar_close_price * (1 - slip_mult)
    else:
        fill = bar_close_price
    order.fill_price = Decimal(str(round(fill, 6)))
    order.filled_at = datetime.now(timezone.utc)
    order.status = "filled"
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_orders
        SET fill_price=?, filled_at=?, status=?
        WHERE order_id=?
        """,
        (str(order.fill_price), order.filled_at.isoformat(), order.status, order.order_id),
    )
    con.commit()
    record_audit_event(
        event_type="paper.order_filled",
        entity_type="paper_order",
        entity_id=order.order_id,
        payload={
            "spec_id": order.spec_id,
            "symbol": order.instrument.symbol,
            "venue": order.instrument.venue.value,
            "fill_price": str(order.fill_price),
            "status": order.status,
        },
    )
    return order


def open_position(order: PaperOrder) -> PaperPosition:
    position = PaperPosition(
        position_id=str(uuid.uuid4()),
        spec_id=order.spec_id,
        instrument=order.instrument,
        direction=order.direction,
        opened_at=order.filled_at or datetime.now(timezone.utc),
        entry_price=order.fill_price or Decimal("0"),
        size_usd=order.size_usd,
    )
    con = get_sqlite()
    con.execute(
        """
        INSERT INTO paper_positions (
            position_id, spec_id, instrument_json, direction, opened_at,
            entry_price, size_usd, unrealized_pnl_usd, accrued_funding_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            position.position_id,
            position.spec_id,
            json.dumps({"symbol": position.instrument.symbol, "venue": position.instrument.venue.value, "mode": position.instrument.mode.value, "quote": position.instrument.quote}),
            position.direction,
            position.opened_at.isoformat(),
            str(position.entry_price),
            position.size_usd,
            position.unrealized_pnl_usd,
            position.accrued_funding_usd,
        ),
    )
    con.commit()
    record_audit_event(
        event_type="paper.position_opened",
        entity_type="paper_position",
        entity_id=position.position_id,
        payload={
            "spec_id": position.spec_id,
            "symbol": position.instrument.symbol,
            "venue": position.instrument.venue.value,
            "direction": position.direction,
            "entry_price": str(position.entry_price),
            "size_usd": position.size_usd,
        },
    )
    return position


def close_position(position: PaperPosition, fill_price: float) -> float:
    entry = float(position.entry_price)
    raw_pnl = ((fill_price - entry) / entry) * position.size_usd if entry else 0.0
    if position.direction == "short":
        raw_pnl = -raw_pnl
    realized = raw_pnl + position.accrued_funding_usd
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_positions
        SET closed_at=?, close_price=?, realized_pnl_usd=?
        WHERE position_id=?
        """,
        (datetime.now(timezone.utc).isoformat(), str(round(fill_price, 6)), realized, position.position_id),
    )
    con.commit()
    record_audit_event(
        event_type="paper.position_closed",
        entity_type="paper_position",
        entity_id=position.position_id,
        payload={
            "spec_id": position.spec_id,
            "symbol": position.instrument.symbol,
            "venue": position.instrument.venue.value,
            "close_price": round(fill_price, 6),
            "realized_pnl_usd": realized,
        },
    )
    return realized


def update_unrealized_pnl(position_id: str, unrealized_pnl_usd: float) -> None:
    con = get_sqlite()
    con.execute(
        """
        UPDATE paper_positions
        SET unrealized_pnl_usd=?
        WHERE position_id=?
        """,
        (unrealized_pnl_usd, position_id),
    )
    con.commit()
