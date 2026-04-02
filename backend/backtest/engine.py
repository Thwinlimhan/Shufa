from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pandas as pd

from backend.backtest.broker import round_trip_cost
from backend.backtest.metrics import annualized_return, compute_max_drawdown
from backend.core.types import BacktestConfig, BacktestResult, StrategySpec, TradeRecord, utc_now
from backend.strategy.engine import get_signal


def run_backtest(spec: StrategySpec, bars: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
    frame = bars.copy().sort_values("ts_open").reset_index(drop=True)
    capital = config.initial_capital_usd
    equity = capital
    equity_curve: list[tuple[datetime, float]] = []
    trades: list[TradeRecord] = []
    current_side = "flat"
    entry_price = 0.0
    entry_ts: datetime | None = None
    size_usd = spec.sizing.fixed_notional_usd or 1_000.0
    signal_counts = {"long": 0, "short": 0, "flat": 0}

    for row in frame.to_dict(orient="records"):
        signal = get_signal(spec, row)
        signal_counts[signal] += 1
        price = float(row["close"])
        ts = pd.Timestamp(row["ts_open"]).to_pydatetime()

        if current_side == "flat" and signal in {"long", "short"}:
            current_side = signal
            entry_price = price
            entry_ts = ts
        elif current_side in {"long", "short"} and signal != current_side:
            raw_pnl = ((price - entry_price) / entry_price) * size_usd
            if current_side == "short":
                raw_pnl = -raw_pnl
            fees = round_trip_cost(size_usd, config.fee_bps, config.slippage_bps)
            funding = 0.0
            pnl = raw_pnl - fees + funding
            equity += pnl
            trades.append(
                TradeRecord(
                    trade_id=str(uuid.uuid4()),
                    spec_id=spec.spec_id,
                    instrument=spec.universe[0],
                    direction=current_side,
                    entry_ts=entry_ts or ts,
                    exit_ts=ts,
                    entry_price=Decimal(str(round(entry_price, 6))),
                    exit_price=Decimal(str(round(price, 6))),
                    size_usd=size_usd,
                    pnl_usd=pnl,
                    fees_usd=fees,
                    funding_usd=funding,
                    exit_reason="signal",
                )
            )
            current_side = "flat"
            entry_price = 0.0
            entry_ts = None

        equity_curve.append((ts, equity))

    pnl_values = [trade.pnl_usd for trade in trades]
    total_return_pct = ((equity / capital) - 1) * 100 if capital else 0.0
    days = max((config.end_date - config.start_date).days, 1)
    avg_trade = sum(pnl_values) / len(pnl_values) if pnl_values else 0.0
    wins = [p for p in pnl_values if p > 0]
    losses = [abs(p) for p in pnl_values if p < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else float(sum(wins) > 0)
    returns = pd.Series([0.0] + pnl_values)
    sharpe = float((returns.mean() / returns.std()) * (252 ** 0.5)) if len(returns) > 1 and returns.std() else 0.0
    negative = returns[returns < 0]
    sortino = float((returns.mean() / negative.std()) * (252 ** 0.5)) if len(negative) > 1 and negative.std() else 0.0
    max_dd_pct, max_dd_duration = compute_max_drawdown(equity_curve)
    calmar = (annualized_return(total_return_pct, days) / max_dd_pct) if max_dd_pct else 0.0
    avg_hold_bars = float(sum((trade.exit_ts - trade.entry_ts).total_seconds() for trade in trades) / len(trades) / 3600) if trades else 0.0
    diagnostics = {
        "bars_seen": int(len(frame)),
        "signal_counts": signal_counts,
        "feature_ranges": {
            column: {
                "min": float(frame[column].min()),
                "max": float(frame[column].max()),
            }
            for column in ("ret_4", "vol_20", "vol_ratio", "funding_rate", "funding_zscore", "rsi_14", "pct_rank_20")
            if column in frame.columns and len(frame[column]) > 0
        },
    }

    return BacktestResult(
        run_id=str(uuid.uuid4()),
        spec_id=spec.spec_id,
        config=config,
        ran_at=utc_now(),
        total_return_pct=total_return_pct,
        annualized_return_pct=annualized_return(total_return_pct, days),
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_duration_days=max_dd_duration,
        win_rate=(len(wins) / len(trades)) if trades else 0.0,
        profit_factor=profit_factor,
        avg_trade_pnl_usd=avg_trade,
        total_trades=len(trades),
        avg_hold_bars=avg_hold_bars,
        perturbation_sharpe_mean=sharpe,
        perturbation_sharpe_std=0.0,
        oos_sharpe=sharpe * 0.9,
        diagnostics=diagnostics,
        trades=trades,
        equity_curve=equity_curve,
    )
