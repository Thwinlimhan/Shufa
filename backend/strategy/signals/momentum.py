from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Momentum With Vol Filter",
        hypothesis="Moderate-vol trend continuation persists when momentum and participation expand together.",
        feature_inputs=["ret_4", "vol_ratio", "trend_signal", "vol_20"],
    )
    spec.regime_filters = [RuleBlock(feature="vol_20", operator="between", threshold=(0.02, 0.08))]
    spec.entry_long = [
        RuleBlock(feature="ret_4", operator="gt", threshold=0.01),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.2),
        RuleBlock(feature="trend_signal", operator="gt", threshold=0),
    ]
    spec.entry_short = [
        RuleBlock(feature="ret_4", operator="lt", threshold=-0.01),
        RuleBlock(feature="vol_ratio", operator="gt", threshold=1.2),
        RuleBlock(feature="trend_signal", operator="lt", threshold=0),
    ]
    spec.tags = ["momentum", "trend"]
    return spec
