import pytest

from backend.data import storage
from backend.secrets import vault
from backend.worker.jobs import enqueue_job
from backend.worker import service as worker_service


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")
    monkeypatch.setattr(
        vault,
        "settings",
        type("DummySettings", (), {"vault_file_path": tmp_path / "meta" / "secrets.vault", "vault_passphrase": "unit-test-passphrase"})(),
    )


def test_vault_round_trip(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)

    if not vault.CRYPTOGRAPHY_AVAILABLE:
        with pytest.raises(RuntimeError, match="vault_dependency_missing"):
            vault.set_secret("binance_api_key", "abc123")
        status = vault.vault_status()
        assert status["available"] is False
        return

    status = vault.set_secret("binance_api_key", "abc123")

    assert status["exists"] is True
    assert vault.get_secret("binance_api_key") == "abc123"


def test_process_next_job_completes_execution_submit(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(
        worker_service,
        "process_execution_job",
        lambda payload: {"ticket_id": payload["ticket_id"], "submission": {"status": "ok"}},
    )
    job = enqueue_job("execution_submit", {"ticket_id": "t-1"})

    completed = worker_service.process_next_job()

    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["job_id"] == job["job_id"]
