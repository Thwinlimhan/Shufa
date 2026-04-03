from __future__ import annotations

from backend.core.types import RuleBlock, StrategySpec


def evaluate_rule(rule: RuleBlock, features: dict[str, float]) -> bool:
    if rule.feature not in features:
        return False
    value = features[rule.feature]
    threshold = rule.threshold
    match rule.operator:
        case "gt":
            return value > threshold
        case "lt":
            return value < threshold
        case "gte":
            return value >= threshold
        case "lte":
            return value <= threshold
        case "eq":
            return value == threshold
        case "neq":
            return value != threshold
        case "between":
            lower, upper = threshold
            return lower <= value <= upper
        case "crossover":
            previous = features.get(f"{rule.feature}_prev")
            return previous is not None and previous <= threshold < value
        case "crossunder":
            previous = features.get(f"{rule.feature}_prev")
            return previous is not None and previous >= threshold > value
        case _:
            return False


def evaluate_rules(rules: list[RuleBlock], features: dict[str, float]) -> bool:
    return all(evaluate_rule(rule, features) for rule in rules)


def get_signal(spec: StrategySpec, features: dict[str, float]) -> str:
    if spec.regime_filters and not evaluate_rules(spec.regime_filters, features):
        return "flat"
    if spec.entry_long and evaluate_rules(spec.entry_long, features):
        return "long"
    if spec.entry_short and evaluate_rules(spec.entry_short, features):
        return "short"
    return "flat"


def get_signal_with_position(
    spec: StrategySpec,
    features: dict[str, float],
    current_direction: str | None = None,
) -> str:
    """Return a trading signal that also respects exit rules.

    When *current_direction* is ``"long"`` or ``"short"`` and the
    strategy defines ``exit_long`` / ``exit_short`` rules, an exit
    signal (``"flat"``) is produced when those rules fire — even if
    entry rules for the *same* side would otherwise keep the position
    open.
    """
    if spec.regime_filters and not evaluate_rules(spec.regime_filters, features):
        return "flat"

    # Check exit rules first when a position is already open.
    if current_direction == "long" and spec.exit_long:
        if evaluate_rules(spec.exit_long, features):
            return "flat"
    if current_direction == "short" and spec.exit_short:
        if evaluate_rules(spec.exit_short, features):
            return "flat"

    if spec.entry_long and evaluate_rules(spec.entry_long, features):
        return "long"
    if spec.entry_short and evaluate_rules(spec.entry_short, features):
        return "short"
    return "flat"

