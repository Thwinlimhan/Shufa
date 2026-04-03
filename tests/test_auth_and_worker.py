from backend.auth.service import bootstrap_users, get_user_by_token
from backend.core.config import settings
from backend.data import storage
from backend.execution.service import approve_execution_ticket, create_execution_ticket
from backend.worker.jobs import list_jobs
from backend.worker.service import job_metrics


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    storage.reset_sqlite_connection()


def test_bootstrap_users_supports_default_operator_tokens(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    bootstrap_users()

    operator = get_user_by_token(settings.auth_operator_token)

    assert operator["role"] == "operator"
    assert operator["display_name"] == "Operator"


def test_approved_live_ticket_queues_when_enabled_and_secrets_present(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    from backend.execution import service

    monkeypatch.setattr(service, "live_secrets_status", lambda: {"all_present": True, "venues": {"binance": True, "hyperliquid": True}})
    monkeypatch.setattr(
        service,
        "settings",
        type("DummySettings", (), {"live_trading_enabled": True, "live_approval_mode": True})(),
    )

    ticket = create_execution_ticket(
        spec_id="builtin-range-breakout",
        symbol="ETH",
        venue="binance",
        direction="long",
        action="open",
        size_usd=1000.0,
    )
    approved = approve_execution_ticket(ticket["ticket_id"])
    jobs = list_jobs()
    metrics = job_metrics()

    assert approved["status"] == "queued"
    assert len(jobs) == 1
    assert jobs[0]["job_type"] == "execution_submit"
    assert metrics["queued"] == 1
