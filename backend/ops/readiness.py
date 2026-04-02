from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.core.config import settings
from backend.data.storage import fetch_all
from backend.execution.service import live_secrets_status
from backend.paper.activity import portfolio_snapshot
from backend.strategy.targets import best_target_snapshot

FRESHNESS_WINDOWS = {
    "15m": timedelta(minutes=30),
    "1h": timedelta(hours=2),
    "4h": timedelta(hours=6),
}


def _parse_ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def readiness_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    health_rows = [dict(row) for row in fetch_all("SELECT * FROM dataset_health ORDER BY instrument_key, timeframe")]
    audit_count = fetch_all("SELECT COUNT(*) AS count FROM audit_events")[0]["count"] if health_rows is not None else 0
    paper_event_count = fetch_all("SELECT COUNT(*) AS count FROM paper_cycle_events")[0]["count"]
    reconciliation_count = fetch_all("SELECT COUNT(*) AS count FROM execution_reconciliation")[0]["count"]
    promoted_targets = fetch_all(
        "SELECT COUNT(*) AS count FROM strategy_targets WHERE status='promoted'"
    )[0]["count"]
    paper_targets = fetch_all(
        "SELECT COUNT(*) AS count FROM strategy_targets WHERE paper_enabled=1 AND status IN ('candidate','promoted')"
    )[0]["count"]

    health_issues: list[str] = []
    healthy_rows = 0
    fresh_rows = 0
    for row in health_rows:
        if row["quality"] == "healthy":
            healthy_rows += 1
        last_bar_ts = _parse_ts(row["last_bar_ts"])
        freshness_limit = FRESHNESS_WINDOWS.get(row["timeframe"], timedelta(hours=2))
        if last_bar_ts and now - last_bar_ts <= freshness_limit:
            fresh_rows += 1
        else:
            health_issues.append(f"stale_dataset:{row['instrument_key']}:{row['timeframe']}")
        if row["quality"] != "healthy":
            health_issues.append(f"quality_{row['quality']}:{row['instrument_key']}:{row['timeframe']}")
        if float(row["coverage_days"] or 0.0) < settings.data_readiness_coverage_days:
            health_issues.append(f"low_coverage:{row['instrument_key']}:{row['timeframe']}")

    data_ready = bool(health_rows) and not health_issues
    paper_ready = paper_targets > 0 and paper_event_count >= settings.paper_readiness_min_events
    best_target = best_target_snapshot()
    portfolio = portfolio_snapshot(limit=20)
    secrets = live_secrets_status()

    blockers: list[str] = []
    if not data_ready:
        blockers.append("data_health_not_ready")
    if promoted_targets == 0:
        blockers.append("no_promoted_targets")
    if paper_targets == 0:
        blockers.append("no_active_paper_targets")
    if paper_event_count < settings.paper_readiness_min_events:
        blockers.append("insufficient_paper_event_history")
    if not settings.paper_trading_enabled:
        blockers.append("paper_trading_disabled")
    if not settings.live_trading_enabled:
        blockers.append("live_trading_disabled_by_config")
    if not secrets["all_present"]:
        blockers.append("live_exchange_secrets_missing")
    if reconciliation_count == 0:
        blockers.append("no_execution_reconciliation_history")

    live_ready = (
        settings.live_trading_enabled
        and data_ready
        and promoted_targets > 0
        and paper_ready
        and secrets["all_present"]
        and reconciliation_count > 0
        and len(portfolio["positions"]) <= settings.paper_max_open_positions
    )

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "data_ready": data_ready,
            "paper_ready": paper_ready,
            "live_ready": live_ready,
            "blockers": blockers,
        },
        "counts": {
            "datasets": len(health_rows),
            "healthy_datasets": healthy_rows,
            "fresh_datasets": fresh_rows,
            "audit_events": audit_count,
            "paper_cycle_events": paper_event_count,
            "reconciliation_runs": reconciliation_count,
            "promoted_targets": promoted_targets,
            "active_paper_targets": paper_targets,
            "open_positions": len(portfolio["positions"]),
        },
        "risk": {
            "paper_trading_enabled": settings.paper_trading_enabled,
            "live_trading_enabled": settings.live_trading_enabled,
            "live_approval_mode": settings.live_approval_mode,
            "paper_max_open_positions": settings.paper_max_open_positions,
            "paper_daily_loss_limit_usd": settings.paper_daily_loss_limit_usd,
            "live_secrets": secrets,
        },
        "best_target": best_target,
        "recent_health_issues": health_issues[:20],
    }
