from __future__ import annotations

from datetime import datetime

import httpx
import pandas as pd

from backend.core.config import settings
from backend.core.types import Instrument, Timeframe

INTERVAL_MAP = {
    Timeframe.M15: "15m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
}


async def fetch_bars(inst: Instrument, tf: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": inst.symbol,
            "interval": INTERVAL_MAP[tf],
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
        },
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts_open"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df["ts_close"] = df["ts_open"]
    df["open"] = df["o"].astype(float)
    df["high"] = df["h"].astype(float)
    df["low"] = df["l"].astype(float)
    df["close"] = df["c"].astype(float)
    df["volume"] = df["v"].astype(float)
    df["volume_quote"] = (df["close"] * df["volume"]).astype(float)
    df["trades"] = 0
    return df[["ts_open", "ts_close", "open", "high", "low", "close", "volume", "volume_quote", "trades"]]


async def fetch_funding_history(inst: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
    payload = {
        "type": "fundingHistory",
        "coin": inst.symbol,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]
