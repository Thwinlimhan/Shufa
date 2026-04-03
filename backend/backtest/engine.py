from __future__ import annotations

import random
import statistics
import uuid
from datetime import datetime
from decimal import Decimal

import pandas as pd

from backend.backtest.broker import round_trip_cost
from backend.backtest.metrics import annualized_return, compute_max_drawdown
from backend.core.types import BacktestConfig, BacktestResult, EquityPoint, StrategySpec, TradeRecord, utc_now
from backend.strategy.engine import get_signal


def _resolve_backtest_size(
    spec: StrategySpec,
    row: dict,
    capital: float,
) -> float:
    """Mirror the sizing logic used by the paper-trading runner."""
    method = spec.sizing.method
    fixed = spec.sizing.fixed_notional_usd or 1_000.0
    if method == "vol_target":
        target_vol = float(spec.sizing.target_vol or 0.02)
        realized_vol = max(float(row.get("vol_20") or 0.0), 1e-6)
        raw_size = capital * (target_vol / realized_vol)
        cap = capital * spec.sizing.max_position_pct
        return float(max(100.0, min(raw_size, cap)))
    if method == "kelly_half":
        cap = capital * spec.sizing.max_position_pct
        return float(max(100.0, min(fixed * 1.5, cap)))
    return float(fixed)


def _estimate_funding(
    row: dict,
    size_usd: float,
    direction: str,
    config: BacktestConfig,
) -> float:
    """Estimate funding cost for one bar.

    If ``config.funding_included`` is ``False`` or the bar lacks a
    ``funding_rate`` column the cost is zero.

    Funding convention:
    - Positive rate = longs pay shorts.
    - A long position *pays* ``size * rate``.
    - A short position *receives* ``size * rate``.
    """
    if not config.funding_included:
        return 0.0
    rate = float(row.get("funding_rate") or 0.0)
    if rate == 0.0:
        return 0.0
    # For longs a positive rate is a cost (negative PnL).
    # For shorts a positive rate is income (positive PnL).
    if direction == "long":
        return -(size_usd * rate)
    return size_usd * rate


def run_backtest(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    *,
    compute_robustness: bool = True,
) -> BacktestResult:
    frame = bars.copy().sort_values("ts_open").reset_index(drop=True)
    capital = config.initial_capital_usd
    equity = capital
    equity_curve: list[EquityPoint] = []
    trades: list[TradeRecord] = []
    current_side = "flat"
    entry_price = 0.0
    entry_ts: datetime | None = None
    size_usd = _resolve_backtest_size(spec, {}, capital)
    accrued_funding = 0.0
    signal_counts = {"long": 0, "short": 0, "flat": 0}

    for row in frame.to_dict(orient="records"):
        signal = get_signal(spec, row)
        signal_counts[signal] += 1
        price = float(row["close"])
        ts = pd.Timestamp(row["ts_open"]).to_pydatetime()

        # Accrue funding each bar while a position is open.
        if current_side in {"long", "short"}:
            accrued_funding += _estimate_funding(row, size_usd, current_side, config)

        if current_side == "flat" and signal in {"long", "short"}:
            current_side = signal
            entry_price = price
            entry_ts = ts
            size_usd = _resolve_backtest_size(spec, row, equity)
            accrued_funding = 0.0
        elif current_side in {"long", "short"} and signal != current_side:
            raw_pnl = ((price - entry_price) / entry_price) * size_usd
            if current_side == "short":
                raw_pnl = -raw_pnl
            fees = round_trip_cost(size_usd, config.fee_bps, config.slippage_bps)
            funding = accrued_funding
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
            accrued_funding = 0.0

        equity_curve.append(EquityPoint(ts=ts, equity=equity))

    if current_side in {"long", "short"} and not frame.empty:
        last_row = frame.iloc[-1]
        last_price = float(last_row["close"])
        last_ts = pd.Timestamp(last_row["ts_open"]).to_pydatetime()
        raw_pnl = ((last_price - entry_price) / entry_price) * size_usd if entry_price else 0.0
        if current_side == "short":
            raw_pnl = -raw_pnl
        fees = round_trip_cost(size_usd, config.fee_bps, config.slippage_bps)
        funding = accrued_funding
        pnl = raw_pnl - fees + funding
        equity += pnl
        trades.append(
            TradeRecord(
                trade_id=str(uuid.uuid4()),
                spec_id=spec.spec_id,
                instrument=spec.universe[0],
                direction=current_side,
                entry_ts=entry_ts or last_ts,
                exit_ts=last_ts,
                entry_price=Decimal(str(round(entry_price, 6))),
                exit_price=Decimal(str(round(last_price, 6))),
                size_usd=size_usd,
                pnl_usd=pnl,
                fees_usd=fees,
                funding_usd=funding,
                exit_reason="end_of_backtest",
            )
        )
        if equity_curve:
            equity_curve[-1] = EquityPoint(ts=last_ts, equity=equity)
        else:
            equity_curve.append(EquityPoint(ts=last_ts, equity=equity))

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
            + (
                "oi_change_pct",
                "buy_sell_ratio",
                "liquidation_intensity",
                "spread_bps",
                "orderbook_imbalance",
                "btc_ret_1",
                "rel_strength_20",
                "beta_btc_20",
                "onchain_pressure",
            )
            if column in frame.columns and len(frame[column]) > 0
        },
    }

    result = BacktestResult(
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
        oos_sharpe=sharpe,
        diagnostics=diagnostics,
        trades=trades,
        equity_curve=equity_curve,
    )
    if not compute_robustness:
        return result

    perturb_mean, perturb_std = _compute_perturbation_sharpe(spec, frame, config)
    result.perturbation_sharpe_mean = perturb_mean
    result.perturbation_sharpe_std = perturb_std
    result.oos_sharpe = _compute_oos_sharpe(spec, frame, config)
    return result


def _compute_perturbation_sharpe(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    n_runs: int = 20,
) -> tuple[float, float]:
    if bars.empty or "close" not in bars.columns:
        return 0.0, 0.0
    rng = random.Random(42)
    sharpes: list[float] = []
    for _ in range(n_runs):
        noised = bars.copy()
        noised["close"] = noised["close"].astype(float).map(lambda price: price * rng.uniform(0.998, 1.002))
        noised_result = run_backtest(spec, noised, config, compute_robustness=False)
        sharpes.append(noised_result.sharpe)
    return float(statistics.fmean(sharpes)), float(statistics.pstdev(sharpes))


def _compute_oos_sharpe(
    spec: StrategySpec,
    bars: pd.DataFrame,
    config: BacktestConfig,
    oos_fraction: float = 0.3,
) -> float:
    if bars.empty or len(bars) < 2:
        return 0.0
    split = int(len(bars) * (1 - oos_fraction))
    split = max(1, min(split, len(bars) - 1))
    oos_bars = bars.iloc[split:].reset_index(drop=True)
    oos_start = pd.Timestamp(oos_bars["ts_open"].iloc[0]).to_pydatetime()
    oos_config = BacktestConfig(
        start_date=oos_start,
        end_date=config.end_date,
        instrument=config.instrument,
        initial_capital_usd=config.initial_capital_usd,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
        funding_included=config.funding_included,
    )
    oos_result = run_backtest(spec, oos_bars, oos_config, compute_robustness=False)
    return float(oos_result.sharpe)
