from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd

from backend.core.config import settings
from backend.core.types import Instrument, PaperPosition, StrategySpec, Venue, VenueMode, strategy_spec_from_dict
from backend.data.storage import fetch_all, read_bars
from backend.ops.alerts import notify_event
from backend.ops.audit import record_paper_cycle_event
from backend.ops.metrics import TRADE_EVENTS
from backend.paper.broker import close_position, fill_order, open_position, submit_order, update_unrealized_pnl
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
        risk_reason = _risk_block_reason(spec, current_bar, target_inst)
        if risk_reason:
            _log_cycle_event(target_key, "skipped", risk_reason, {"signal": signal, "close_price": close_price})
            continue
        remaining_positions: list[dict] = []
        for position in positions:
            stop_take_reason = _check_stop_take(spec, position, close_price, current_bar)
            if stop_take_reason:
                realized = close_position(_row_to_position(position), close_price)
                _log_cycle_event(
                    target_key,
                    "position_closed",
                    stop_take_reason,
                    {"position_id": position["position_id"], "realized_pnl_usd": realized},
                )
            elif position["direction"] != signal:
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
                unrealized = raw_pnl + float(position["accrued_funding_usd"]) - float(position.get("entry_fees_usd") or 0.0)
                update_unrealized_pnl(position["position_id"], unrealized)
                remaining_positions.append(position)

        if signal in {"long", "short"} and not remaining_positions:
            size_usd = _resolve_size_usd(spec, current_bar)
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
        elif signal in {"long", "short"} and remaining_positions:
            _log_cycle_event(
                target_key,
                "skipped",
                "position_already_open",
                {"signal": signal, "open_positions": len(remaining_positions)},
            )
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


def _risk_block_reason(spec: StrategySpec, current_bar: dict, instrument: Instrument) -> str | None:
    volume_quote = float(current_bar.get("volume_quote") or 0.0)
    if volume_quote < spec.execution.min_volume_usd:
        return "min_volume_not_met"
    if _open_position_count() >= settings.paper_max_open_positions:
        return "max_open_positions_reached"
    if _gross_exposure_usd() >= settings.paper_max_gross_exposure_usd:
        return "gross_exposure_limit_breached"
    correlation_reason = _correlation_block_reason(spec, instrument, current_bar)
    if correlation_reason:
        return correlation_reason
    daily_realized = _daily_realized_pnl()
    if daily_realized <= -abs(settings.paper_daily_loss_limit_usd):
        return "daily_loss_limit_breached"
    return None


def _open_position_count() -> int:
    row = fetch_all("SELECT COUNT(*) AS count FROM paper_positions WHERE closed_at IS NULL", [])
    return int(row[0]["count"])


def _gross_exposure_usd() -> float:
    row = fetch_all("SELECT COALESCE(SUM(size_usd), 0) AS total FROM paper_positions WHERE closed_at IS NULL", [])
    return float(row[0]["total"] or 0.0)


def _daily_realized_pnl() -> float:
    now = datetime.now(timezone.utc)
    reset_hour = settings.paper_day_reset_hour_utc % 24
    start_of_day_dt = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if now < start_of_day_dt:
        start_of_day_dt -= timedelta(days=1)
    start_of_day = start_of_day_dt.isoformat()
    row = fetch_all(
        "SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total FROM paper_positions WHERE closed_at IS NOT NULL AND closed_at>=?",
        [start_of_day],
    )
    return float(row[0]["total"] or 0.0)


def _check_stop_take(spec: StrategySpec, position: dict, current_price: float, current_bar: dict) -> str | None:
    entry = float(position.get("entry_price") or 0.0)
    if entry <= 0:
        return None
    pnl_pct = (current_price - entry) / entry
    if position.get("direction") == "short":
        pnl_pct = -pnl_pct
    atr = float(current_bar.get("atr_14") or 0.0)
    if atr <= 0:
        return None

    stop_mult = spec.risk_limits.stop_loss_atr_mult
    if stop_mult:
        stop_dist = (float(stop_mult) * atr) / entry
        if pnl_pct <= -stop_dist:
            return "stop_loss"

    take_mult = spec.risk_limits.take_profit_atr_mult
    if take_mult:
        take_dist = (float(take_mult) * atr) / entry
        if pnl_pct >= take_dist:
            return "take_profit"
    return None


