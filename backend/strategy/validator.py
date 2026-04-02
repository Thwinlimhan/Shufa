from __future__ import annotations

from dataclasses import dataclass, field

from backend.core.types import RuleBlock, StrategySpec

ALLOWED_OPERATORS = {"gt", "lt", "gte", "lte", "between", "crossover", "crossunder", "eq", "neq"}
KNOWN_FEATURES = {
    "ret_1",
    "ret_4",
    "vol_20",
    "vol_ratio",
    "atr_14",
    "rsi_14",
    "pct_rank_20",
    "trend_signal",
    "funding_rate",
    "funding_zscore",
    "close",
    "volume_quote",
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _validate_rule(rule: RuleBlock, errors: list[str], field_name: str) -> None:
    if rule.feature not in KNOWN_FEATURES:
        errors.append(f"{field_name}: unknown feature '{rule.feature}'")
    if rule.operator not in ALLOWED_OPERATORS:
        errors.append(f"{field_name}: unsupported operator '{rule.operator}'")
    if rule.operator == "between" and not isinstance(rule.threshold, tuple):
        errors.append(f"{field_name}: 'between' requires a tuple threshold")


def validate_spec(spec: StrategySpec) -> ValidationResult:
    errors: list[str] = []
    if not spec.name.strip():
        errors.append("name is required")
    if not spec.hypothesis.strip():
        errors.append("hypothesis is required")
    if not spec.universe:
        errors.append("universe cannot be empty")

    for field_name in ("regime_filters", "entry_long", "entry_short", "exit_long", "exit_short"):
        rules = getattr(spec, field_name)
        for index, rule in enumerate(rules):
            _validate_rule(rule, errors, f"{field_name}[{index}]")

    if not spec.entry_long and not spec.entry_short:
        errors.append("at least one entry side must be defined")

    if spec.sizing.method == "fixed_notional" and not spec.sizing.fixed_notional_usd:
        errors.append("fixed_notional method requires fixed_notional_usd")

    return ValidationResult(valid=not errors, errors=errors)
