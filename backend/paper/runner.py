from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from backend.core.config import settings
from backend.core.types import Instrument, PaperPosition, StrategySpec, Venue, VenueMode, strategy_spec_from_dict
from backend.data.storage import fetch_all
from backend.ops.audit import record_paper_cycle_event
from backend.paper.broker import close_position, fill_order, open_position, submit_order
from backend.strategy.engine import get_signal
from backend.strategy.targets import instrument_for_target, list_active_paper_targets


def run_bar(current_bar: dict) -> None:
    targets = _load_active_targets()
    for target in targets:
        spec = target["spec"]
        target_inst = target["instrument"]
        if spec.primary_timeframe.value != current_bar["timeframe"]:
            continue
        if current_bar["symbol"] != target_inst.symbol or current_bar["venue"] != target_inst.venue.value:
            continue
        target_key = {
            "spec_id": spec.spec_id,
            "symbol": target_inst.symbol,
            "venue": target_inst.venue.value,
            "timeframe": current_bar["timeframe"],
        }
        signal = get_signal(spec, current_bar)
        positions = _get_open_positions(spec.spec_id, target_inst)
        close_price = float(current_bar["close"])
        if not settings.paper_trading_enabled:
            _log_cycle_event(target_key, "skipped", "paper_trading_disabled", {"signal": signal})
            continue
        risk_reason = _risk_block_reason(spec, current_bar)
        if risk_reason:
            _log_cycle_event(target_key, "skipped", risk_reason, {"signal": signal, "close_price": close_price})
            continue
        for position in positions:
            if position["direction"] != signal:
                realized = close_position(_row_to_position(position), close_price)
                _log_cycle_event(
                    target_key,
                    "position_closed",
                    "signal_flip",
                    {"position_id": position["position_id"], "realized_pnl_usd": realized},
                )
            else:
                entry = float(position["entry_price"])
                raw_pnl = ((close_price - entry) / entry) * float(position["size_usd"]) if entry else 0.0
                if position["direction"] == "short":
                    raw_pnl = -raw_pnl
                unrealized = raw_pnl + float(position["accrued_funding_usd"])
                from backend.paper.broker import update_unrealized_pnl
                update_unrealized_pnl(position["position_id"], unrealized)
                
        if signal in {"long", "short"} and not positions:
            size_usd = spec.sizing.fixed_notional_usd or 1_000.0
            order = submit_order(spec, target_inst, signal, "open", size_usd, current_bar["ts"])
            filled = fill_order(order, close_price)
            position = open_position(filled)
            _log_cycle_event(
                target_key,
                "position_opened",
                "signal_entry",
                {
                    "order_id": order.order_id,
                    "position_id": position.position_id,
                    "direction": signal,
                    "fill_price": str(filled.fill_price),
                    "size_usd": size_usd,
                },
            )
        elif signal in {"long", "short"} and positions:
            _log_cycle_event(target_key, "skipped", "position_already_open", {"signal": signal, "open_positions": len(positions)})
        else:
            _log_cycle_event(target_key, "skipped", "no_signal", {"signal": signal})


def _load_active_targets() -> list[dict]:
    rows = list_active_paper_targets()
    return [
        {
            "spec": strategy_spec_from_dict(json.loads(row["spec_json"])),
            "instrument": instrument_for_target(row),
            "target": row,
        }
        for row in rows
    ]


def _risk_block_reason(spec: StrategySpec, current_bar: dict) -> str | None:
    volume_quote = float(current_bar.get("volume_quote") or 0.0)
    if volume_quote < spec.execution.min_volume_usd:
        return "min_volume_not_met"
    if _open_position_count() >= settings.paper_max_open_positions:
        return "max_open_positions_reached"
    daily_realized = _daily_realized_pnl()
    if daily_realized <= -abs(settings.paper_daily_loss_limit_usd):
        return "daily_loss_limit_breached"
    return None


def _open_position_count() -> int:
    row = fetch_all("SELECT COUNT(*) AS count FROM paper_positions WHERE closed_at IS NULL")
    return int(row[0]["count"])


def _daily_realized_pnl() -> float:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    row = fetch_all(
        "SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total FROM paper_positions WHERE closed_at IS NOT NULL AND closed_at>=?",
        [start_of_day],
    )
    return float(row[0]["total"] or 0.0)


def _log_cycle_event(target_key: dict, event_type: str, reason: str, payload: dict) -> None:
    record_paper_cycle_event(
        spec_id=target_key["spec_id"],
        symbol=target_key["symbol"],
        venue=target_key["venue"],
        timeframe=target_key["timeframe"],
        event_type=event_type,
        reason=reason,
        payload=payload,
    )


def _get_open_positions(spec_id: str, instrument: Instrument) -> list[dict]:
    rows = fetch_all("SELECT * FROM paper_positions WHERE spec_id=? AND closed_at IS NULL", [spec_id])
    filtered = []
    for row in rows:
        item = dict(row)
        inst_json = json.loads(item["instrument_json"])
        if inst_json["symbol"] == instrument.symbol and inst_json["venue"] == instrument.venue.value:
            filtered.append(item)
    return filtered


def _row_to_position(row: dict) -> PaperPosition:
    inst_json = json.loads(row["instrument_json"])
    inst = Instrument(
        symbol=inst_json["symbol"],
        venue=Venue(inst_json["venue"]),
        mode=VenueMode(inst_json["mode"]),
        quote=inst_json.get("quote", "USDT"),
    )
    return PaperPosition(
        position_id=row["position_id"],
        spec_id=row["spec_id"],
        instrument=inst,
        direction=row["direction"],
        opened_at=datetime.fromisoformat(row["opened_at"]),
        entry_price=Decimal(row["entry_price"]),
        size_usd=row["size_usd"],
        unrealized_pnl_usd=row["unrealized_pnl_usd"],
        accrued_funding_usd=row["accrued_funding_usd"],
    )
