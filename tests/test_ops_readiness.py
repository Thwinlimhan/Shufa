from datetime import datetime, timedelta, timezone

from backend.data import storage
from backend.ops.audit import record_audit_event
from backend.ops.readiness import readiness_snapshot
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")


def test_readiness_reports_live_blockers_when_live_is_disabled(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    now = datetime.now(timezone.utc)
    storage.upsert_dataset_health(
        [
            {
                "instrument_key": "binance:perp:BTC/USDT",
                "timeframe": "1h",
                "quality": "healthy",
                "last_bar_ts": (now - timedelta(minutes=30)).isoformat(),
                "gap_count": 0,
                "duplicate_count": 0,
                "coverage_days": 25.0,
                "checked_at": now.isoformat(),
            }
        ]
    )
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="promoted",
        paper_enabled=True,
    )
    record_audit_event("test.event", "system", "one", {"ok": True})

    snapshot = readiness_snapshot()

    assert snapshot["summary"]["data_ready"] is True
    assert snapshot["summary"]["live_ready"] is False
    assert "live_trading_disabled_by_config" in snapshot["summary"]["blockers"]
    assert snapshot["counts"]["audit_events"] >= 1

