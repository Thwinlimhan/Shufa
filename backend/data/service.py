from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.core.types import DataQuality, Instrument, Timeframe, Venue, VenueMode
from backend.data.adapters import binance, hyperliquid
from backend.data.features import add_funding_features, compute_features
from backend.data.quality import check_dataset
from backend.data.storage import read_bars, set_runner_state, upsert_dataset_health, write_bars

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
    features = compute_features(bars)
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
    features = compute_features(bars)
    funding = await load_funding_like_series_async(inst, timeframe, start, end)
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
