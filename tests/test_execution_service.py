from backend.data import storage
from backend.execution.service import (
    approve_execution_ticket,
    create_execution_ticket,
    list_reconciliation,
    live_secrets_status,
    reconcile_venue,
)


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_create_execution_ticket_builds_preview(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )

    assert ticket["status"] == "pending_approval"
    assert ticket["preview"]["approval_required"] is True
    assert ticket["preview"]["estimated_fee_usd"] > 0


def test_approve_execution_ticket_blocks_when_live_is_disabled(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )
    approved = approve_execution_ticket(ticket["ticket_id"])

    assert approved["status"] == "blocked"


def test_reconcile_venue_persists_snapshot(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    result = reconcile_venue("binance")
    rows = list_reconciliation()

    assert result["venue"] == "binance"
    assert len(rows) == 1
    assert rows[0]["status"] == "approval_mode"


def test_live_secrets_status_defaults_missing() -> None:
    status = live_secrets_status()
    assert status["all_present"] is False
