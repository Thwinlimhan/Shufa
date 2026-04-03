"""TSV experiment logger — every hypothesis attempt gets a row here."""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.research.vault_config import vault_cfg

HEADER = [
    "hypothesis_id",
    "status",
    "confidence",
    "evidence_count",
    "timestamp",
    "description",
]


def _ensure_file(path: Path) -> None:
    os.makedirs(path.parent, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(HEADER)


def log_result(
    hypothesis_id: str,
    status: str,
    confidence: float,
    evidence_count: int,
    description: str,
    *,
    tsv_path: Path | None = None,
) -> None:
    """Append one row to results.tsv."""
    path = tsv_path or vault_cfg.results_tsv
    _ensure_file(path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([hypothesis_id, status, f"{confidence:.2f}", evidence_count, now, description])


def read_results(*, tsv_path: Path | None = None) -> list[dict]:
    """Read all rows from results.tsv as list of dicts."""
    path = tsv_path or vault_cfg.results_tsv
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def next_hypothesis_id(*, tsv_path: Path | None = None) -> str:
    """Return the next sequential hypothesis ID like H001, H002, …"""
    rows = read_results(tsv_path=tsv_path)
    existing_ids = [r["hypothesis_id"] for r in rows if r.get("hypothesis_id", "").startswith("H")]
    if not existing_ids:
        return "H001"
    max_num = max(int(hid[1:]) for hid in existing_ids)
    return f"H{max_num + 1:03d}"
