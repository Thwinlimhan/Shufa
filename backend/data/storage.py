from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    import duckdb
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without duckdb installed
    duckdb = None

from backend.core.config import settings
from backend.core.types import Instrument, Timeframe

RAW_ROOT = settings.raw_data_root
CURATED_DB = settings.curated_db_path
META_DB = settings.meta_db_path
_SQLITE_CONNECTION: sqlite3.Connection | None = None


def ensure_data_dirs() -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    CURATED_DB.parent.mkdir(parents=True, exist_ok=True)
    META_DB.parent.mkdir(parents=True, exist_ok=True)


def raw_path(inst: Instrument, tf: Timeframe, year: int, month: int) -> Path:
    root = RAW_ROOT / inst.venue.value / inst.symbol / tf.value
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{year:04d}-{month:02d}.parquet"


def funding_raw_path(inst: Instrument, year: int, month: int) -> Path:
    root = RAW_ROOT / inst.venue.value / inst.symbol / "funding"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{year:04d}-{month:02d}.parquet"


def market_context_raw_path(inst: Instrument, dataset: str, year: int, month: int) -> Path:
    root = RAW_ROOT / inst.venue.value / inst.symbol / "context" / dataset
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{year:04d}-{month:02d}.parquet"


def write_bars(inst: Instrument, tf: Timeframe, df: pd.DataFrame) -> None:
    if df.empty:
        return
    ensure_data_dirs()
    working = df.copy()
    working["ts_open"] = pd.to_datetime(working["ts_open"], utc=True)
    if "ts_close" in working.columns:
        working["ts_close"] = pd.to_datetime(working["ts_close"], utc=True)
    for (year, month), group in working.groupby([working["ts_open"].dt.year, working["ts_open"].dt.month]):
        path = raw_path(inst, tf, int(year), int(month))
        if path.exists():
            existing = pd.read_parquet(path)
            group = pd.concat([existing, group], ignore_index=True)
        deduped = group.drop_duplicates(subset="ts_open", keep="last").sort_values("ts_open")
        deduped.to_parquet(path, index=False)


def write_funding(inst: Instrument, df: pd.DataFrame) -> None:
    if df.empty:
        return
    ensure_data_dirs()
    working = df.copy()
    working["ts"] = pd.to_datetime(working["ts"], utc=True)
    for (year, month), group in working.groupby([working["ts"].dt.year, working["ts"].dt.month]):
        path = funding_raw_path(inst, int(year), int(month))
        if path.exists():
            existing = pd.read_parquet(path)
            group = pd.concat([existing, group], ignore_index=True)
        deduped = group.drop_duplicates(subset="ts", keep="last").sort_values("ts")
        deduped.to_parquet(path, index=False)


