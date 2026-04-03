from datetime import datetime, timezone

from backend.data import storage
from backend.data.storage import fetch_all
from backend.paper.runner import run_bar
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_run_bar_logs_risk_block_event_for_low_volume(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )

    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2500.0,
            "volume_quote": 100.0,
            "pct_rank_20": 0.99,
            "vol_ratio": 2.1,
        }
    )

    rows = fetch_all("SELECT * FROM paper_cycle_events ORDER BY created_at DESC", [])

    assert len(rows) == 1
    assert rows[0]["event_type"] == "skipped"
    assert rows[0]["reason"] == "min_volume_not_met"


def test_run_bar_full_cycle_opens_and_closes_position(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )

    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2500.0,
            "volume_quote": 1_200_000.0,
            "pct_rank_20": 0.99,
            "vol_ratio": 2.1,
            "atr_14": 22.0,
            "vol_20": 0.04,
        }
    )
    run_bar(
        {
            "timeframe": "1h",
            "symbol": "ETH",
            "venue": "binance",
            "ts": datetime.now(timezone.utc),
            "close": 2475.0,
            "volume_quote": 1_400_000.0,
            "pct_rank_20": 0.01,
            "vol_ratio": 2.2,
            "atr_14": 25.0,
            "vol_20": 0.05,
        }
    )

    positions = fetch_all("SELECT * FROM paper_positions ORDER BY opened_at DESC", [])
    orders = fetch_all("SELECT * FROM paper_orders ORDER BY triggered_at DESC", [])
    events = fetch_all("SELECT * FROM paper_cycle_events ORDER BY created_at DESC", [])

    assert len(orders) >= 2
    assert len(positions) >= 1
    assert any(row["closed_at"] is not None for row in positions)
    assert any(row["event_type"] == "position_opened" for row in events)
    assert any(row["event_type"] == "position_closed" for row in events)
