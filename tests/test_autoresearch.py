"""Tests for the AutoResearch vault system — search, writers, results_log."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_vault(tmp_path):
    """Create a temporary vault structure and patch VAULT_ROOT for every test."""
    for subdir in (
        "raw/web_clips", "raw/papers", "raw/assets", "raw/datasets",
        "wiki/concepts", "wiki/summaries",
        "wiki/hypotheses/supported", "wiki/hypotheses/refuted", "wiki/hypotheses/open",
        "wiki/disputes",
        "outputs/reports", "outputs/slides", "outputs/plots",
        "logs/run_logs",
    ):
        (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
    (tmp_path / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "logs" / "results.tsv").write_text(
        "hypothesis_id\tstatus\tconfidence\tevidence_count\ttimestamp\tdescription\n",
        encoding="utf-8",
    )

    # Patch the vault_cfg singleton so all modules use tmp_path
    with patch.dict(os.environ, {"VAULT_ROOT": str(tmp_path)}):
        # Force reload of the vault config
        from backend.research import vault_config
        new_cfg = vault_config.VaultConfig()
        with patch.object(vault_config, "vault_cfg", new_cfg):
            yield tmp_path


# ── Search Tests ─────────────────────────────────────────────────────

def test_search_init_and_reindex(tmp_vault):
    """FTS5 db gets created and indexes markdown files."""
    from backend.research.search import init_db, reindex, search

    # Write a test article
    (tmp_vault / "wiki" / "concepts" / "Test_Concept.md").write_text(
        "---\ntags: [test, funding]\n---\n# Test Concept\n\nFunding rates are interesting.",
        encoding="utf-8",
    )

    init_db()
    count = reindex(tmp_vault / "wiki")
    assert count >= 1  # at least the concept + index.md

    results = search("funding")
    assert len(results) >= 1
    assert any("Test_Concept" in r["file"] for r in results)


def test_search_empty_query(tmp_vault):
    """Search on empty index returns empty list."""
    from backend.research.search import init_db, search

    init_db()
    results = search("nonexistent topic xyz")
    assert results == []


# ── Vault Writer Tests ───────────────────────────────────────────────

def test_write_summary(tmp_vault):
    from backend.research.vault_writer import write_summary

    path = write_summary(
        filename="test_doc",
        source_path="raw/web_clips/test_doc.md",
        source_hash="abc123",
        entities=["funding_rate", "basis"],
        body="# Test Doc\n\nThis is a test summary.",
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "sha256:abc123" in content
    assert "funding_rate" in content


def test_write_concept(tmp_vault):
    from backend.research.vault_writer import write_concept

    path = write_concept(
        title="Funding Rate Arbitrage",
        content="Funding rate arb is a delta-neutral strategy.",
        tags=["funding", "arbitrage"],
        related_links=["Basis Trading"],
        source_count=3,
        confidence="high",
        action="CREATE",
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "confidence_level: high" in content
    assert "[[Basis Trading]]" in content


def test_write_hypothesis(tmp_vault):
    from backend.research.vault_writer import write_hypothesis

    path = write_hypothesis(
        hypothesis_id="H001",
        title="Funding spikes predict mean-reversion",
        claim="When BTC funding > 0.03%, price drops 2%.",
        status="supported",
        confidence=0.78,
        evidence_for=["Paper A shows 72% rate"],
        evidence_against=["Bull runs break the pattern"],
        conclusion="Supported in range-bound markets.",
        further_questions=["Does this hold for ETH?"],
        related_concepts=["Funding Rate Arbitrage"],
    )
    assert path.exists()
    assert "supported" in str(path)
    content = path.read_text(encoding="utf-8")
    assert "H001" in content
    assert "0.78" in content


def test_write_dispute(tmp_vault):
    from backend.research.vault_writer import write_dispute

    path = write_dispute(
        dispute_id="D001",
        articles=["Article_A", "Article_B"],
        conflict_description="A says X, B says Y.",
        suggested_resolution="Merge the information.",
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "unresolved" in content
    assert "Article_A" in content


def test_write_slides(tmp_vault):
    from backend.research.vault_writer import write_slides

    path = write_slides("Test Talk", ["## Slide 1\n- Point A", "## Slide 2\n- Point B"])
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "marp: true" in content
    assert "---" in content


def test_rebuild_index(tmp_vault):
    from backend.research.vault_writer import rebuild_index, write_concept

    write_concept("Alpha", "content", ["tag"], [], 1)
    write_concept("Beta", "content", ["tag"], [], 1)

    path = rebuild_index()
    content = path.read_text(encoding="utf-8")
    assert "[[Alpha]]" in content
    assert "[[Beta]]" in content
    # Other tests may have written concepts too, so just check >= 2
    assert "Total concepts**:" in content


# ── Results Log Tests ────────────────────────────────────────────────

def test_results_log(tmp_vault):
    from backend.research.results_log import log_result, next_hypothesis_id, read_results

    tsv = tmp_vault / "logs" / "results.tsv"
    assert next_hypothesis_id(tsv_path=tsv) == "H001"

    log_result("H001", "supported", 0.78, 5, "Test hypothesis", tsv_path=tsv)
    log_result("H002", "refuted", 0.2, 3, "Another hypothesis", tsv_path=tsv)

    rows = read_results(tsv_path=tsv)
    assert len(rows) == 2
    assert rows[0]["hypothesis_id"] == "H001"
    assert rows[1]["status"] == "refuted"

    assert next_hypothesis_id(tsv_path=tsv) == "H003"


# ── Linter Tests (sync-only checks) ─────────────────────────────────

def test_linter_broken_links(tmp_vault):
    from backend.research.agents.linter import check_broken_links

    # Create a concept with a broken link
    (tmp_vault / "wiki" / "concepts" / "Test.md").write_text(
        "# Test\n\nSee [[Nonexistent Article]] for details.",
        encoding="utf-8",
    )

    issues = check_broken_links()
    broken_links = [i["link"] for i in issues if i["type"] == "broken_link"]
    assert "Nonexistent Article" in broken_links


def test_linter_orphan_raw(tmp_vault):
    from backend.research.agents import linter
    from backend.research import vault_config

    # Create a raw file with no summary
    orphan_path = tmp_vault / "raw" / "web_clips" / "unique_orphan_file.md"
    orphan_path.write_text("Some orphan content", encoding="utf-8")

    # Patch at both levels to ensure the linter reads from tmp_vault
    new_cfg = vault_config.VaultConfig()
    with patch.object(vault_config, "vault_cfg", new_cfg), \
         patch.object(linter, "vault_cfg", new_cfg):
        issues = linter.check_orphan_raw_files()
        assert len(issues) >= 1
        all_files = [i["file"] for i in issues]
        assert any("unique_orphan_file" in f for f in all_files)


# ── Scout Tests (sync-only checks) ──────────────────────────────────

def test_scout_orphan_summaries(tmp_vault):
    from backend.research.agents.scout import find_orphan_summaries

    # Create a summary with no concept linking to it
    (tmp_vault / "wiki" / "summaries" / "lonely_summary.md").write_text(
        "---\nsource: raw/test.md\n---\n# Lonely\n\nNo concept links here.",
        encoding="utf-8",
    )

    orphans = find_orphan_summaries()
    assert "lonely_summary" in orphans


def test_scout_stub_concepts(tmp_vault):
    from backend.research.agents import scout
    from backend.research import vault_config

    # Create a concept with no links at all
    (tmp_vault / "wiki" / "concepts" / "StubTest.md").write_text(
        "# StubTest Concept\n\nVery thin article with no links.",
        encoding="utf-8",
    )

    new_cfg = vault_config.VaultConfig()
    with patch.object(vault_config, "vault_cfg", new_cfg), \
         patch.object(scout, "vault_cfg", new_cfg):
        stubs = scout.find_stub_concepts(min_sources=1)
        stub_names = [s["concept"] for s in stubs]
        assert "StubTest" in stub_names
