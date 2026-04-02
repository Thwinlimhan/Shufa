import json

from backend.data import storage
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")


def test_infer_target_status_promotes_strong_runs() -> None:
    status, note = targets.infer_target_status(
        {
            "sharpe": 1.36,
            "total_return_pct": 0.05,
            "total_trades": 57,
            "max_drawdown_pct": 0.03,
        },
        {"passed": False, "policy": {"min_trade_count": 30}},
    )

    assert status == "promoted"
    assert "Auto-promoted" in note


def test_sync_target_with_backtest_disables_rejected_paper_targets(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="candidate",
        paper_enabled=True,
    )

    synced = targets.sync_target_with_backtest(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        result={
            "run_id": "run-reject",
            "sharpe": -1.1,
            "total_return_pct": -3.0,
            "total_trades": 4,
            "max_drawdown_pct": 14.0,
        },
        decision={"passed": False, "policy": {"min_trade_count": 30}},
    )

    assert synced["status"] == "rejected"
    assert synced["paper_enabled"] == 0
    assert synced["last_backtest_run_id"] == "run-reject"


def test_best_target_snapshot_uses_latest_target_runs(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()

    storage.save_json_record(
        "backtest_runs",
        {
            "run_id": "run-eth",
            "spec_id": "builtin-range-breakout",
            "config_json": json.dumps({"instrument": {"symbol": "ETH", "venue": "binance"}}),
            "result_json": json.dumps({"sharpe": 1.36, "total_return_pct": 0.05, "total_trades": 57}),
            "ran_at": "2026-04-02T00:00:00+00:00",
        },
        "run_id",
    )
    storage.save_json_record(
        "backtest_runs",
        {
            "run_id": "run-btc",
            "spec_id": "builtin-funding-mean-reversion",
            "config_json": json.dumps({"instrument": {"symbol": "BTC", "venue": "binance"}}),
            "result_json": json.dumps({"sharpe": 0.37, "total_return_pct": 0.02, "total_trades": 23}),
            "ran_at": "2026-04-02T00:10:00+00:00",
        },
        "run_id",
    )
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        last_backtest_run_id="run-eth",
    )
    targets.update_target_state(
        spec_id="builtin-funding-mean-reversion",
        symbol="BTC",
        venue="binance",
        status="candidate",
        last_backtest_run_id="run-btc",
    )

    snapshot = targets.best_target_snapshot()

    assert snapshot is not None
    assert snapshot["spec_id"] == "builtin-range-breakout"
    assert snapshot["symbol"] == "ETH"
    assert snapshot["result"]["sharpe"] == 1.36
