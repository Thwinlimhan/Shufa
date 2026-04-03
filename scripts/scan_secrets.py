from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", ".venv", ".pytest_cache", ".npm-cache", "node_modules", "data"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".parquet", ".duckdb", ".db", ".wal", ".shm", ".lock"}

PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|passphrase)\s*=\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
]


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for pattern in PATTERNS:
            for match in pattern.finditer(text):
                snippet = match.group(0)
                findings.append(f"{path.relative_to(ROOT)} :: {snippet[:90]}")
    if findings:
        print("Potential secrets detected:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
