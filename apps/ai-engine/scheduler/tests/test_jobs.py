"""Tests for the :mod:`scheduler.jobs` factories.

Each factory should:
- Return a :class:`Job` carrying its own id/name/interval/metadata.
- Accept dependency injection (``func=...``) without instantiating
  any engine itself.
- Convert minutes/hours -> seconds correctly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from scheduler.jobs import (
    Job,
    confluence_sync_job,
    default_jobs,
    doc_reconciliation_job,
    signoz_sync_job,
    staleness_lint_job,
)


# --------------------------------------------------------------------------- #
# Individual factories
# --------------------------------------------------------------------------- #


def test_confluence_sync_job_default_interval() -> None:
    func = AsyncMock(return_value={"pages_ingested": 0})
    job = confluence_sync_job(func=func)
    assert isinstance(job, Job)
    assert job.id == "confluence_sync"
    assert job.interval_seconds == 60 * 60  # 60 minutes default
    assert job.func is func
    assert job.enabled is True
    assert job.metadata["connector"] == "confluence"


def test_confluence_sync_job_custom_interval() -> None:
    func = AsyncMock()
    job = confluence_sync_job(func=func, interval_minutes=5)
    assert job.interval_seconds == 5 * 60
    assert job.interval_minutes == 5.0


def test_signoz_sync_job_records_lookback() -> None:
    func = AsyncMock()
    job = signoz_sync_job(func=func, interval_minutes=10, lookback_minutes=120)
    assert job.id == "signoz_sync"
    assert job.interval_seconds == 600
    assert job.metadata["lookback_minutes"] == 120
    assert job.metadata["connector"] == "signoz"


def test_staleness_lint_job_uses_hours() -> None:
    func = AsyncMock()
    job = staleness_lint_job(func=func, interval_hours=2)
    assert job.id == "staleness_lint"
    assert job.interval_seconds == 7200
    assert job.metadata["connector"] == "staleness_linter"


def test_doc_reconciliation_job_default_topics() -> None:
    func = AsyncMock()
    job = doc_reconciliation_job(func=func)
    assert job.id == "doc_reconciliation"
    assert job.metadata["topics"] == ["all"]
    assert job.interval_seconds == 12 * 3600


def test_doc_reconciliation_job_custom_topics() -> None:
    func = AsyncMock()
    job = doc_reconciliation_job(
        func=func,
        interval_hours=6,
        topics=["postgres", "kafka"],
    )
    assert job.metadata["topics"] == ["postgres", "kafka"]
    assert job.interval_seconds == 6 * 3600


# --------------------------------------------------------------------------- #
# Dependency injection
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_factory_func_is_called_via_runner() -> None:
    """The injected callable must be the one actually awaited."""
    func = AsyncMock(return_value={"pages_ingested": 7})
    job = confluence_sync_job(func=func)
    result: Any = await job.func()
    assert result == {"pages_ingested": 7}
    func.assert_awaited_once_with()


def test_disabled_flag_propagates() -> None:
    func = AsyncMock()
    job = staleness_lint_job(func=func, enabled=False)
    assert job.enabled is False


# --------------------------------------------------------------------------- #
# default_jobs
# --------------------------------------------------------------------------- #


def test_default_jobs_returns_four_jobs_disabled_when_deps_missing() -> None:
    jobs = default_jobs(deps={})
    assert [j.id for j in jobs] == [
        "confluence_sync",
        "signoz_sync",
        "staleness_lint",
        "doc_reconciliation",
    ]
    assert all(not j.enabled for j in jobs)


def test_default_jobs_enables_jobs_when_deps_provided() -> None:
    deps = {
        "confluence_sync": AsyncMock(),
        "signoz_sync": AsyncMock(),
        "staleness_lint": AsyncMock(),
        "doc_reconciliation": AsyncMock(),
        "reconciliation_topics": ["postgres"],
    }
    jobs = default_jobs(deps=deps)
    by_id = {j.id: j for j in jobs}
    assert by_id["confluence_sync"].enabled is True
    assert by_id["signoz_sync"].enabled is True
    assert by_id["staleness_lint"].enabled is True
    assert by_id["doc_reconciliation"].enabled is True
    assert by_id["doc_reconciliation"].metadata["topics"] == ["postgres"]
