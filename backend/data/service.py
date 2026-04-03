from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.core.types import DataQuality, Instrument, Timeframe, Venue, VenueMode
from backend.data.adapters import binance, hyperliquid
from backend.data.features import add_funding_features, compute_features
from backend.data.quality import check_dataset
from backend.data.storage import (
    read_bars,
    read_funding,
    read_market_context,
    save_mark_price,
    set_runner_state,
    upsert_dataset_health,
    write_bars,
    write_funding,
    write_market_context,
)
from backend.paper.portfolio import mark_to_market

DEFAULT_INSTRUMENTS = [
    Instrument(symbol="BTC", venue=Venue.BINANCE, mode=VenueMode.PERP),
    Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP),
    Instrument(symbol="BTC", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
    Instrument(symbol="ETH", venue=Venue.HYPERLIQUID, mode=VenueMode.PERP),
]
DEFAULT_TIMEFRAMES = [Timeframe.M15, Timeframe.H1, Timeframe.H4]


@dataclass
class IngestSummary:
    instrument_key: str
    timeframe: str
    rows_written: int
    start: str
    end: str
    quality: str


def default_instruments() -> list[Instrument]:
    return list(DEFAULT_INSTRUMENTS)


def default_timeframes() -> list[Timeframe]:
    return list(DEFAULT_TIMEFRAMES)


async def ingest_bars(inst: Instrument, timeframe: Timeframe, start: datetime, end: datetime) -> IngestSummary:
    bars = await _fetch_bars(inst, timeframe, start, end)
    if not bars.empty:
        write_bars(inst, timeframe, bars)
    health = check_dataset(inst, timeframe, read_bars(inst, timeframe, start, end), now=datetime.now(timezone.utc))
    upsert_dataset_health(
        [
            {
                "instrument_key": inst.key,
                "timeframe": timeframe.value,
                "quality": health.quality.value,
                "last_bar_ts": health.last_bar_ts.isoformat() if health.last_bar_ts else None,
                "gap_count": health.gap_count,
                "duplicate_count": health.duplicate_count,
                "coverage_days": health.coverage_days,
                "checked_at": health.checked_at.isoformat(),
            }
        ]
    )
    return IngestSummary(
        instrument_key=inst.key,
        timeframe=timeframe.value,
        rows_written=int(len(bars)),
        start=start.isoformat(),
        end=end.isoformat(),
        quality=health.quality.value,
    )


async def ingest_defaults(lookback_days: int = 30) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    results = await asyncio.gather(
        *[
            ingest_bars(inst, timeframe, start, end)
            for inst in default_instruments()
            for timeframe in default_timeframes()
        ]
    )
    return [summary.__dict__ for summary in results]