def _resolve_size_usd(spec: StrategySpec, current_bar: dict) -> float:
    method = spec.sizing.method
    fixed = spec.sizing.fixed_notional_usd or 1_000.0
    if method == "fixed_notional":
        return float(fixed)
    if method == "vol_target":
        target_vol = float(spec.sizing.target_vol or 0.02)
        realized_vol = max(float(current_bar.get("vol_20") or 0.0), 1e-6)
        raw_size = settings.paper_initial_capital_usd * (target_vol / realized_vol)
        cap = settings.paper_initial_capital_usd * spec.sizing.max_position_pct
        return float(max(100.0, min(raw_size, cap)))
    if method == "kelly_half":
        # Conservative half-kelly proxy when no explicit expectancy model is available.
        cap = settings.paper_initial_capital_usd * spec.sizing.max_position_pct
        return float(max(100.0, min(fixed * 1.5, cap)))
    return float(fixed)


def _correlation_block_reason(spec: StrategySpec, instrument: Instrument, current_bar: dict) -> str | None:
    threshold = float(settings.paper_max_signal_correlation)
    if threshold <= 0:
        return None
    open_rows = fetch_all("SELECT instrument_json FROM paper_positions WHERE closed_at IS NULL", [])
    if not open_rows:
        return None
    as_of = current_bar.get("ts") or datetime.now(timezone.utc)
    as_of_ts = pd.Timestamp(as_of)
    if as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.tz_localize("UTC")
    else:
        as_of_ts = as_of_ts.tz_convert("UTC")
    end = as_of_ts.to_pydatetime()
    start = end - timedelta(days=14)
    target_bars = read_bars(instrument, spec.primary_timeframe, start, end)
    if target_bars.empty or len(target_bars) < 40:
        return None
    target_ret = (
        target_bars[["ts_open", "close"]]
        .sort_values("ts_open")
        .assign(target_ret=lambda frame: frame["close"].astype(float).pct_change())
        .dropna(subset=["target_ret"])
    )
    if target_ret.empty:
        return None
    for row in open_rows:
        inst_json = json.loads(row["instrument_json"])
        other = Instrument(
            symbol=inst_json["symbol"],
            venue=Venue(inst_json["venue"]),
            mode=VenueMode(inst_json["mode"]),
            quote=inst_json.get("quote", "USDT"),
        )
        if other.symbol == instrument.symbol and other.venue == instrument.venue:
            continue
        other_bars = read_bars(other, spec.primary_timeframe, start, end)
        if other_bars.empty or len(other_bars) < 40:
            continue
        other_ret = (
            other_bars[["ts_open", "close"]]
            .sort_values("ts_open")
            .assign(other_ret=lambda frame: frame["close"].astype(float).pct_change())
            .dropna(subset=["other_ret"])
        )
        merged = target_ret.merge(other_ret, on="ts_open", how="inner")
        if len(merged) < 20:
            continue
        corr = merged["target_ret"].corr(merged["other_ret"])
        if pd.notna(corr) and abs(float(corr)) >= threshold:
            return "correlation_limit_breached"
    return None


def _log_cycle_event(target_key: dict, event_type: str, reason: str, payload: dict) -> None:
    if event_type in {"position_opened", "position_closed"}:
        TRADE_EVENTS.labels(event_type=event_type, spec_id=target_key["spec_id"]).inc()
        notify_event(event_type, f"{target_key['symbol']} {target_key['venue']} {reason}", {"target": target_key, **payload})
    if reason in {"daily_loss_limit_breached", "stop_loss"}:
        notify_event("risk_alert", reason, {"target": target_key, **payload})
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
        entry_fees_usd=float(row.get("entry_fees_usd") or 0.0),
    )
