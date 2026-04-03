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

        equity_curve.append(EquityPoint(ts=ts, equity=equity))

    if current_side in {"long", "short"} and not frame.empty:
        last_row = frame.iloc[-1]
        last_price = float(last_row["close"])
        last_ts = pd.Timestamp(last_row["ts_open"]).to_pydatetime()
        raw_pnl = ((last_price - entry_price) / entry_price) * size_usd if entry_price else 0.0
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
