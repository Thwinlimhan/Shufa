from __future__ import annotations

import json

from backend.core.types import StrategySpec, dataclass_to_dict, strategy_spec_from_dict
from backend.data.storage import fetch_all, fetch_one, save_json_record
from backend.strategy.signals import funding_reversion, momentum, vol_regime
from backend.strategy.targets import strategy_status_summary


BUILTIN_BUILDERS = (
    funding_reversion.build,
    momentum.build,
    vol_regime.build,
)


def bootstrap_builtin_specs() -> None:
    for builder in BUILTIN_BUILDERS:
        spec = builder()
        row = fetch_one("SELECT spec_id FROM strategy_specs WHERE spec_id=?", [spec.spec_id])
        if row is None:
            save_json_record(
                "strategy_specs",
                {
                    "spec_id": spec.spec_id,
                    "name": spec.name,
                    "version": spec.version,
                    "parent_id": spec.parent_id,
                    "status": "proposed",
                    "spec_json": json.dumps(dataclass_to_dict(spec)),
                    "created_at": spec.created_at.isoformat(),
                },
                "spec_id",
            )


def list_specs() -> list[dict]:
    bootstrap_builtin_specs()
    rows = fetch_all("SELECT spec_id, name, version, parent_id, status, created_at, spec_json FROM strategy_specs ORDER BY created_at DESC")
    results = []
    for row in rows:
        target_summary = strategy_status_summary(row["spec_id"])
        results.append(
            {
            "spec_id": row["spec_id"],
            "name": row["name"],
            "version": row["version"],
            "parent_id": row["parent_id"],
            "status": target_summary["status"],
            "created_at": row["created_at"],
            "spec": json.loads(row["spec_json"]),
            "paper_enabled_count": target_summary["paper_enabled_count"],
            "targets": target_summary["targets"],
        }
        )
    return results


def load_spec(spec_id: str) -> StrategySpec | None:
    row = fetch_one("SELECT spec_json FROM strategy_specs WHERE spec_id=?", [spec_id])
    if row is None:
        return None
    return strategy_spec_from_dict(json.loads(row["spec_json"]))