def write_market_context(inst: Instrument, dataset: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    ensure_data_dirs()
    if "ts" not in df.columns:
        raise ValueError("market_context_requires_ts_column")
    working = df.copy()
    working["ts"] = pd.to_datetime(working["ts"], utc=True)
    for (year, month), group in working.groupby([working["ts"].dt.year, working["ts"].dt.month]):
        path = market_context_raw_path(inst, dataset, int(year), int(month))
        if path.exists():
            existing = pd.read_parquet(path)
            group = pd.concat([existing, group], ignore_index=True)
        deduped = group.drop_duplicates(subset="ts", keep="last").sort_values("ts")
        deduped.to_parquet(path, index=False)


def read_bars(inst: Instrument, tf: Timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in range(start.year, end.year + 1):
        for month in range(1, 13):
            path = raw_path(inst, tf, year, month)
            if path.exists():
                frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["ts_open"] = pd.to_datetime(df["ts_open"], utc=True)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize("UTC")
    else:
        start_ts = start_ts.tz_convert("UTC")
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    else:
        end_ts = end_ts.tz_convert("UTC")
    mask = (df["ts_open"] >= start_ts) & (df["ts_open"] <= end_ts)
    return df.loc[mask].sort_values("ts_open").reset_index(drop=True)


def read_funding(inst: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in range(start.year, end.year + 1):
        for month in range(1, 13):
            path = funding_raw_path(inst, year, month)
            if path.exists():
                frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize("UTC")
    else:
        start_ts = start_ts.tz_convert("UTC")
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    else:
        end_ts = end_ts.tz_convert("UTC")
    mask = (df["ts"] >= start_ts) & (df["ts"] <= end_ts)
    return df.loc[mask].sort_values("ts").reset_index(drop=True)


def read_market_context(inst: Instrument, dataset: str, start: datetime, end: datetime) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in range(start.year, end.year + 1):
        for month in range(1, 13):
            path = market_context_raw_path(inst, dataset, year, month)
            if path.exists():
                frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame(columns=["ts"])
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize("UTC")
    else:
        start_ts = start_ts.tz_convert("UTC")
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    else:
        end_ts = end_ts.tz_convert("UTC")
    mask = (df["ts"] >= start_ts) & (df["ts"] <= end_ts)
    return df.loc[mask].sort_values("ts").reset_index(drop=True)


def get_duckdb():
    if duckdb is None:
        raise RuntimeError("duckdb is not installed in the active Python environment")
    ensure_data_dirs()
    con = duckdb.connect(str(CURATED_DB))
    _init_duckdb_views(con)
    return con


def _safe_parquet_glob(tf: str) -> str:
    return str(RAW_ROOT / "*" / "*" / tf / "*.parquet").replace("\\", "/")


def _init_duckdb_views(con) -> None:
    for timeframe in ("15m", "1h", "4h"):
        view_name = f"raw_bars_{timeframe.replace('m', 'm').replace('h', 'h')}"
        paths = list(RAW_ROOT.glob(f"*/*/{timeframe}/*.parquet"))
        if paths:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT * FROM read_parquet('{_safe_parquet_glob(timeframe)}', union_by_name=true)
                """
            )
        else:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT
                    CAST(NULL AS TIMESTAMP) AS ts_open,
                    CAST(NULL AS TIMESTAMP) AS ts_close,
                    CAST(NULL AS DOUBLE) AS open,
                    CAST(NULL AS DOUBLE) AS high,
                    CAST(NULL AS DOUBLE) AS low,
                    CAST(NULL AS DOUBLE) AS close,
                    CAST(NULL AS DOUBLE) AS volume,
                    CAST(NULL AS DOUBLE) AS volume_quote,
                    CAST(NULL AS INTEGER) AS trades
                WHERE FALSE
                """
            )


def get_sqlite() -> sqlite3.Connection:
    global _SQLITE_CONNECTION
    if _SQLITE_CONNECTION is None:
        ensure_data_dirs()
        con = sqlite3.connect(str(META_DB), check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.row_factory = sqlite3.Row
        _init_sqlite(con)
        _apply_sqlite_migrations(con)
        _SQLITE_CONNECTION = con
    return _SQLITE_CONNECTION


def _init_sqlite(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategy_specs (
            spec_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version INTEGER NOT NULL,
            parent_id TEXT,
            status TEXT NOT NULL DEFAULT 'proposed',
            spec_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            config_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            ran_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS promotion_decisions (
            decision_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            policy_json TEXT NOT NULL,
            passed INTEGER NOT NULL,
            failures_json TEXT NOT NULL,
            decided_at TEXT NOT NULL,
            approved_by TEXT
        );

        CREATE TABLE IF NOT EXISTS paper_positions (
            position_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            instrument_json TEXT NOT NULL,
            direction TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            entry_price TEXT NOT NULL,
            size_usd REAL NOT NULL,
            unrealized_pnl_usd REAL DEFAULT 0,
            accrued_funding_usd REAL DEFAULT 0,
            entry_fees_usd REAL NOT NULL DEFAULT 0,
            closed_at TEXT,
            close_price TEXT,
            realized_pnl_usd REAL
        );

        CREATE TABLE IF NOT EXISTS paper_orders (
            order_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            instrument_json TEXT NOT NULL,
            direction TEXT NOT NULL,
            action TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            size_usd REAL NOT NULL,
            fill_price TEXT,
            filled_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS dataset_health (
            instrument_key TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            quality TEXT NOT NULL,
            last_bar_ts TEXT,
            gap_count INTEGER DEFAULT 0,
            duplicate_count INTEGER DEFAULT 0,
            coverage_days REAL DEFAULT 0,
            checked_at TEXT NOT NULL,
            PRIMARY KEY (instrument_key, timeframe)
        );

        CREATE TABLE IF NOT EXISTS runner_state (
            job_name TEXT PRIMARY KEY,
            last_processed_ts TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS strategy_targets (
            target_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            venue TEXT NOT NULL,
            mode TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'shortlist',
            paper_enabled INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            last_backtest_run_id TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(spec_id, symbol, venue)
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS paper_cycle_events (
            event_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            venue TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            event_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS execution_tickets (
            ticket_id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            venue TEXT NOT NULL,
            direction TEXT NOT NULL,
            action TEXT NOT NULL,
            size_usd REAL NOT NULL,
            status TEXT NOT NULL,
            approval_mode TEXT NOT NULL,
            requested_by TEXT,
            rationale TEXT,
            preview_json TEXT NOT NULL,
            broker_order_id TEXT,
            created_at TEXT NOT NULL,
            approved_at TEXT,
            submitted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS execution_reconciliation (
            reconciliation_id TEXT PRIMARY KEY,
            venue TEXT NOT NULL,
            status TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS app_users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_queue (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            result_json TEXT,
            priority INTEGER NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            finished_at TEXT
        );

        CREATE TABLE IF NOT EXISTS job_dead_letters (
            dead_letter_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            job_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            last_error TEXT,
            failed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS worker_heartbeat (
            worker_id TEXT PRIMARY KEY,
            last_seen TEXT NOT NULL,
            status TEXT NOT NULL,
            details_json TEXT
        );

        CREATE TABLE IF NOT EXISTS market_marks (
            instrument_key TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            venue TEXT NOT NULL,
            price REAL NOT NULL,
            ts TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_paper_positions_spec_id ON paper_positions(spec_id);
        CREATE INDEX IF NOT EXISTS idx_paper_positions_closed ON paper_positions(closed_at);
        CREATE INDEX IF NOT EXISTS idx_paper_orders_spec ON paper_orders(spec_id);
        CREATE INDEX IF NOT EXISTS idx_strategy_targets_spec ON strategy_targets(spec_id);
        CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status, priority, created_at);
        """
    )
    _ensure_column(con, "job_queue", "attempt_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(con, "job_queue", "last_error", "TEXT")
    _ensure_column(con, "job_queue", "next_attempt_at", "TEXT")
    _ensure_column(con, "paper_positions", "entry_fees_usd", "REAL NOT NULL DEFAULT 0")
    con.commit()


def _ensure_column(con: sqlite3.Connection, table: str, column: str, sql_type: str) -> None:
    row = con.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {item["name"] for item in row}
    if column in existing:
        return
    con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")


def _apply_sqlite_migrations(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    migrations_dir = Path(__file__).resolve().parent / "migrations" / "sqlite"
    if not migrations_dir.exists():
        return
    applied_rows = con.execute("SELECT migration_id FROM schema_migrations").fetchall()
    applied = {row["migration_id"] for row in applied_rows}
    for path in sorted(migrations_dir.glob("*.sql")):
        migration_id = path.stem
        if migration_id in applied:
            continue
        con.executescript(path.read_text(encoding="utf-8"))
        con.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            [migration_id, datetime.now(timezone.utc).isoformat()],
        )


def upsert_dataset_health(rows: Iterable[dict]) -> None:
    con = get_sqlite()
    con.executemany(
        """
        INSERT INTO dataset_health (
            instrument_key, timeframe, quality, last_bar_ts,
            gap_count, duplicate_count, coverage_days, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_key, timeframe) DO UPDATE SET
            quality=excluded.quality,
            last_bar_ts=excluded.last_bar_ts,
            gap_count=excluded.gap_count,
            duplicate_count=excluded.duplicate_count,
            coverage_days=excluded.coverage_days,
            checked_at=excluded.checked_at
        """,
        [
            (
                row["instrument_key"],
                row["timeframe"],
                row["quality"],
                row.get("last_bar_ts"),
                row["gap_count"],
                row["duplicate_count"],
                row["coverage_days"],
                row["checked_at"],
            )
            for row in rows
        ],
    )
    con.commit()


def save_json_record(table: str, payload: dict, key_field: str) -> None:
    con = get_sqlite()
    columns = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    update_cols = ", ".join(f"{column}=excluded.{column}" for column in payload if column != key_field)
    con.execute(
        f"""
        INSERT INTO {table} ({columns})
        VALUES ({placeholders})
        ON CONFLICT({key_field}) DO UPDATE SET {update_cols}
        """,
        list(payload.values()),
    )
    con.commit()


def fetch_all(query: str, params: tuple | list) -> list[sqlite3.Row]:
    con = get_sqlite()
    return con.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple | list | None = None) -> sqlite3.Row | None:
    con = get_sqlite()
    return con.execute(query, params or []).fetchone()


def set_runner_state(job_name: str, last_processed_ts: str) -> None:
    save_json_record(
        "runner_state",
        {"job_name": job_name, "last_processed_ts": last_processed_ts},
        "job_name",
    )


def save_mark_price(instrument_key: str, symbol: str, venue: str, price: float, ts: str) -> None:
    save_json_record(
        "market_marks",
        {
            "instrument_key": instrument_key,
            "symbol": symbol,
            "venue": venue,
            "price": float(price),
            "ts": ts,
        },
        "instrument_key",
    )


def get_mark_price(instrument_key: str) -> dict | None:
    row = fetch_one("SELECT * FROM market_marks WHERE instrument_key=?", [instrument_key])
    return dict(row) if row else None


def reset_sqlite_connection() -> None:
    global _SQLITE_CONNECTION
    if _SQLITE_CONNECTION is not None:
        _SQLITE_CONNECTION.close()
    _SQLITE_CONNECTION = None
