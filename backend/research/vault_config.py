"""AutoResearch vault configuration and shared utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from backend.core.config import settings


@dataclass(frozen=True)
class VaultConfig:
    """Paths and tunables for the research vault."""

    root: Path = field(
        default_factory=lambda: Path(os.getenv("VAULT_ROOT", "./data/vault"))
    )

    # ── sub-directories ──────────────────────────────────────────────
    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def concepts_dir(self) -> Path:
        return self.wiki_dir / "concepts"

    @property
    def summaries_dir(self) -> Path:
        return self.wiki_dir / "summaries"

    @property
    def hypotheses_dir(self) -> Path:
        return self.wiki_dir / "hypotheses"

    @property
    def disputes_dir(self) -> Path:
        return self.wiki_dir / "disputes"

    @property
    def index_path(self) -> Path:
        return self.wiki_dir / "index.md"

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def results_tsv(self) -> Path:
        return self.logs_dir / "results.tsv"

    @property
    def search_db(self) -> Path:
        return self.root / "search.db"

    @property
    def program_md(self) -> Path:
        return self.root / "program.md"

    # ── LLM settings (inherited from main config) ───────────────────
    @property
    def openrouter_api_key(self) -> str:
        return settings.openrouter_api_key

    @property
    def openrouter_model(self) -> str:
        return settings.openrouter_model


vault_cfg = VaultConfig()
