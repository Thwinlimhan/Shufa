from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest.engine import run_backtest
from backend.core.types import BacktestConfig, RuleBlock
from backend.strategy.engine import evaluate_rules
from backend.strategy.signals.momentum import build as build_momentum


def test_rule_evaluation_gt() -> None:
    rule = RuleBlock(feature="rsi_14", operator="gt", threshold=70)
    assert evaluate_rules([rule], {"rsi_14": 75}) is True
    assert evaluate_rules([rule], {"rsi_14": 65}) is False


def test_fees_and_backtest_runs() -> None:
    spec = build_momentum()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(80):
        rows.append(
            {
                "ts_open": start + timedelta(hours=index),
                "open": 100 + index,
                "high": 101 + index,
                "low": 99 + index,
                "close": 100 + index,
                "volume": 10,
                "volume_quote": 1_000_000,
                "ret_4": 0.02 if index % 10 < 5 else -0.02,
                "vol_ratio": 1.5,
                "trend_signal": 1 if index % 10 < 5 else -1,
                "vol_20": 0.05,
            }
        )
    result = run_backtest(spec, pd.DataFrame(rows), BacktestConfig(start_date=start, end_date=start + timedelta(hours=80)))
    assert result.total_trades > 0
    assert result.avg_trade_pnl_usd != 0
