from __future__ import annotations

from copy import deepcopy

from backend.core.types import RuleBlock, StrategySpec


def strategy_sweep_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    if spec.spec_id == "builtin-funding-mean-reversion":
        return _funding_variants(spec)
    if spec.spec_id == "builtin-momentum-with-vol-filter":
        return _momentum_variants(spec)
    if spec.spec_id == "builtin-range-breakout":
        return _breakout_variants(spec)
    return [("baseline", spec)]


def _funding_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for funding_threshold in (1.5, 2.0, 2.5):
        for vol_cap in (0.05, 0.08, 0.12):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{funding_threshold:.1f}/{vol_cap:.2f}]"
            clone.entry_long[0].threshold = -funding_threshold
            clone.entry_short[0].threshold = funding_threshold
            clone.regime_filters[0].threshold = vol_cap
            variants.append((f"z={funding_threshold:.1f}, vol<{vol_cap:.2f}", clone))
    return variants


def _momentum_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for ret_threshold in (0.005, 0.01, 0.015):
        for vol_ratio in (1.0, 1.2, 1.4):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{ret_threshold:.3f}/{vol_ratio:.1f}]"
            clone.entry_long[0].threshold = ret_threshold
            clone.entry_short[0].threshold = -ret_threshold
            clone.entry_long[1].threshold = vol_ratio
            clone.entry_short[1].threshold = vol_ratio
            variants.append((f"ret={ret_threshold:.3f}, vr>{vol_ratio:.1f}", clone))
    return variants


def _breakout_variants(spec: StrategySpec) -> list[tuple[str, StrategySpec]]:
    variants: list[tuple[str, StrategySpec]] = []
    for rank in (0.9, 0.95, 0.98):
        for vol_ratio in (1.2, 1.5, 1.8):
            clone = deepcopy(spec)
            clone.name = f"{spec.name} [{rank:.2f}/{vol_ratio:.1f}]"
            clone.entry_long[0].threshold = rank
            clone.entry_short[0].threshold = round(1 - rank, 2)
            clone.entry_long[1].threshold = vol_ratio
            clone.entry_short[1].threshold = vol_ratio
            variants.append((f"rank={rank:.2f}, vr>{vol_ratio:.1f}", clone))
    return variants
