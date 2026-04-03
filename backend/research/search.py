"""SQLite FTS5 full-text search over the wiki vault.

Usage:
    python -m backend.research.search "funding rate"
    python -m backend.research.search --reindex
"""
from __future__ import annotations

import glob
import hashlib
import os
import sqlite3
from pathlib import Path

import structlog

from backend.research.vault_config import vault_cfg

log = structlog.get_logger()


def _db_path() -> str:
    return str(vault_cfg.search_db)


def _file_hash(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def init_db() -> None:
    """Create FTS5 virtual table and hash tracker if they don't exist."""
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(
            filepath,
            title,
            content,
            tags,
            tokenize='porter unicode61'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_hashes (
            filepath TEXT PRIMARY KEY,
            hash     TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def reindex(wiki_path: Path | None = None) -> int:
    """Rebuild the search index.  Returns count of files indexed."""
    wiki_path = wiki_path or vault_cfg.wiki_dir
    init_db()
    conn = sqlite3.connect(_db_path())
    existing: dict[str, str] = dict(
        conn.execute("SELECT filepath, hash FROM file_hashes").fetchall()
    )
    indexed = 0
    pattern = os.path.join(str(wiki_path), "**", "*.md")
    for filepath in glob.glob(pattern, recursive=True):
        current_hash = _file_hash(filepath)
        if existing.get(filepath) == current_hash:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title from first H1
        title = ""
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract tags from YAML frontmatter
        tags = ""
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                for line in content[3:fm_end].split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("tags:"):
                        tags = stripped.split(":", 1)[1].strip()

        # Upsert into FTS
        conn.execute("DELETE FROM wiki_fts WHERE filepath = ?", (filepath,))
        conn.execute(
            "INSERT INTO wiki_fts (filepath, title, content, tags) VALUES (?, ?, ?, ?)",
            (filepath, title, content, tags),
        )
        conn.execute(
            "INSERT OR REPLACE INTO file_hashes (filepath, hash) VALUES (?, ?)",
            (filepath, current_hash),
        )
        indexed += 1

    # Remove entries for deleted files
    current_files = set(glob.glob(pattern, recursive=True))
    for old_path in set(existing.keys()) - current_files:
        conn.execute("DELETE FROM wiki_fts WHERE filepath = ?", (old_path,))
        conn.execute("DELETE FROM file_hashes WHERE filepath = ?", (old_path,))

    conn.commit()
    conn.close()
    log.info("search reindex complete", indexed=indexed)
    return indexed


def search(query: str, *, limit: int = 10) -> list[dict]:
    """BM25-ranked full-text search.  Returns list of hit dicts."""
    init_db()
    conn = sqlite3.connect(_db_path())
    try:
        rows = conn.execute(
            """
            SELECT filepath,
                   title,
                   snippet(wiki_fts, 2, '>>>', '<<<', '...', 40),
                   rank
            FROM   wiki_fts
            WHERE  wiki_fts MATCH ?
            ORDER  BY rank
            LIMIT  ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        # Empty index or bad query syntax
        rows = []
    conn.close()
    return [
        {"file": r[0], "title": r[1], "snippet": r[2], "score": r[3]}
        for r in rows
    ]


def read_file(filepath: str) -> str:
    """Read an arbitrary file from the vault (helper for agents)."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# ── CLI entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m backend.research.search <query>")
        print("       python -m backend.research.search --reindex")
        sys.exit(1)

    if sys.argv[1] == "--reindex":
        init_db()
        count = reindex()
        print(f"Indexed {count} files.")
    else:
        q = " ".join(sys.argv[1:])
        hits = search(q)
        if not hits:
            print("No results.")
        for h in hits:
            print(f"[{h['score']:.2f}] {h['title']}")
            print(f"  {h['file']}")
            print(f"  {h['snippet']}\n")
