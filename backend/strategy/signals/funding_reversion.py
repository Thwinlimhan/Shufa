from __future__ import annotations

from backend.core.types import RuleBlock
from backend.strategy.spec import new_strategy


def build():
    spec = new_strategy(
        name="Funding Mean Reversion",
        hypothesis="Extreme funding is often followed by short-term reversion once positioning becomes crowded.",
        feature_inputs=["funding_rate", "funding_zscore", "vol_20"],
    )
    spec.regime_filters = [RuleBlock(feature="vol_20", operator="lt", threshold=0.08)]
    spec.entry_long = [RuleBlock(feature="funding_zscore", operator="lt", threshold=-2.0)]
    spec.entry_short = [RuleBlock(feature="funding_zscore", operator="gt", threshold=2.0)]
    spec.exit_long = [RuleBlock(feature="funding_zscore", operator="gte", threshold=0.0)]
    spec.exit_short = [RuleBlock(feature="funding_zscore", operator="lte", threshold=0.0)]
    spec.tags = ["funding", "mean_reversion"]
    return spec
