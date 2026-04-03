from __future__ import annotations

import random
import statistics
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest.engine import run_backtest
from backend.backtest.tuning import strategy_sweep_variants
from backend.core.types import BacktestConfig, Instrument, StrategySpec
from backend.data.storage import read_bars


def walk_forward_analysis(spec: StrategySpec, instrument: Instrument, lookback_days: int = 180, windows: int = 4) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    bars = read_bars(instrument, spec.primary_timeframe, start, end)
    if bars.empty or len(bars) < max(60, windows * 12):
        return {"windows": [], "stability_score": 0.0}

    stride = max(10, len(bars) // windows)
    results: list[dict] = []
    for window_index in range(windows):
        train_start = window_index * stride
        train_end = min(train_start + stride, len(bars) - 1)
        test_end = min(train_end + stride, len(bars))
        if test_end - train_end < 5:
            continue
        train = bars.iloc[train_start:train_end].reset_index(drop=True)
        test = bars.iloc[train_end:test_end].reset_index(drop=True)
        best_label = "base"
        best_spec = spec
        best_sharpe = float("-inf")
        train_config = BacktestConfig(
            start_date=pd.Timestamp(train["ts_open"].iloc[0]).to_pydatetime(),
            end_date=pd.Timestamp(train["ts_open"].iloc[-1]).to_pydatetime(),
            instrument=instrument,
        )
        for label, variant in strategy_sweep_variants(spec):
            train_result = run_backtest(variant, train, train_config)
            if train_result.sharpe > best_sharpe:
                best_sharpe = train_result.sharpe
                best_label = label
                best_spec = variant
        test_config = BacktestConfig(
            start_date=pd.Timestamp(test["ts_open"].iloc[0]).to_pydatetime(),
            end_date=pd.Timestamp(test["ts_open"].iloc[-1]).to_pydatetime(),
            instrument=instrument,
        )
        test_result = run_backtest(best_spec, test, test_config)
        results.append(
            {
                "window": window_index + 1,
                "best_variant": best_label,
                "train_sharpe": round(best_sharpe, 4),
                "test_sharpe": round(test_result.sharpe, 4),
                "test_return_pct": round(test_result.total_return_pct, 4),
                "test_trades": test_result.total_trades,
            }
        )
    test_sharpes = [item["test_sharpe"] for item in results]
    if len(test_sharpes) > 1 and statistics.pstdev(test_sharpes) > 0:
        stability_score = statistics.fmean(test_sharpes) / statistics.pstdev(test_sharpes)
    else:
        stability_score = 0.0
    return {"windows": results, "stability_score": round(float(stability_score), 4)}


def monte_carlo_trade_paths(trades: list[dict], simulations: int = 500) -> dict:
    pnl_values = [float(item.get("pnl_usd", 0.0)) for item in trades]
    if not pnl_values:
        return {"simulations": simulations, "p5": 0.0, "p50": 0.0, "p95": 0.0}
    rng = random.Random(42)
    finals: list[float] = []
    for _ in range(simulations):
        path = [rng.choice(pnl_values) for _ in range(len(pnl_values))]
        finals.append(sum(path))
    ordered = sorted(finals)
    p5 = ordered[int(0.05 * (len(ordered) - 1))]
    p50 = ordered[int(0.50 * (len(ordered) - 1))]
    p95 = ordered[int(0.95 * (len(ordered) - 1))]
    return {
        "simulations": simulations,
        "p5": round(float(p5), 4),
        "p50": round(float(p50), 4),
        "p95": round(float(p95), 4),
        "mean": round(float(statistics.fmean(finals)), 4),
    }


def strategy_correlation(spec: StrategySpec, lookback_days: int = 120) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    series: dict[str, pd.Series] = {}
    for instrument in spec.universe:
        bars = read_bars(instrument, spec.primary_timeframe, start, end)
        if bars.empty:
            continue
        closes = bars.sort_values("ts_open")["close"].astype(float).pct_change().fillna(0.0)
        series[f"{instrument.symbol}/{instrument.venue.value}"] = closes.reset_index(drop=True)
    if len(series) < 2:
        return {"matrix": {}, "warning": "insufficient_series"}
    frame = pd.DataFrame(series).dropna()
    matrix = frame.corr().round(4)
    return {
        "matrix": matrix.to_dict(),
        "warning": None,
    }
