from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import pandas as pd

from backend.core.config import settings
from backend.core.retry import retry_async
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
            response = await retry_async(
                lambda: client.get(
                    f"{settings.binance_base_url}/fapi/v1/klines",
                    params={
                        "symbol": inst.venue_symbol,
                        "interval": TF_MAP[tf],
                        "startTime": cursor,
                        "endTime": end_ms,
                        "limit": 1500,
                    },
                ),
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
        response = await retry_async(
            lambda: client.get(
                f"{settings.binance_base_url}/fapi/v1/fundingRate",
                params={
                    "symbol": inst.venue_symbol,
                    "startTime": int(start.timestamp() * 1000),
                    "endTime": int(end.timestamp() * 1000),
                    "limit": 1000,
                },
            ),
        )
        response.raise_for_status()
    data = response.json()
    if not data:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.DataFrame(data)
    df["ts"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]]


async def fetch_open_interest_history(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await retry_async(
            lambda: client.get(
                f"{settings.binance_base_url}/futures/data/openInterestHist",
                params={"symbol": inst.venue_symbol, "period": period, "limit": limit},
            )
        )
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["ts", "open_interest"])
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["open_interest"] = df["sumOpenInterestValue"].astype(float)
    return df[["ts", "open_interest"]]


async def fetch_taker_buy_sell_volume(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await retry_async(
            lambda: client.get(
                f"{settings.binance_base_url}/futures/data/takerBuySellVol",
                params={"symbol": inst.venue_symbol, "period": period, "limit": limit},
            )
        )
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"])
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["taker_buy_volume"] = df["takerBuyVolValue"].astype(float)
    df["taker_sell_volume"] = df["takerSellVolValue"].astype(float)
    return df[["ts", "taker_buy_volume", "taker_sell_volume"]]


async def fetch_liquidation_history(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    safe_limit = max(1, min(int(limit), 100))
    async with httpx.AsyncClient(timeout=30) as client:
        response = await retry_async(
            lambda: client.get(
                f"{settings.binance_base_url}/futures/data/allForceOrders",
                params={"symbol": inst.venue_symbol, "autoCloseType": "LIQUIDATION", "limit": safe_limit},
            )
        )
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return pd.DataFrame(columns=["ts", "liquidation_volume"])
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    avg_px = pd.to_numeric(df.get("averagePrice"), errors="coerce").fillna(0.0)
    exec_qty = pd.to_numeric(df.get("executedQty"), errors="coerce").fillna(0.0)
    df["liquidation_volume"] = avg_px * exec_qty
    grouped = (
        df.set_index("ts")
        .resample(period)
        .agg(liquidation_volume=("liquidation_volume", "sum"))
        .reset_index()
        .sort_values("ts")
    )
    return grouped[["ts", "liquidation_volume"]]


async def fetch_order_book_snapshot(inst: Instrument) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await retry_async(
            lambda: client.get(
                f"{settings.binance_base_url}/fapi/v1/depth",
                params={"symbol": inst.venue_symbol, "limit": 20},
            )
        )
        response.raise_for_status()
    data = response.json()
    bids = data.get("bids", [])
    asks = data.get("asks", [])
    if not bids or not asks:
        return {"spread_bps": 0.0, "orderbook_imbalance": 0.0}
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    spread_bps = ((best_ask - best_bid) / best_bid) * 10_000 if best_bid else 0.0
    bid_depth = sum(float(item[1]) for item in bids[:10])
    ask_depth = sum(float(item[1]) for item in asks[:10])
    denom = bid_depth + ask_depth
    imbalance = ((bid_depth - ask_depth) / denom) if denom else 0.0
    return {"spread_bps": spread_bps, "orderbook_imbalance": imbalance}
