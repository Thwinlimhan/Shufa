from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from backend.backtest.service import compare_runs, correlation_for_spec, execute_backtest, monte_carlo_for_run, sweep_runs, walk_forward
from backend.auth.service import require_role
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.ops.audit import record_audit_event
from backend.strategy.targets import sync_target_with_backtest

router = APIRouter()


@router.get("")
def list_backtests() -> list[dict]:
    rows = fetch_all("SELECT * FROM backtest_runs ORDER BY ran_at DESC", [])
    return [
        {
            "run_id": row["run_id"],
            "spec_id": row["spec_id"],
            "config": json.loads(row["config_json"]),
            "result": json.loads(row["result_json"]),
            "ran_at": row["ran_at"],
        }
        for row in rows
    ]


@router.post("")
def create_backtest(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    target = None
    result, decision = execute_backtest(
        spec_id=spec_id,
        symbol=payload.get("symbol"),
        venue=payload.get("venue"),
        lookback_days=payload.get("lookback_days", 120),
    )
    save_json_record(
        "backtest_runs",
        {
            "run_id": result["run_id"],
            "spec_id": result["spec_id"],
            "config_json": json.dumps(result["config"]),
            "result_json": json.dumps(result),
            "ran_at": result["ran_at"],
        },
        "run_id",
    )
    save_json_record(
        "promotion_decisions",
        {
            "decision_id": f"{result['run_id']}:auto",
            "spec_id": result["spec_id"],
            "run_id": result["run_id"],
            "policy_json": json.dumps(decision["policy"]),
            "passed": 1 if decision["passed"] else 0,
            "failures_json": json.dumps(decision["failures"]),
            "decided_at": decision["decided_at"],
            "approved_by": decision["approved_by"],
        },
        "decision_id",
    )
    if payload.get("symbol") and payload.get("venue"):
        target = sync_target_with_backtest(
            spec_id=spec_id,
            symbol=payload["symbol"],
            venue=payload["venue"],
            result=result,
            decision=decision,
        )
    record_audit_event(
        event_type="backtest.completed",
        entity_type="backtest_run",
        entity_id=result["run_id"],
        payload={
            "spec_id": result["spec_id"],
            "instrument": result["config"].get("instrument"),
            "sharpe": result["sharpe"],
            "total_return_pct": result["total_return_pct"],
            "total_trades": result["total_trades"],
            "promotion_passed": decision["passed"],
            "target_status": target["status"] if target else None,
        },
    )
    return {"result": result, "promotion": decision, "target": target}


@router.post("/compare")
def compare_backtests(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    lookback_days = payload.get("lookback_days", 180)
    return {"comparisons": compare_runs(spec_id, lookback_days)}


@router.post("/sweep")
def sweep_backtests(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    spec_id = payload["spec_id"]
    lookback_days = payload.get("lookback_days", 180)
    return {
        "results": sweep_runs(
            spec_id=spec_id,
            symbol=payload.get("symbol"),
            venue=payload.get("venue"),
            lookback_days=lookback_days,
        )
    }


@router.post("/walk-forward")
def walk_forward_backtest(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return {
        "analysis": walk_forward(
            spec_id=payload["spec_id"],
            symbol=payload.get("symbol"),
            venue=payload.get("venue"),
            lookback_days=payload.get("lookback_days", 180),
            windows=payload.get("windows", 4),
        )
    }


@router.get("/{run_id}/monte-carlo")
def monte_carlo(run_id: str, simulations: int = 500) -> dict:
    return {"run_id": run_id, "analysis": monte_carlo_for_run(run_id, simulations=simulations)}


@router.post("/correlation")
def correlation(payload: dict, user: dict = Depends(require_role("operator"))) -> dict:
    return {
        "analysis": correlation_for_spec(
            spec_id=payload["spec_id"],
            lookback_days=payload.get("lookback_days", 120),
        )
    }


@router.get("/{run_id}")
def get_backtest(run_id: str) -> dict:
    row = fetch_one("SELECT * FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {
        "run_id": row["run_id"],
        "spec_id": row["spec_id"],
        "config": json.loads(row["config_json"]),
        "result": json.loads(row["result_json"]),
        "ran_at": row["ran_at"],
    }


@router.get("/{run_id}/equity")
def get_equity(run_id: str) -> dict:
    row = fetch_one("SELECT result_json FROM backtest_runs WHERE run_id=?", [run_id])
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    result = json.loads(row["result_json"])
    return {"run_id": run_id, "equity_curve": result.get("equity_curve", [])}
