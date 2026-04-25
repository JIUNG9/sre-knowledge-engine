"""FastAPI router for the Aegis scheduler (Phase 2.4).

Exposes four endpoints under ``/api/v1/scheduler``:

* ``GET  /api/v1/scheduler/jobs`` — list jobs + last run + next run
* ``POST /api/v1/scheduler/jobs/{id}/run`` — fire immediately
* ``POST /api/v1/scheduler/jobs/{id}/pause`` — pause future ticks
* ``POST /api/v1/scheduler/jobs/{id}/resume`` — resume paused job
* ``GET  /api/v1/scheduler/history`` — recent run records

Like the Control Tower router, the endpoints depend on a
``get_scheduler`` dependency that returns 503 by default and is
overridden by ``main.py`` once a real :class:`Scheduler` is attached
to ``app.state``. This keeps router import side-effect-free.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .scheduler import Scheduler

scheduler_router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #


class JobView(BaseModel):
    """One job entry in ``GET /api/v1/scheduler/jobs``."""

    id: str
    name: str
    enabled: bool
    interval_seconds: int
    next_run: str | None = None
    last_run: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HistoryView(BaseModel):
    """Run-history row in ``GET /api/v1/scheduler/history``."""

    job_id: str
    started_at: str
    finished_at: str | None
    duration_ms: float | None
    outcome: str
    error: str | None
    detail: dict[str, Any]


class RunView(BaseModel):
    """Body returned by ``POST /api/v1/scheduler/jobs/{id}/run``."""

    job_id: str
    outcome: str
    started_at: str
    finished_at: str | None
    duration_ms: float | None
    error: str | None
    detail: dict[str, Any]


class ControlResult(BaseModel):
    """Body returned by pause / resume."""

    job_id: str
    action: str
    success: bool


# --------------------------------------------------------------------------- #
# Dependency
# --------------------------------------------------------------------------- #


def get_scheduler() -> Scheduler:
    """Return the active :class:`Scheduler`.

    Default implementation raises 503 so importing the router never
    forces the scheduler to start. ``main.py`` overrides this in the
    lifespan hook with ``app.dependency_overrides``.
    """
    raise HTTPException(
        status_code=503,
        detail=(
            "scheduler not configured; set AEGIS_SCHEDULER_ENABLED=1 "
            "and override `get_scheduler` in the FastAPI app"
        ),
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@scheduler_router.get(
    "/jobs",
    response_model=list[JobView],
    summary="List scheduled jobs",
)
def list_jobs(scheduler: Scheduler = Depends(get_scheduler)) -> list[JobView]:
    """Return every registered job + its last/next run timestamps."""
    return [JobView(**row) for row in scheduler.list_jobs()]


@scheduler_router.post(
    "/jobs/{job_id}/run",
    response_model=RunView,
    summary="Run a job immediately",
)
async def run_job(
    job_id: str,
    scheduler: Scheduler = Depends(get_scheduler),
) -> RunView:
    """Fire ``job_id`` once, off-schedule, and return the run record."""
    record = await scheduler.run_now(job_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"job {job_id!r} not found"
        )
    return RunView(**record)


@scheduler_router.post(
    "/jobs/{job_id}/pause",
    response_model=ControlResult,
    summary="Pause a job",
)
def pause_job(
    job_id: str,
    scheduler: Scheduler = Depends(get_scheduler),
) -> ControlResult:
    """Pause future ticks of ``job_id`` until ``resume`` is called."""
    if scheduler.get_job(job_id) is None:
        raise HTTPException(
            status_code=404, detail=f"job {job_id!r} not found"
        )
    success = scheduler.pause_job(job_id)
    return ControlResult(job_id=job_id, action="pause", success=success)


@scheduler_router.post(
    "/jobs/{job_id}/resume",
    response_model=ControlResult,
    summary="Resume a paused job",
)
def resume_job(
    job_id: str,
    scheduler: Scheduler = Depends(get_scheduler),
) -> ControlResult:
    """Resume ``job_id`` after a prior pause."""
    if scheduler.get_job(job_id) is None:
        raise HTTPException(
            status_code=404, detail=f"job {job_id!r} not found"
        )
    success = scheduler.resume_job(job_id)
    return ControlResult(job_id=job_id, action="resume", success=success)


@scheduler_router.get(
    "/history",
    response_model=list[HistoryView],
    summary="Recent job run history",
)
def list_history(
    scheduler: Scheduler = Depends(get_scheduler),
    job_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[HistoryView]:
    """Return recent :class:`JobRunRecord` entries (newest first)."""
    rows = scheduler.history.list(job_id=job_id, limit=limit)
    return [HistoryView(**row.to_dict()) for row in rows]
