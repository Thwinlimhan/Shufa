from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import websockets


async def stream_mark_prices(symbols: list[str], callback: Callable[[dict], Awaitable[None]]) -> None:
    if not symbols:
        return
    streams = "/".join(f"{symbol.lower()}usdt@markPrice" for symbol in symbols)
    url = f"wss://fstream.binance.com/stream?streams={streams}"
    async with websockets.connect(url) as ws:  # pragma: no cover - network runtime
        async for msg in ws:
            payload = json.loads(msg)
            data = payload.get("data", {})
            symbol = str(data.get("s", "")).replace("USDT", "")
            mark_price = float(data.get("p", 0.0))
            if not symbol or mark_price <= 0:
                continue
            await callback(
                {
                    "venue": "binance",
                    "symbol": symbol,
                    "price": mark_price,
                    "ts": int(data.get("E", 0)),
                }
            )