async def ingest_funding_defaults(lookback_days: int = 14) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    summaries: list[dict] = []
    for inst in default_instruments():
        funding = await load_funding_like_series_async(inst, Timeframe.H1, start, end)
        if funding.empty:
            continue
        write_funding(inst, funding)
        summaries.append(
            {
                "instrument_key": inst.key,
                "rows_written": int(len(funding)),
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        )
    return summaries


async def fetch_market_context_series(inst: Instrument, start: datetime, end: datetime) -> dict[str, pd.DataFrame]:
    lookback_hours = max(24, int((end - start).total_seconds() // 3600) + 1)
    limit = min(500, lookback_hours)
    if inst.venue == Venue.BINANCE:
        open_interest = await binance.fetch_open_interest_history(inst, period="1h", limit=limit)
        taker_flow = await binance.fetch_taker_buy_sell_volume(inst, period="1h", limit=limit)
        liquidations = await binance.fetch_liquidation_history(inst, period="1h", limit=limit)
    else:
        open_interest = await hyperliquid.fetch_open_interest_history(inst, period="1h", limit=limit)
        taker_flow = await hyperliquid.fetch_taker_buy_sell_volume(inst, period="1h", limit=limit)
        liquidations = await hyperliquid.fetch_liquidation_history(inst, period="1h", limit=limit)
    return {
        "open_interest": open_interest,
        "taker_flow": taker_flow,
        "liquidations": liquidations,
    }


async def ingest_market_context_defaults(lookback_days: int = 14) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    summaries: list[dict] = []
    for inst in default_instruments():
        series = await fetch_market_context_series(inst, start, end)
        row_counts: dict[str, int] = {}
        for dataset, frame in series.items():
            row_counts[dataset] = int(len(frame))
            if not frame.empty:
                write_market_context(inst, dataset, frame)
        summaries.append(
            {
                "instrument_key": inst.key,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "rows": row_counts,
            }
        )
    return summaries


def refresh_health(instruments: list[Instrument] | None = None, timeframes: list[Timeframe] | None = None) -> list[dict]:
    instruments = instruments or default_instruments()
    timeframes = timeframes or default_timeframes()
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for inst in instruments:
        for timeframe in timeframes:
            bars = read_bars(inst, timeframe, now - timedelta(days=30), now)
            health = check_dataset(inst, timeframe, bars, now=now)
            payload = {
                "instrument_key": inst.key,
                "timeframe": timeframe.value,
                "quality": health.quality.value,
                "last_bar_ts": health.last_bar_ts.isoformat() if health.last_bar_ts else None,
                "gap_count": health.gap_count,
                "duplicate_count": health.duplicate_count,
                "coverage_days": health.coverage_days,
                "checked_at": health.checked_at.isoformat(),
            }
            results.append(payload)
    upsert_dataset_health(results)
    return results


def latest_feature_bar(inst: Instrument, timeframe: Timeframe, lookback_bars: int = 250) -> dict | None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(latest_feature_bar_async(inst, timeframe, lookback_bars))

    bars = read_bars(inst, timeframe, datetime.now(timezone.utc) - timedelta(days=lookback_bars * 2), datetime.now(timezone.utc))
    if bars.empty:
        return None
    bars_with_context = _attach_market_context_from_storage(inst, bars)
    bars_with_context = attach_benchmark_close(inst, timeframe, bars_with_context)
    features = compute_features(bars_with_context)
    enriched = add_funding_features(features, pd.DataFrame(columns=["ts", "rate"]))
    latest = enriched.iloc[-1].to_dict()
    latest["ts"] = pd.Timestamp(latest["ts_open"]).to_pydatetime()
    latest["timeframe"] = timeframe.value
    latest["symbol"] = inst.symbol
    latest["venue"] = inst.venue.value
    return latest


async def latest_feature_bar_async(inst: Instrument, timeframe: Timeframe, lookback_bars: int = 250) -> dict | None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_bars * 2)
    bars = read_bars(inst, timeframe, start, end)
    if bars.empty:
        return None
    bars_with_context = _attach_market_context_from_storage(inst, bars)
    bars_with_context = attach_benchmark_close(inst, timeframe, bars_with_context)
    if not _has_market_context_columns(bars_with_context):
        series = await fetch_market_context_series(inst, start, end)
        for dataset, frame in series.items():
            if frame.empty:
                continue
            write_market_context(inst, dataset, frame)
        bars_with_context = _attach_market_context_from_storage(inst, bars)
        bars_with_context = attach_benchmark_close(inst, timeframe, bars_with_context)
    features = compute_features(bars_with_context)
    funding = read_funding(inst, start, end)
    if funding.empty:
        funding = await load_funding_like_series_async(inst, timeframe, start, end)
        if not funding.empty:
            write_funding(inst, funding)
    enriched = add_funding_features(features, funding)
    latest = enriched.iloc[-1].to_dict()
    latest["ts"] = pd.Timestamp(latest["ts_open"]).to_pydatetime()
    latest["timeframe"] = timeframe.value
    latest["symbol"] = inst.symbol
    latest["venue"] = inst.venue.value
    return latest


def should_process_bar(job_name: str, bar_ts: datetime) -> bool:
    from backend.data.storage import fetch_one

    row = fetch_one("SELECT last_processed_ts FROM runner_state WHERE job_name=?", [job_name])
    if row is None:
        return True
    return datetime.fromisoformat(row["last_processed_ts"]) < bar_ts


def mark_processed(job_name: str, bar_ts: datetime) -> None:
    set_runner_state(job_name, bar_ts.isoformat())


async def _fetch_bars(inst: Instrument, timeframe: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    if inst.venue == Venue.BINANCE:
        return await binance.fetch_bars(inst, timeframe, start, end)
    return await hyperliquid.fetch_bars(inst, timeframe, start, end)


async def load_funding_like_series_async(inst: Instrument, timeframe: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    if inst.venue == Venue.BINANCE:
        return await binance.fetch_funding_history(inst, start, end)
    return await hyperliquid.fetch_funding_history(inst, start, end)


def load_funding_like_series(inst: Instrument, timeframe: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    return asyncio.run(load_funding_like_series_async(inst, timeframe, start, end))


def ingest_mark_price(venue: str, symbol: str, price: float, ts_ms: int | None = None) -> dict:
    instrument = Instrument(symbol=symbol, venue=Venue(venue), mode=VenueMode.PERP)
    ts = datetime.now(timezone.utc) if ts_ms is None else datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    save_mark_price(instrument.key, symbol, venue, price, ts.isoformat())
    updated_positions = mark_to_market(symbol=symbol, venue=venue, price=price)
    return {
        "instrument_key": instrument.key,
        "symbol": symbol,
        "venue": venue,
        "price": price,
        "ts": ts.isoformat(),
        "updated_positions": updated_positions,
    }


def _attach_market_context_from_storage(inst: Instrument, bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return bars.copy()
    working = bars.copy().sort_values("ts_open").reset_index(drop=True)
    start = pd.Timestamp(working["ts_open"].min()).to_pydatetime()
    end = pd.Timestamp(working["ts_open"].max()).to_pydatetime()
    datasets = ("open_interest", "taker_flow", "liquidations")
    for dataset in datasets:
        frame = read_market_context(inst, dataset, start, end)
        if frame.empty:
            continue
        frame = frame.sort_values("ts")
        working = pd.merge_asof(working, frame, left_on="ts_open", right_on="ts", direction="backward")
        if "ts" in working.columns:
            working = working.drop(columns=["ts"])
    return working


def attach_benchmark_close(inst: Instrument, timeframe: Timeframe, bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return bars.copy()
    if inst.symbol.upper() == "BTC":
        out = bars.copy()
        out["btc_close"] = out["close"].astype(float)
        return out
    benchmark = Instrument(symbol="BTC", venue=inst.venue, mode=inst.mode, quote=inst.quote)
    start = pd.Timestamp(bars["ts_open"].min()).to_pydatetime()
    end = pd.Timestamp(bars["ts_open"].max()).to_pydatetime()
    btc_bars = read_bars(benchmark, timeframe, start, end)
    if btc_bars.empty:
        return bars.copy()
    btc_close = (
        btc_bars[["ts_open", "close"]]
        .copy()
        .rename(columns={"close": "btc_close"})
        .sort_values("ts_open")
        .reset_index(drop=True)
    )
    merged = bars.copy().sort_values("ts_open").reset_index(drop=True)
    merged = pd.merge_asof(merged, btc_close, on="ts_open", direction="backward")
    merged["btc_close"] = merged["btc_close"].ffill().bfill()
    return merged


def _has_market_context_columns(df: pd.DataFrame) -> bool:
    required = {"open_interest", "taker_buy_volume", "taker_sell_volume", "liquidation_volume"}
    if not required.intersection(set(df.columns)):
        return False
    return df[list(required.intersection(set(df.columns)))].notna().any().any()
