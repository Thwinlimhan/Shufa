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
