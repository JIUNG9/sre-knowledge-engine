"""Thin facade over APScheduler's :class:`AsyncIOScheduler`.

We want callers to depend on Aegis types only — never on
``apscheduler.*`` directly — so the underlying library can be swapped
later (e.g. for Celery, Arq, or APScheduler 4.x). The facade exposes
exactly the operations the API router and lifespan need.

Design notes:
- Uses an in-memory ``MemoryJobStore``. Persistent stores (SQLAlchemy,
  Redis) are explicitly out of scope: a Phase 2.4 sync scheduler does
  not need cross-restart durability — the schedule recomputes on every
  app start.
- :class:`SchedulerConfig.enabled` gates :meth:`start`. When disabled,
  :meth:`start` is a no-op so unit tests / CI cold starts never tick.
- Every registered job is wrapped by :class:`JobRunner` so kill-switch
  + OTel + history are uniform across job types.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .config import SchedulerConfig
from .history import JobHistory
from .runner import JobRunner

if TYPE_CHECKING:
    from .jobs import Job

logger = logging.getLogger("aegis.scheduler")


class Scheduler:
    """Manages a set of :class:`Job` objects on a periodic trigger.

    Args:
        config: :class:`SchedulerConfig`. If ``None``, defaults to
            ``SchedulerConfig()`` (disabled).
        history: Optional :class:`JobHistory` instance. The scheduler
            constructs one internally if not provided so callers don't
            have to.
        killswitch: Optional kill-switch object exposing
            ``is_active() -> bool``. Forwarded to every :class:`JobRunner`.
    """

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        *,
        history: JobHistory | None = None,
        killswitch: Any | None = None,
    ) -> None:
        self.config = config or SchedulerConfig()
        self.history = history or JobHistory(
            max_per_job=self.config.max_history
        )
        self.runner = JobRunner(self.history, killswitch=killswitch)
        self._jobs: dict[str, "Job"] = {}
        self._impl: Any | None = None  # APScheduler AsyncIOScheduler
        self._started = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Build the APScheduler instance and begin firing jobs.

        No-op when :attr:`config.enabled` is False — keeps CI / cold
        starts quiet without forcing the caller to gate the call.
        """
        if not self.config.enabled:
            logger.info("scheduler: disabled (AEGIS_SCHEDULER_ENABLED unset)")
            return
        if self._started:
            return

        from apscheduler.jobstores.memory import MemoryJobStore
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        loop = asyncio.get_running_loop()
        scheduler = AsyncIOScheduler(
            event_loop=loop,
            jobstores={"default": MemoryJobStore()},
            timezone="UTC",
        )

        for job in self._jobs.values():
            if not job.enabled:
                logger.info(
                    "scheduler: job %s disabled by config; skipping registration",
                    job.id,
                )
                continue
            self._register_with_apscheduler(scheduler, job, IntervalTrigger)

        scheduler.start()
        self._impl = scheduler
        self._started = True
        logger.info(
            "scheduler: started with %d jobs (timezone=UTC)", len(self._jobs)
        )

    async def stop(self) -> None:
        """Shut the scheduler down gracefully.

        Awaits in-flight job completion (``wait=True``) up to the
        APScheduler default. Safe to call even if :meth:`start` was never
        called.
        """
        if not self._started or self._impl is None:
            return
        try:
            self._impl.shutdown(wait=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler: shutdown raised %r", exc)
        self._impl = None
        self._started = False
        logger.info("scheduler: stopped")

    def add_job(self, job: "Job") -> None:
        """Register a :class:`Job` with the scheduler.

        Adding a job after :meth:`start` is allowed and will register
        it live; adding before :meth:`start` defers registration to
        :meth:`start`.
        """
        # Apply config override for this job id, if present.
        override = self.config.jobs.get(job.id)
        if override is not None:
            job.enabled = override.enabled and job.enabled
            if override.interval_seconds > 0:
                job.interval_seconds = override.interval_seconds

        self._jobs[job.id] = job

        if self._started and self._impl is not None and job.enabled:
            from apscheduler.triggers.interval import IntervalTrigger

            self._register_with_apscheduler(self._impl, job, IntervalTrigger)

    def remove_job(self, job_id: str) -> None:
        """Stop firing the job and forget it.

        Idempotent — removing an unknown id silently no-ops.
        """
        self._jobs.pop(job_id, None)
        if self._impl is not None:
            try:
                self._impl.remove_job(job_id)
            except Exception:  # job may already be gone
                pass

    def list_jobs(self) -> list[dict[str, Any]]:
        """Snapshot every registered job for the API.

        Includes:
            - ``id``, ``name``, ``enabled``, ``interval_seconds``
            - ``next_run`` (ISO-8601) — None if not started or paused
            - ``last_run`` — last :class:`JobRunRecord` as dict
            - ``metadata`` — connector, lookback, topics, etc.
        """
        out: list[dict[str, Any]] = []
        for job in self._jobs.values():
            next_run = self._next_run_iso(job.id)
            last = self.history.last_run(job.id)
            out.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "enabled": job.enabled,
                    "interval_seconds": job.interval_seconds,
                    "next_run": next_run,
                    "last_run": last.to_dict() if last else None,
                    "metadata": dict(job.metadata),
                }
            )
        return out

    def get_job(self, job_id: str) -> "Job | None":
        """Look up a registered job by id, or None if not present."""
        return self._jobs.get(job_id)

    def pause_job(self, job_id: str) -> bool:
        """Pause future ticks for a job. Returns True on success."""
        if self._impl is None:
            return False
        try:
            self._impl.pause_job(job_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler: pause_job(%s) raised %r", job_id, exc)
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a previously-paused job. Returns True on success."""
        if self._impl is None:
            return False
        try:
            self._impl.resume_job(job_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler: resume_job(%s) raised %r", job_id, exc)
            return False

    async def run_now(self, job_id: str) -> dict[str, Any] | None:
        """Trigger a job immediately, bypassing the schedule.

        Returns the resulting :class:`JobRunRecord` as a dict so the
        API can echo it. ``None`` when the id is unknown.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        record = await self.runner.run_once(job)
        return record.to_dict()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _register_with_apscheduler(
        self,
        scheduler: Any,
        job: "Job",
        IntervalTriggerCls: Any,
    ) -> None:
        """Hand a wrapped job to APScheduler with an IntervalTrigger.

        ``coalesce=True`` collapses missed-fire backlogs into one run —
        the right default for sync jobs because we always want the
        latest data, not a queue of stale ticks.
        """
        wrapped = self.runner.wrap(job)
        trigger = IntervalTriggerCls(seconds=job.interval_seconds)
        scheduler.add_job(
            wrapped,
            trigger=trigger,
            id=job.id,
            name=job.name,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info(
            "scheduler: registered job %s every %ds",
            job.id,
            job.interval_seconds,
        )

    def _next_run_iso(self, job_id: str) -> str | None:
        if self._impl is None:
            return None
        try:
            ap_job = self._impl.get_job(job_id)
        except Exception:
            return None
        if ap_job is None or ap_job.next_run_time is None:
            return None
        return ap_job.next_run_time.isoformat()
