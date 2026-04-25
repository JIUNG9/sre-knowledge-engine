"""Tests for :mod:`scheduler.scheduler` — the APScheduler facade.

Strategy:
- Unit-test ``add_job`` / ``remove_job`` / ``list_jobs`` / ``run_now``
  without starting the underlying APScheduler — these operate on the
  facade's own state.
- Use a single integration test that actually starts APScheduler with a
  1-second interval and waits for one tick to land in history. We rely
  on the in-memory job store (default) and an asyncio.Event the job
  itself sets, so no clock mocking is needed.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from scheduler.config import JobConfig, SchedulerConfig
from scheduler.history import JobHistory
from scheduler.jobs import Job
from scheduler.scheduler import Scheduler


# --------------------------------------------------------------------------- #
# Facade unit tests (no APScheduler needed)
# --------------------------------------------------------------------------- #


def _job(func, *, job_id: str = "demo") -> Job:
    return Job(
        id=job_id,
        name=f"{job_id} job",
        interval_seconds=1,
        func=func,
        metadata={"connector": "demo"},
    )


def test_add_and_list_jobs_before_start() -> None:
    scheduler = Scheduler()
    scheduler.add_job(_job(AsyncMock(), job_id="a"))
    scheduler.add_job(_job(AsyncMock(), job_id="b"))

    rows = scheduler.list_jobs()
    assert {r["id"] for r in rows} == {"a", "b"}
    # Without start, every job has no next_run yet.
    assert all(r["next_run"] is None for r in rows)


def test_remove_job_is_idempotent() -> None:
    scheduler = Scheduler()
    scheduler.add_job(_job(AsyncMock(), job_id="x"))
    scheduler.remove_job("x")
    scheduler.remove_job("x")  # second call is a no-op
    assert scheduler.get_job("x") is None


def test_config_override_disables_job() -> None:
    """A SchedulerConfig override flips ``enabled`` on registration."""
    cfg = SchedulerConfig(
        enabled=True,
        jobs={"a": JobConfig(id="a", enabled=False, interval_seconds=999)},
    )
    scheduler = Scheduler(config=cfg)
    job = _job(AsyncMock(), job_id="a")
    scheduler.add_job(job)
    rows = scheduler.list_jobs()
    assert rows[0]["enabled"] is False
    assert rows[0]["interval_seconds"] == 999


@pytest.mark.asyncio
async def test_run_now_executes_off_schedule() -> None:
    func = AsyncMock(return_value={"pages": 5})
    scheduler = Scheduler()
    scheduler.add_job(_job(func, job_id="manual"))

    record = await scheduler.run_now("manual")
    assert record is not None
    assert record["outcome"] == "success"
    assert record["detail"]["pages"] == 5
    func.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_now_unknown_returns_none() -> None:
    scheduler = Scheduler()
    record = await scheduler.run_now("does-not-exist")
    assert record is None


@pytest.mark.asyncio
async def test_start_is_noop_when_disabled() -> None:
    scheduler = Scheduler(config=SchedulerConfig(enabled=False))
    scheduler.add_job(_job(AsyncMock(), job_id="quiet"))
    await scheduler.start()
    # No APScheduler should have been built; stop() must still be safe.
    await scheduler.stop()


# --------------------------------------------------------------------------- #
# Integration: real APScheduler tick
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_scheduler_actually_fires_a_job() -> None:
    """End-to-end: start scheduler, wait for one real tick, stop."""
    fired = asyncio.Event()
    call_count = 0

    async def work() -> dict:
        nonlocal call_count
        call_count += 1
        fired.set()
        return {"call": call_count}

    cfg = SchedulerConfig(enabled=True, jobs={})
    history = JobHistory()
    scheduler = Scheduler(config=cfg, history=history)
    scheduler.add_job(
        Job(
            id="fast_demo",
            name="fast demo",
            interval_seconds=1,
            func=work,
            metadata={"connector": "demo"},
        )
    )

    await scheduler.start()
    try:
        await asyncio.wait_for(fired.wait(), timeout=5.0)
    finally:
        await scheduler.stop()

    last = history.last_run("fast_demo")
    assert last is not None
    assert last.outcome == "success"
    assert last.detail.get("call") == 1


@pytest.mark.asyncio
async def test_scheduler_continues_after_failing_job() -> None:
    """A failing job must not kill the scheduler — next tick still fires."""
    runs = 0
    fired_twice = asyncio.Event()

    async def flaky() -> dict:
        nonlocal runs
        runs += 1
        if runs == 1:
            raise RuntimeError("transient")
        fired_twice.set()
        return {"call": runs}

    cfg = SchedulerConfig(enabled=True, jobs={})
    history = JobHistory()
    scheduler = Scheduler(config=cfg, history=history)
    scheduler.add_job(
        Job(
            id="flaky",
            name="flaky",
            interval_seconds=1,
            func=flaky,
            metadata={"connector": "demo"},
        )
    )

    await scheduler.start()
    try:
        await asyncio.wait_for(fired_twice.wait(), timeout=10.0)
    finally:
        await scheduler.stop()

    rows = history.list(job_id="flaky")
    outcomes = [r.outcome for r in rows]
    assert "failed" in outcomes
    assert "success" in outcomes


# --------------------------------------------------------------------------- #
# Pause / resume
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_pause_and_resume_after_start() -> None:
    cfg = SchedulerConfig(enabled=True, jobs={})
    scheduler = Scheduler(config=cfg)
    scheduler.add_job(
        Job(
            id="pausable",
            name="pausable",
            interval_seconds=60,
            func=AsyncMock(return_value=None),
        )
    )
    await scheduler.start()
    try:
        assert scheduler.pause_job("pausable") is True
        assert scheduler.resume_job("pausable") is True
        # Unknown id returns False — but doesn't raise.
        assert scheduler.pause_job("missing") is False
    finally:
        await scheduler.stop()


def test_pause_resume_before_start_returns_false() -> None:
    scheduler = Scheduler()
    scheduler.add_job(_job(AsyncMock(), job_id="x"))
    assert scheduler.pause_job("x") is False
    assert scheduler.resume_job("x") is False
