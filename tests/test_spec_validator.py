from backend.core.types import RuleBlock
from backend.strategy.signals.momentum import build as build_momentum
from backend.strategy.validator import validate_spec


def test_rejects_empty_hypothesis() -> None:
    spec = build_momentum()
    spec.hypothesis = ""
    result = validate_spec(spec)
    assert result.valid is False


def test_rejects_unknown_feature() -> None:
    spec = build_momentum()
    spec.entry_long = [RuleBlock(feature="made_up_feature", operator="gt", threshold=1)]
    result = validate_spec(spec)
    assert result.valid is False
