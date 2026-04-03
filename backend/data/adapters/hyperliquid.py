from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    """Fetch current open interest from Hyperliquid's meta endpoint.

    Hyperliquid does not expose a dedicated OI *history* API, so we
    return a single-row DataFrame containing the latest snapshot.
    """
    payload = {"type": "metaAndAssetCtxs"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await retry_async(
                lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
            )
            response.raise_for_status()
        data = response.json()
        # data is [meta, [asset_ctx, ...]]
        meta = data[0] if isinstance(data, list) and len(data) > 0 else {}
        asset_ctxs = data[1] if isinstance(data, list) and len(data) > 1 else []
        universe = meta.get("universe", [])
        coin_idx: int | None = None
        for idx, item in enumerate(universe):
            if item.get("name") == inst.symbol:
                coin_idx = idx
                break
        if coin_idx is not None and coin_idx < len(asset_ctxs):
            ctx = asset_ctxs[coin_idx]
            oi_value = float(ctx.get("openInterest", 0)) * float(ctx.get("markPx", 0))
            return pd.DataFrame([{
                "ts": pd.Timestamp.now(tz="UTC"),
                "open_interest": oi_value,
            }])
    except Exception:
        pass
    return pd.DataFrame(columns=["ts", "open_interest"])


async def fetch_taker_buy_sell_volume(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Derive approximate taker buy/sell volume from recent candle data.

    Hyperliquid does not expose a taker buy/sell breakdown API.
    We use individual candle volume as a rough proxy, splitting volume
    based on whether the candle closed higher or lower than it opened.
    """
    now = datetime.now(tz=timezone.utc)
    interval = INTERVAL_MAP.get(Timeframe.H1, "1h")
    start_ms = int((now - timedelta(hours=limit)).timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": inst.symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await retry_async(
                lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
            )
            response.raise_for_status()
        rows = response.json()
        if not rows:
            return pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"])
        df = pd.DataFrame(rows)
        df["ts"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df["vol"] = df["v"].astype(float)
        df["close_f"] = df["c"].astype(float)
        df["open_f"] = df["o"].astype(float)
        # Rough heuristic: bullish candle → most volume is taker buy.
        buy_frac = (df["close_f"] > df["open_f"]).astype(float) * 0.6 + 0.2
        df["taker_buy_volume"] = df["vol"] * buy_frac * df["close_f"]
        df["taker_sell_volume"] = df["vol"] * (1 - buy_frac) * df["close_f"]
        return df[["ts", "taker_buy_volume", "taker_sell_volume"]]
    except Exception:
        return pd.DataFrame(columns=["ts", "taker_buy_volume", "taker_sell_volume"])


async def fetch_liquidation_history(inst: Instrument, period: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch recent liquidations from Hyperliquid user fills endpoint.

    Hyperliquid exposes liquidations through the ``userFills`` endpoint
    filtered by ``liquidation`` type.  If data is unavailable (e.g.
    permissions), an empty DataFrame is returned gracefully.
    """
    payload = {
        "type": "userFills",
        "user": "0x0000000000000000000000000000000000000000",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await retry_async(
                lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
            )
            response.raise_for_status()
        rows = response.json()
        if not rows:
            return pd.DataFrame(columns=["ts", "liquidation_volume"])
        df = pd.DataFrame(rows)
        if "liquidation" not in df.columns:
            return pd.DataFrame(columns=["ts", "liquidation_volume"])
        liq = df[df["liquidation"].notna()].copy()
        if liq.empty:
            return pd.DataFrame(columns=["ts", "liquidation_volume"])
        liq["ts"] = pd.to_datetime(liq["time"], unit="ms", utc=True)
        liq["liquidation_volume"] = pd.to_numeric(liq["px"], errors="coerce").fillna(0) * pd.to_numeric(liq["sz"], errors="coerce").fillna(0)
        grouped = (
            liq.set_index("ts")
            .resample(period)
            .agg(liquidation_volume=("liquidation_volume", "sum"))
            .reset_index()
            .sort_values("ts")
        )
        return grouped[["ts", "liquidation_volume"]]
    except Exception:
        return pd.DataFrame(columns=["ts", "liquidation_volume"])


async def fetch_order_book_snapshot(inst: Instrument) -> dict:
    """Fetch L2 order book snapshot from Hyperliquid."""
    payload = {"type": "l2Book", "coin": inst.symbol}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await retry_async(
                lambda: client.post(f"{settings.hyperliquid_base_url}/info", json=payload)
            )
            response.raise_for_status()
        data = response.json()
        levels = data.get("levels", [[], []])
        bids = levels[0] if len(levels) > 0 else []
        asks = levels[1] if len(levels) > 1 else []
        if not bids or not asks:
            return {"spread_bps": 0.0, "orderbook_imbalance": 0.0}
        best_bid = float(bids[0].get("px", 0))
        best_ask = float(asks[0].get("px", 0))
        spread_bps = ((best_ask - best_bid) / best_bid) * 10_000 if best_bid else 0.0
        bid_depth = sum(float(item.get("sz", 0)) for item in bids[:10])
        ask_depth = sum(float(item.get("sz", 0)) for item in asks[:10])
        denom = bid_depth + ask_depth
        imbalance = ((bid_depth - ask_depth) / denom) if denom else 0.0
        return {"spread_bps": spread_bps, "orderbook_imbalance": imbalance}
    except Exception:
        return {"spread_bps": 0.0, "orderbook_imbalance": 0.0}

