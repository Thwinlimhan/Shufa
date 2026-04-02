from __future__ import annotations


def round_trip_cost(size_usd: float, fee_bps: float, slippage_bps: float) -> float:
    return size_usd * ((fee_bps + slippage_bps * 2) / 10_000)
