from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import websockets


async def stream_mark_prices(symbols: list[str], callback: Callable[[dict], Awaitable[None]]) -> None:
    if not symbols:
        return
    url = "wss://api.hyperliquid.xyz/ws"
    async with websockets.connect(url) as ws:  # pragma: no cover - network runtime
        await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "allMids"}}))
        async for msg in ws:
            payload = json.loads(msg)
            data = payload.get("data") or {}
            mids = data.get("mids") or data
            if not isinstance(mids, dict):
                continue
            for symbol in symbols:
                if symbol not in mids:
                    continue
                try:
                    mark_price = float(mids[symbol])
                except Exception:
                    continue
                if mark_price <= 0:
                    continue
                await callback(
                    {
                        "venue": "hyperliquid",
                        "symbol": symbol,
                        "price": mark_price,
                        "ts": None,
                    }
                )
