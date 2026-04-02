from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from backend.backtest.engine import run_backtest
from backend.backtest.metrics import evaluate_promotion
from backend.backtest.tuning import strategy_sweep_variants
from backend.core.types import BacktestConfig, Instrument, Venue, dataclass_to_dict
from backend.data.features import add_funding_features, compute_features
from backend.data.service import load_funding_like_series
from backend.data.storage import read_bars
from backend.strategy.registry import load_spec


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
    features = compute_features(bars)
    funding = load_funding_like_series(instrument, timeframe, start, now)
    enriched = add_funding_features(features, funding)
    return enriched, start, now


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
        except HTTPException:
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
