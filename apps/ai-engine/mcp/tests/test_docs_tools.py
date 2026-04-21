"""Integration tests for the Layer 5 ``docs_*`` MCP tools.

These verify:

1. Each tool registers into the manifest under scope="read".
2. None of the tools appear in the "write" scope.
3. The tools produce JSON-serialisable dicts (never raw pydantic models).
4. External HTTP calls in ``check_doc_links`` are mocked via respx so
   tests never touch the network.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

# Importing the read package triggers decorator registration.
import mcp.tools.read  # noqa: F401
from mcp.manifest import manifest as shared_manifest
from mcp.scope_config import MCPScopeConfig
from mcp.tools.read import _docs_runtime as docs_runtime
from reconciliation.models import Doc
from reconciliation.reconciler import Reconciler
from reconciliation.sources import DocSource


# ---- Tiny in-memory source -------------------------------------------- #


class InMemSource(DocSource):
    def __init__(self, name: str, docs: list[Doc]):
        self.name = name  # type: ignore[assignment]
        self._docs = {d.id: d for d in docs}

    def list(self):
        return list(self._docs.keys())

    def fetch(self, doc_id):
        return self._docs.get(doc_id)


@pytest.fixture(autouse=True)
def reset_reconciler():
    docs_runtime.reset()
    yield
    docs_runtime.reset()


@pytest.fixture
def seeded_reconciler():
    now = datetime.now(timezone.utc)
    obs = InMemSource(
        "obsidian",
        [
            Doc(
                id="runbooks/db.md",
                source="obsidian",
                title="Database Runbook",
                body=(
                    "# Database\nRun postgres 16 pool=50.\n"
                    "See [docs](https://postgres.example.com)."
                ),
                last_modified=now - timedelta(days=5),
                tags=["db"],
            )
        ],
    )
    conf = InMemSource(
        "confluence",
        [
            Doc(
                id="100",
                source="confluence",
                title="Database Runbook",
                body="Run postgres 13 pool=20. DEPRECATED.",
                last_modified=now - timedelta(days=900),
                tags=["db"],
            )
        ],
    )
    r = Reconciler(sources=[obs, conf], llm_router=None)
    docs_runtime.set_reconciler(r)
    return r


# ---- Manifest registration -------------------------------------------- #


def test_all_four_docs_tools_register_as_read():
    config = MCPScopeConfig()
    read_names = {t.name for t in shared_manifest.load_scope("read", config)}
    assert "find_docs" in read_names
    assert "reconcile_docs" in read_names
    assert "detect_stale_docs" in read_names
    assert "check_doc_links" in read_names


def test_no_docs_tool_leaks_into_write_scope():
    config = MCPScopeConfig(load_write=True)
    write_names = {t.name for t in shared_manifest.load_scope("write", config)}
    for tool_name in ("find_docs", "reconcile_docs", "detect_stale_docs", "check_doc_links"):
        assert tool_name not in write_names


def test_docs_tools_never_in_blocked():
    assert shared_manifest.load_scope("blocked", MCPScopeConfig()) == []
    blocked_names = {t.name for t in shared_manifest.get_blocked()}
    for tool_name in ("find_docs", "reconcile_docs", "detect_stale_docs", "check_doc_links"):
        assert tool_name not in blocked_names


# ---- find_docs -------------------------------------------------------- #


def test_find_docs_returns_json_dict(seeded_reconciler):
    from mcp.tools.read.docs_find import find_docs

    result = find_docs("postgres")
    # Must be JSON-serialisable.
    json.dumps(result)
    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["docs"][0]["source"] in ("obsidian", "confluence")
    # Fresh Obsidian doc should be ranked above stale Confluence.
    assert result["docs"][0]["source"] == "obsidian"


def test_find_docs_source_filter(seeded_reconciler):
    from mcp.tools.read.docs_find import find_docs

    result = find_docs("postgres", sources=["confluence"])
    assert result["count"] == 1
    assert result["docs"][0]["source"] == "confluence"


# ---- reconcile_docs --------------------------------------------------- #


def test_reconcile_docs_detects_version_mismatch(seeded_reconciler):
    from mcp.tools.read.docs_reconcile import reconcile_docs

    result = reconcile_docs("postgres")
    json.dumps(result)
    report = result["report"]
    assert report["topic"] == "postgres"
    categories = {c["category"] for c in report["contradictions"]}
    assert "version_mismatch" in categories


# ---- detect_stale_docs ------------------------------------------------ #


def test_detect_stale_docs_flags_old_confluence(seeded_reconciler):
    from mcp.tools.read.docs_staleness import detect_stale_docs

    result = detect_stale_docs("confluence", threshold_days=180)
    json.dumps(result)
    assert result["count"] == 1
    assert result["stale_docs"][0]["doc_id"] == "100"
    assert result["stale_docs"][0]["staleness"]["age_days"] > 180


def test_detect_stale_docs_unknown_source_returns_error(seeded_reconciler):
    from mcp.tools.read.docs_staleness import detect_stale_docs

    result = detect_stale_docs("does-not-exist")
    assert result["status"] == "error"
    assert "available_sources" in result


# ---- check_doc_links -------------------------------------------------- #


@respx.mock
def test_check_doc_links_probes_external_urls(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    # Allow robots.txt fetch + HEAD probe. respx blocks real net by default.
    respx.get("https://postgres.example.com/robots.txt").mock(
        return_value=httpx.Response(404)
    )
    respx.head("https://postgres.example.com").mock(
        return_value=httpx.Response(200)
    )

    result = check_doc_links("obsidian:runbooks/db.md")
    json.dumps(result)
    assert result["status"] == "success"
    external = [
        c for c in result["report"]["checked"] if c["url"].startswith("https://")
    ]
    assert external
    assert external[0]["status"] == "ok"


@respx.mock
def test_check_doc_links_marks_broken_urls(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    respx.get("https://postgres.example.com/robots.txt").mock(
        return_value=httpx.Response(404)
    )
    respx.head("https://postgres.example.com").mock(
        return_value=httpx.Response(500)
    )

    result = check_doc_links("obsidian:runbooks/db.md")
    assert result["broken_count"] >= 1


@respx.mock
def test_check_doc_links_respects_robots_txt(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    # Disallow everything.
    respx.get("https://postgres.example.com/robots.txt").mock(
        return_value=httpx.Response(
            200,
            text="User-agent: *\nDisallow: /\n",
        )
    )

    result = check_doc_links("obsidian:runbooks/db.md")
    statuses = [c["status"] for c in result["report"]["checked"]]
    assert "skipped_robots" in statuses


def test_check_doc_links_malformed_doc_id(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    result = check_doc_links("no-colon-here")
    assert result["status"] == "error"


def test_check_doc_links_unknown_source(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    result = check_doc_links("notion:whatever")
    assert result["status"] == "error"
    assert "available_sources" in result


def test_check_doc_links_missing_doc(seeded_reconciler):
    from mcp.tools.read.docs_link_check import check_doc_links

    result = check_doc_links("obsidian:missing.md")
    assert result["status"] == "error"
