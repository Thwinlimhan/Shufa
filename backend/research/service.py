from __future__ import annotations

from datetime import datetime, timezone

from backend.core.types import Timeframe
from backend.data.service import default_instruments, latest_feature_bar_async
from backend.research.orchestrator import run_market_structure_analysis


async def build_feature_summary() -> dict:
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "markets": []}
    for inst in default_instruments():
        bar = await latest_feature_bar_async(inst, Timeframe.H1)
        if not bar:
            continue
        summary["markets"].append(
            {
                "symbol": inst.symbol,
                "venue": inst.venue.value,
                "ret_4": float(bar.get("ret_4", 0.0)),
                "vol_20": float(bar.get("vol_20", 0.0)),
                "vol_ratio": float(bar.get("vol_ratio", 0.0)),
                "funding_zscore": float(bar.get("funding_zscore", 0.0)),
                "oi_change_pct": float(bar.get("oi_change_pct", 0.0)),
            }
        )
    return summary


async def research_digest() -> dict:
    feature_summary = await build_feature_summary()
    analysis = await run_market_structure_analysis(feature_summary)
    return {"feature_summary": feature_summary, "analysis": analysis}
