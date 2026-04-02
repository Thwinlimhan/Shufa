from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from backend.core.types import DataQuality, DatasetHealth, Instrument, Timeframe, utc_now

EXPECTED_DELTAS = {
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
}

STALE_MULTIPLIER = {
    Timeframe.M15: 3,
    Timeframe.H1: 3,
    Timeframe.H4: 2,
}


def check_dataset(inst: Instrument, tf: Timeframe, df: pd.DataFrame, now: datetime | None = None) -> DatasetHealth:
    now = now or utc_now()
    if df.empty or "ts_open" not in df.columns:
        return DatasetHealth(
            instrument=inst,
            timeframe=tf,
            quality=DataQuality.UNVERIFIED,
            last_bar_ts=None,
            gap_count=0,
            duplicate_count=0,
            coverage_days=0.0,
            checked_at=now,
        )

    working = df.copy()
    working["ts_open"] = pd.to_datetime(working["ts_open"], utc=True)
    working = working.sort_values("ts_open").reset_index(drop=True)
    duplicate_count = int(working.duplicated(subset="ts_open").sum())
    deltas = working["ts_open"].diff().dropna()
    expected = EXPECTED_DELTAS[tf]
    gap_count = int((deltas > expected).sum())
    last_bar_ts = working["ts_open"].iloc[-1].to_pydatetime()
    coverage = (working["ts_open"].iloc[-1] - working["ts_open"].iloc[0]).total_seconds() / 86400 if len(working) > 1 else 0.0
    stale_cutoff = now - expected * STALE_MULTIPLIER[tf]

    quality = DataQuality.HEALTHY
    if gap_count > 0:
        quality = DataQuality.GAPPED
    elif last_bar_ts < stale_cutoff:
        quality = DataQuality.STALE

    return DatasetHealth(
        instrument=inst,
        timeframe=tf,
        quality=quality,
        last_bar_ts=last_bar_ts,
        gap_count=gap_count,
        duplicate_count=duplicate_count,
        coverage_days=round(float(coverage), 3),
        checked_at=now,
    )
