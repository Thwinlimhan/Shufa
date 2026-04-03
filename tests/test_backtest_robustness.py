from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.backtest import engine
from backend.core.types import BacktestConfig
from backend.strategy.signals.momentum import build as build_momentum


def test_backtest_robustness_metrics_are_applied(monkeypatch) -> None:
    spec = build_momentum()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(90):
        rows.append(
            {
                "ts_open": start + timedelta(hours=index),
                "close": 100 + index * 0.5,
                "ret_4": 0.02 if index % 9 < 5 else -0.02,
                "vol_ratio": 1.5,
                "trend_signal": 1 if index % 9 < 5 else -1,
                "vol_20": 0.05,
            }
        )
    frame = pd.DataFrame(rows)
    config = BacktestConfig(start_date=start, end_date=start + timedelta(hours=90))

    monkeypatch.setattr(engine, "_compute_perturbation_sharpe", lambda *args, **kwargs: (1.23, 0.11))
    monkeypatch.setattr(engine, "_compute_oos_sharpe", lambda *args, **kwargs: 0.77)

    result = engine.run_backtest(spec, frame, config)

    assert result.perturbation_sharpe_mean == 1.23
    assert result.perturbation_sharpe_std == 0.11
    assert result.oos_sharpe == 0.77
