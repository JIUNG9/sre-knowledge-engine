"""Shared pytest fixtures for the reconciliation test suite."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

# Ensure `from reconciliation.x import ...` and `from mcp.x import ...` work.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create an Obsidian-shaped vault with a few fixture files."""
    now = datetime(2026, 4, 21, tzinfo=timezone.utc)
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "_meta").mkdir()
    (tmp_path / "_archive").mkdir()

    fresh = tmp_path / "runbooks" / "db.md"
    fresh.write_text(
        """---
title: "Database Runbook"
tags: [db, runbook]
last_updated: "2026-04-01T00:00:00+00:00"
---
# DB Runbook

Run postgres 16 with connection pool size 50.
""",
        encoding="utf-8",
    )

    stale = tmp_path / "runbooks" / "old-db.md"
    stale.write_text(
        """---
title: "Old Database Runbook"
tags: [db]
last_updated: "2022-01-01T00:00:00+00:00"
---
# DB Runbook (legacy)

Run postgres 13 with connection pool size 20. This is DEPRECATED.
It still mentions CentOS 7. Note this was written in 2022.
See [docs](https://example.com/db).
""",
        encoding="utf-8",
    )

    archived = tmp_path / "_archive" / "skip-me.md"
    archived.write_text("archived — must be skipped", encoding="utf-8")

    meta = tmp_path / "_meta" / "ignore.md"
    meta.write_text("meta — must be skipped", encoding="utf-8")

    return tmp_path


@pytest.fixture
def tmp_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "Home.md").write_text("# Home\nSee [[db]].", encoding="utf-8")
    (wiki / "Db.md").write_text(
        "# Database\nPostgres 16. See https://postgres.example.com.",
        encoding="utf-8",
    )
    return wiki


@pytest.fixture
def confluence_pages() -> list[dict[str, Any]]:
    return [
        {
            "id": "100",
            "title": "Database Runbook",
            "body": {"storage": {"value": "Run postgres 13 pool=20"}},
            "version": {"createdAt": "2023-01-15T00:00:00Z"},
            "metadata": {"labels": [{"name": "db"}, {"name": "runbook"}]},
            "spaceId": "ENG",
        },
        {
            "id": "200",
            "title": "Network Runbook",
            "body": {"storage": {"value": "Run istio 1.12"}},
            "version": {"createdAt": "2026-04-10T00:00:00Z"},
            "metadata": {"labels": []},
            "spaceId": "ENG",
        },
    ]


@pytest.fixture
def slack_pins() -> list[dict[str, Any]]:
    return [
        {
            "id": "P1",
            "channel": "C123",
            "user": "U1",
            "text": "Reminder: db runbook says postgres 16, pool=50",
            "pinned_at": "2026-04-20T00:00:00Z",
            "permalink": "https://slack.example.com/archives/C123/p1",
            "title": "DB reminder",
        }
    ]


@pytest.fixture
def contradicting_docs(tmp_path: Path) -> list[Any]:
    """Two Docs with deliberate contradictions — versions + procedures."""
    from reconciliation.models import Doc

    now = datetime.now(timezone.utc)
    return [
        Doc(
            id="runbooks/db.md",
            source="obsidian",
            title="Database Runbook",
            body=(
                "Use postgres 16 with pool size 50. When a pod is OOM, "
                "scale the deployment to 0 and wait 30 seconds."
            ),
            last_modified=now - timedelta(days=10),
            tags=["db"],
        ),
        Doc(
            id="100",
            source="confluence",
            title="Database Runbook",
            body=(
                "Use postgres 13 with pool size 20. When a pod is OOM, "
                "restart the deployment. Do NOT scale to 0."
            ),
            last_modified=now - timedelta(days=720),
            tags=["db"],
        ),
    ]
