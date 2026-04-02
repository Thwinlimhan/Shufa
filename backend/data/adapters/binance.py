from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import pandas as pd

from backend.core.config import settings
from backend.core.types import Instrument, Timeframe

TF_MAP = {
    Timeframe.M15: "15m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
}


async def fetch_bars(inst: Instrument, tf: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    rows: list[list] = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    async with httpx.AsyncClient(timeout=30) as client:
        while cursor < end_ms:
            response = await client.get(
                f"{settings.binance_base_url}/fapi/v1/klines",
                params={
                    "symbol": inst.venue_symbol,
                    "interval": TF_MAP[tf],
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1500,
                },
            )
            response.raise_for_status()
            chunk = response.json()
            if not chunk:
                break
            rows.extend(chunk)
            last_open = chunk[-1][0]
            if last_open <= cursor:
                break
            cursor = last_open + 1
            if len(chunk) < 1500:
                break
            await asyncio.sleep(0.1)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows,
        columns=[
            "ts_open_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "ts_close_ms",
            "volume_quote",
            "trades",
            "_buy_base",
            "_buy_quote",
            "_ignore",
        ],
    )
    df["ts_open"] = pd.to_datetime(df["ts_open_ms"], unit="ms", utc=True)
    df["ts_close"] = pd.to_datetime(df["ts_close_ms"], unit="ms", utc=True)
    numeric = ["open", "high", "low", "close", "volume", "volume_quote"]
    df[numeric] = df[numeric].astype(float)
    df["trades"] = df["trades"].astype(int)
    return df[["ts_open", "ts_close", "open", "high", "low", "close", "volume", "volume_quote", "trades"]]


async def fetch_funding_history(inst: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.binance_base_url}/fapi/v1/fundingRate",
            params={
                "symbol": inst.venue_symbol,
                "startTime": int(start.timestamp() * 1000),
                "endTime": int(end.timestamp() * 1000),
                "limit": 1000,
            },
        )
        response.raise_for_status()
    data = response.json()
    if not data:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.DataFrame(data)
    df["ts"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]
