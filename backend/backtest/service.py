from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pandas as pd
import structlog

from backend.backtest.advanced import monte_carlo_trade_paths, strategy_correlation, walk_forward_analysis
from backend.backtest.engine import run_backtest
from backend.backtest.metrics import evaluate_promotion
from backend.backtest.tuning import strategy_sweep_variants
from backend.core.types import BacktestConfig, Instrument, Venue, dataclass_to_dict
from backend.data.features import add_funding_features, compute_features
from backend.data.service import attach_benchmark_close, load_funding_like_series
from backend.data.storage import read_bars
from backend.strategy.registry import load_spec
from backend.data.adapters import binance, hyperliquid

log = structlog.get_logger()


def resolve_instrument(spec_id: str, symbol: str | None, venue: str | None) -> tuple:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    filtered = spec.universe
    if symbol:
        filtered = [inst for inst in filtered if inst.symbol == symbol]
    if venue:
        filtered = [inst for inst in filtered if inst.venue.value == venue]
    if not filtered:
        raise HTTPException(status_code=400, detail="Requested symbol/venue is not available for this strategy")
    return spec, filtered[0]


def build_feature_frame(instrument: Instrument, timeframe, lookback_days: int):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=lookback_days)
    bars = read_bars(instrument, timeframe, start, now)
    if bars.empty:
        raise HTTPException(status_code=400, detail="No bars available for backtest")
    bars = attach_benchmark_close(instrument, timeframe, bars)
    features = compute_features(bars)
    features = _merge_market_context(features, instrument)
    funding = load_funding_like_series(instrument, timeframe, start, now)
    enriched = add_funding_features(features, funding)
    return enriched, start, now


def _run_async(coro):
    """Run an async coroutine safely regardless of whether an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=60)
    return asyncio.run(coro)


def _merge_market_context(features, instrument: Instrument):
    try:
        if instrument.venue == Venue.BINANCE:
            oi = _run_async(binance.fetch_open_interest_history(instrument))
            taker = _run_async(binance.fetch_taker_buy_sell_volume(instrument))
            liquidations = _run_async(binance.fetch_liquidation_history(instrument))
            book = _run_async(binance.fetch_order_book_snapshot(instrument))
        else:
            oi = _run_async(hyperliquid.fetch_open_interest_history(instrument))
            taker = _run_async(hyperliquid.fetch_taker_buy_sell_volume(instrument))
            liquidations = _run_async(hyperliquid.fetch_liquidation_history(instrument))
            book = _run_async(hyperliquid.fetch_order_book_snapshot(instrument))
    except Exception:
        oi = None
        taker = None
        liquidations = None
        book = {"spread_bps": 0.0, "orderbook_imbalance": 0.0}
    merged = features.copy().sort_values("ts_open").reset_index(drop=True)
    if oi is not None and not oi.empty:
        merged = pd.merge_asof(merged, oi.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    if taker is not None and not taker.empty:
        merged = pd.merge_asof(merged, taker.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    if liquidations is not None and not liquidations.empty:
        merged = pd.merge_asof(merged, liquidations.sort_values("ts"), left_on="ts_open", right_on="ts", direction="backward")
        merged.drop(columns=[col for col in ["ts"] if col in merged.columns], inplace=True)
    merged["spread_bps"] = float(book.get("spread_bps") or 0.0)
    merged["orderbook_imbalance"] = float(book.get("orderbook_imbalance") or 0.0)
    return merged


def execute_backtest(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int) -> tuple[dict, dict]:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    features, start, end = build_feature_frame(instrument, spec.primary_timeframe, lookback_days)
    config = BacktestConfig(start_date=start, end_date=end, instrument=instrument)
    result = run_backtest(spec, features, config)
    decision = evaluate_promotion(result)
    return dataclass_to_dict(result), dataclass_to_dict(decision)


def compare_runs(spec_id: str, lookback_days: int) -> list[dict]:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    comparisons: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for instrument in spec.universe:
        key = (instrument.symbol, instrument.venue.value)
        if key in seen:
            continue
        seen.add(key)
        try:
            result, decision = execute_backtest(spec_id, instrument.symbol, instrument.venue.value, lookback_days)
            comparisons.append(
                {
                    "symbol": instrument.symbol,
                    "venue": instrument.venue.value,
                    "sharpe": result["sharpe"],
                    "total_return_pct": result["total_return_pct"],
                    "total_trades": result["total_trades"],
                    "passed": decision["passed"],
                }
            )
        except Exception as exc:
            log.warning("backtest compare failed", symbol=instrument.symbol, venue=instrument.venue.value, error=str(exc))
            comparisons.append(
                {
                    "symbol": instrument.symbol,
                    "venue": instrument.venue.value,
                    "sharpe": None,
                    "total_return_pct": None,
                    "total_trades": 0,
                    "passed": False,
                }
            )
    return comparisons


def sweep_runs(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int) -> list[dict]:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    features, start, end = build_feature_frame(instrument, spec.primary_timeframe, lookback_days)
    results: list[dict] = []
    for label, variant in strategy_sweep_variants(spec):
        config = BacktestConfig(start_date=start, end_date=end, instrument=instrument)
        result = run_backtest(variant, features, config)
        results.append(
            {
                "label": label,
                "sharpe": result.sharpe,
                "return_pct": result.total_return_pct,
                "trades": result.total_trades,
                "drawdown_pct": result.max_drawdown_pct,
            }
        )
    return sorted(results, key=lambda item: (item["sharpe"], item["return_pct"]), reverse=True)


def walk_forward(spec_id: str, symbol: str | None, venue: str | None, lookback_days: int, windows: int = 4) -> dict:
    spec, instrument = resolve_instrument(spec_id, symbol, venue)
    return walk_forward_analysis(spec, instrument, lookback_days=lookback_days, windows=windows)


def monte_carlo_for_run(run_id: str, simulations: int = 500) -> dict:
    from backend.data.storage import fetch_one

    row = fetch_one("SELECT result_json FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    import json

    result = json.loads(row["result_json"])
    return monte_carlo_trade_paths(result.get("trades", []), simulations=simulations)


def correlation_for_spec(spec_id: str, lookback_days: int = 120) -> dict:
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy_correlation(spec, lookback_days=lookback_days)
