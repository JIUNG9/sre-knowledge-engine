"""Tests for reconciliation source adapters."""

from __future__ import annotations

from pathlib import Path


from reconciliation.sources import (
    ConfluenceSource,
    GitHubWikiSource,
    ObsidianSource,
    SlackPinSource,
    extract_links,
)


# --- ObsidianSource -------------------------------------------------------- #


def test_obsidian_lists_only_tracked_files(tmp_vault: Path):
    src = ObsidianSource(tmp_vault)
    listed = src.list()
    # _archive and _meta must be skipped.
    assert all("_archive" not in p and "_meta" not in p for p in listed)
    assert "runbooks/db.md" in listed
    assert "runbooks/old-db.md" in listed


def test_obsidian_fetch_parses_frontmatter(tmp_vault: Path):
    src = ObsidianSource(tmp_vault)
    doc = src.fetch("runbooks/db.md")
    assert doc is not None
    assert doc.title == "Database Runbook"
    assert "postgres 16" in doc.body
    assert "db" in doc.tags
    assert doc.last_modified is not None
    assert doc.last_modified.year == 2026


def test_obsidian_fetch_missing_returns_none(tmp_vault: Path):
    assert ObsidianSource(tmp_vault).fetch("does-not-exist.md") is None


def test_obsidian_search_is_case_insensitive(tmp_vault: Path):
    src = ObsidianSource(tmp_vault)
    results = src.search("POSTGRES")
    assert len(results) >= 1
    assert any("postgres" in r.body.lower() for r in results)


def test_obsidian_score_freshness_ranks_newer_higher(tmp_vault: Path):
    src = ObsidianSource(tmp_vault)
    fresh = src.score_freshness("runbooks/db.md")
    stale = src.score_freshness("runbooks/old-db.md")
    assert fresh > stale


# --- ConfluenceSource ------------------------------------------------------ #


def test_confluence_roundtrip(confluence_pages):
    src = ConfluenceSource(confluence_pages)
    assert set(src.list()) == {"100", "200"}
    doc = src.fetch("100")
    assert doc is not None
    assert doc.source == "confluence"
    assert doc.title == "Database Runbook"
    assert "postgres 13" in doc.body
    assert "db" in doc.tags


def test_confluence_load_from_sync_appends(confluence_pages):
    src = ConfluenceSource()
    assert src.list() == []
    src.load_from_sync(confluence_pages)
    assert len(src.list()) == 2


def test_confluence_last_modified_parsed(confluence_pages):
    src = ConfluenceSource(confluence_pages)
    doc = src.fetch("100")
    assert doc is not None
    assert doc.last_modified is not None
    assert doc.last_modified.year == 2023


# --- GitHubWikiSource ------------------------------------------------------ #


def test_github_wiki_lists_markdown(tmp_wiki: Path):
    src = GitHubWikiSource(tmp_wiki, repo_url="https://github.com/aegis/aegis")
    files = src.list()
    assert set(files) == {"Home.md", "Db.md"}


def test_github_wiki_fetch_builds_url(tmp_wiki: Path):
    src = GitHubWikiSource(tmp_wiki, repo_url="https://github.com/aegis/aegis")
    doc = src.fetch("Db.md")
    assert doc is not None
    assert doc.url == "https://github.com/aegis/aegis/wiki/Db"
    assert "Postgres 16" in doc.body


def test_github_wiki_missing_root_returns_empty(tmp_path: Path):
    src = GitHubWikiSource(tmp_path / "does-not-exist")
    assert src.list() == []


# --- SlackPinSource -------------------------------------------------------- #


def test_slack_pin_stub_honours_seeded_data(slack_pins):
    src = SlackPinSource(slack_pins)
    assert src.list() == ["P1"]
    doc = src.fetch("P1")
    assert doc is not None
    assert doc.source == "slack_pin"
    assert "postgres 16" in doc.body.lower()


def test_slack_pin_empty_stub():
    src = SlackPinSource()
    assert src.list() == []
    assert src.fetch("anything") is None


# --- Link extraction ------------------------------------------------------- #


def test_extract_links_separates_internal_and_external():
    body = """
    See [[Database Runbook]] and [Postgres docs](https://postgres.example.com).
    Also [broken](/relative/path).
    [[Nested|Alias]] link.
    """
    internal, external = extract_links(body)
    assert "Database Runbook" in internal
    assert "Nested" in internal
    assert "/relative/path" in internal
    assert external == ["https://postgres.example.com"]


def test_extract_links_empty_body_returns_empty():
    assert extract_links("") == ([], [])


def test_extract_links_dedupes():
    body = "[one](https://a.com) [again](https://a.com) [[Same]] [[Same]]"
    internal, external = extract_links(body)
    assert external == ["https://a.com"]
    assert internal == ["Same"]
