"""Aegis Scheduler — periodic sync runner (Phase 2.4).

Public API:
- :class:`Scheduler` — thin facade over APScheduler's ``AsyncIOScheduler``.
- :class:`Job` / :class:`JobConfig` — typed job specs.
- :class:`SchedulerConfig` — env-driven configuration.
- :func:`default_jobs` — factory that returns the four built-in jobs
  (Confluence sync, SigNoz sync, staleness lint, doc reconciliation) with
  their default intervals.
- :class:`JobHistory` / :class:`JobRunRecord` — in-memory run history.
- :class:`JobRunner` — wraps every scheduled execution with kill-switch
  gating, OTel span emission, and exception isolation.

Design goals (Layer 2.4):
- Disabled by default. Production deployments opt in via
  ``AEGIS_SCHEDULER_ENABLED=1``. CI and unit tests never fire jobs
  unless the test explicitly starts the scheduler.
- A single failing job never kills the scheduler — failures are logged,
  recorded to ``JobHistory``, and attributed to the span.
- Callers never import APScheduler directly. Every knob is on
  :class:`Scheduler` so the underlying library can be swapped later.

Typical wiring::

    from scheduler import Scheduler, SchedulerConfig, default_jobs

    config = SchedulerConfig.from_env()
    if config.enabled:
        scheduler = Scheduler(config=config)
        for job in default_jobs(deps={"wiki_engine": engine}):
            scheduler.add_job(job)
        await scheduler.start()
        app.state.scheduler = scheduler
"""

from __future__ import annotations

from .config import JobConfig, SchedulerConfig
from .history import JobHistory, JobRunRecord
from .jobs import (
    Job,
    confluence_sync_job,
    default_jobs,
    doc_reconciliation_job,
    signoz_sync_job,
    staleness_lint_job,
)
from .runner import JobRunner, run_with_safety
from .scheduler import Scheduler

__all__ = [
    "Job",
    "JobConfig",
    "JobHistory",
    "JobRunRecord",
    "JobRunner",
    "Scheduler",
    "SchedulerConfig",
    "confluence_sync_job",
    "default_jobs",
    "doc_reconciliation_job",
    "run_with_safety",
    "signoz_sync_job",
    "staleness_lint_job",
]
