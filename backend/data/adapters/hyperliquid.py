from __future__ import annotations

from datetime import datetime

import httpx
import pandas as pd

from backend.core.config import settings
from backend.core.retry import retry_async
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
        response = await retry_async(lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload))
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
        response = await retry_async(lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload))
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]


async def fetch_open_interest_history(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    # Hyperliquid open-interest historical endpoint is not directly available in this adapter yet.
    return pd.DataFrame(columns=["ts", "open_interest"])


async def fetch_taker_buy_sell_volume(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    # Hyperliquid taker buy/sell historical endpoint is not directly available in this adapter yet.
    return pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"])


async def fetch_liquidation_history(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    # Hyperliquid liquidation history endpoint is not directly available in this adapter yet.
    return pd.DataFrame(columns=["ts", "liquidation_volume"])


async def fetch_order_book_snapshot(inst: Instrument) -> dict:
    # Placeholder until a dedicated Hyperliquid book snapshot endpoint is wired.
    return {"spread_bps": 0.0, "orderbook_imbalance": 0.0}
