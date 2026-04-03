from datetime import datetime, timezone

from backend.core.types import Instrument, Venue, VenueMode
from backend.data import storage
from backend.paper.activity import portfolio_snapshot
from backend.paper.broker import fill_order, open_position, submit_order
from backend.strategy import registry, targets


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_portfolio_snapshot_groups_activity_by_target(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    registry.bootstrap_builtin_specs()
    targets.update_target_state(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        status="candidate",
        paper_enabled=True,
    )
    spec = registry.load_spec("builtin-range-breakout")
    assert spec is not None

    inst = Instrument(symbol="ETH", venue=Venue.BINANCE, mode=VenueMode.PERP)
    order = submit_order(spec, inst, "long", "open", 1_000.0, datetime.now(timezone.utc))
    fill_order(order, 101.0)
    open_position(order)

    snapshot = portfolio_snapshot()

    assert len(snapshot["active_targets"]) == 1
    assert snapshot["positions"][0]["symbol"] == "ETH"
    assert snapshot["orders"][0]["venue"] == "binance"
    assert snapshot["target_activity"][0]["recent_orders"] == 1
    assert snapshot["target_activity"][0]["open_positions"] == 1
