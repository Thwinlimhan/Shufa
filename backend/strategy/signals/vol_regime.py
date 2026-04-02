from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Range Breakout",
        hypothesis="Breaks of a tight range with expanding volume tend to continue in the direction of the breakout.",
        feature_inputs=["pct_rank_20", "vol_ratio"],
    )
    spec.entry_long = [
        RuleBlock(feature="pct_rank_20", operator="gt", threshold=0.95),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.5),
    ]
    spec.entry_short = [
        RuleBlock(feature="pct_rank_20", operator="lt", threshold=0.05),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.5),
    ]
    spec.tags = ["breakout", "range"]
    return spec
