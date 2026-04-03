from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings
from backend.data.storage import get_sqlite


def backup_datastores() -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path("./data/backups") / ts
    backup_root.mkdir(parents=True, exist_ok=True)

    sqlite_src = settings.meta_db_path
    duckdb_src = settings.curated_db_path
    sqlite_dst = backup_root / sqlite_src.name
    duckdb_dst = backup_root / duckdb_src.name
    if sqlite_src.exists():
        shutil.copy2(sqlite_src, sqlite_dst)
    if duckdb_src.exists():
        shutil.copy2(duckdb_src, duckdb_dst)

    integrity = get_sqlite().execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "created_at": ts,
        "backup_dir": str(backup_root),
        "sqlite_copied": sqlite_dst.exists(),
        "duckdb_copied": duckdb_dst.exists(),
        "sqlite_integrity": integrity,
    }
