"""Tests for :mod:`scheduler.api` — the FastAPI router.

Uses Starlette's :class:`TestClient` over a minimal FastAPI app that
mounts the scheduler router and overrides ``get_scheduler`` with a
prebuilt :class:`Scheduler`. The scheduler is never actually started
(APScheduler unused) so the tests are deterministic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from scheduler.api import get_scheduler, scheduler_router
from scheduler.config import SchedulerConfig
from scheduler.history import JobHistory, JobRunRecord
from scheduler.jobs import Job
from scheduler.scheduler import Scheduler


def _make_app(scheduler: Scheduler) -> FastAPI:
    app = FastAPI()
    app.include_router(scheduler_router)
    app.dependency_overrides[get_scheduler] = lambda: scheduler
    return app


def _make_scheduler() -> Scheduler:
    history = JobHistory()
    scheduler = Scheduler(
        config=SchedulerConfig(enabled=False),
        history=history,
    )
    scheduler.add_job(
        Job(
            id="confluence_sync",
            name="Confluence sync",
            interval_seconds=3600,
            func=AsyncMock(return_value={"pages_ingested": 12}),
            metadata={"connector": "confluence"},
        )
    )
    scheduler.add_job(
        Job(
            id="signoz_sync",
            name="SigNoz sync",
            interval_seconds=900,
            func=AsyncMock(return_value={"incidents_ingested": 0}),
            metadata={"connector": "signoz"},
        )
    )
    return scheduler


# --------------------------------------------------------------------------- #
# GET /jobs
# --------------------------------------------------------------------------- #


def test_list_jobs_returns_registered_jobs() -> None:
    scheduler = _make_scheduler()
    app = _make_app(scheduler)

    with TestClient(app) as client:
        resp = client.get("/api/v1/scheduler/jobs")

    assert resp.status_code == 200
    body = resp.json()
    assert {row["id"] for row in body} == {"confluence_sync", "signoz_sync"}
    confluence = next(r for r in body if r["id"] == "confluence_sync")
    assert confluence["interval_seconds"] == 3600
    assert confluence["metadata"]["connector"] == "confluence"


def test_list_jobs_returns_503_without_scheduler() -> None:
    """Default ``get_scheduler`` raises 503 when no override is wired."""
    app = FastAPI()
    app.include_router(scheduler_router)
    with TestClient(app) as client:
        resp = client.get("/api/v1/scheduler/jobs")
    assert resp.status_code == 503


# --------------------------------------------------------------------------- #
# POST /jobs/{id}/run
# --------------------------------------------------------------------------- #


def test_run_job_executes_immediately() -> None:
    scheduler = _make_scheduler()
    app = _make_app(scheduler)

    with TestClient(app) as client:
        resp = client.post("/api/v1/scheduler/jobs/confluence_sync/run")

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "confluence_sync"
    assert body["outcome"] == "success"
    assert body["detail"]["pages_ingested"] == 12


def test_run_unknown_job_returns_404() -> None:
    scheduler = _make_scheduler()
    app = _make_app(scheduler)

    with TestClient(app) as client:
        resp = client.post("/api/v1/scheduler/jobs/missing/run")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Pause / Resume
# --------------------------------------------------------------------------- #


def test_pause_unknown_job_returns_404() -> None:
    scheduler = _make_scheduler()
    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.post("/api/v1/scheduler/jobs/missing/pause")
    assert resp.status_code == 404


def test_pause_known_job_returns_control_result() -> None:
    """Pause without started APScheduler reports success=False but 200."""
    scheduler = _make_scheduler()
    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.post("/api/v1/scheduler/jobs/confluence_sync/pause")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "confluence_sync"
    assert body["action"] == "pause"
    # Not started, so pause_job returns False — but the route still 200s.
    assert body["success"] is False


def test_resume_known_job_returns_control_result() -> None:
    scheduler = _make_scheduler()
    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.post("/api/v1/scheduler/jobs/confluence_sync/resume")
    assert resp.status_code == 200
    assert resp.json()["action"] == "resume"


# --------------------------------------------------------------------------- #
# GET /history
# --------------------------------------------------------------------------- #


def test_history_returns_recent_runs() -> None:
    scheduler = _make_scheduler()
    # Pre-populate history with a few synthetic records.
    for i in range(3):
        scheduler.history.record(
            JobRunRecord(
                job_id="confluence_sync",
                started_at=f"2026-04-21T00:0{i}:00+00:00",
                finished_at=f"2026-04-21T00:0{i}:01+00:00",
                duration_ms=1000.0,
                outcome="success",
                detail={"pages_ingested": i},
            )
        )

    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/scheduler/history?job_id=confluence_sync&limit=2"
        )

    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    # Newest-first: the i=2 run should lead.
    assert rows[0]["detail"]["pages_ingested"] == 2


def test_history_with_no_filter_returns_all_jobs() -> None:
    scheduler = _make_scheduler()
    scheduler.history.record(
        JobRunRecord(
            job_id="confluence_sync",
            started_at="2026-04-21T00:00:00+00:00",
            outcome="success",
        )
    )
    scheduler.history.record(
        JobRunRecord(
            job_id="signoz_sync",
            started_at="2026-04-21T00:01:00+00:00",
            outcome="failed",
            error="boom",
        )
    )

    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.get("/api/v1/scheduler/history")

    assert resp.status_code == 200
    rows = resp.json()
    job_ids = {r["job_id"] for r in rows}
    assert job_ids == {"confluence_sync", "signoz_sync"}


def test_history_limit_is_clamped_by_pydantic() -> None:
    """``limit`` outside [1, 500] should be a 422."""
    scheduler = _make_scheduler()
    app = _make_app(scheduler)
    with TestClient(app) as client:
        resp = client.get("/api/v1/scheduler/history?limit=0")
    assert resp.status_code == 422
