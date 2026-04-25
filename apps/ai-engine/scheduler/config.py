"""Environment-driven configuration for the Aegis scheduler.

Reads ``AEGIS_SCHEDULER_*`` environment variables and produces a
:class:`SchedulerConfig`. Defaults are intentionally conservative:
the scheduler is **disabled by default** so CI, unit tests, and cold
starts never fire a sync. Production deployments set
``AEGIS_SCHEDULER_ENABLED=1`` (plus optional per-job overrides) to
opt in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean env var with common truthy/falsy synonyms."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Parse an integer env var, falling back to ``default`` on parse error."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class JobConfig:
    """Per-job runtime config, decoupled from the :class:`Job` factory.

    Attributes:
        id: Stable identifier. Matches the :class:`Job` id; used in API
            paths (e.g. ``/api/v1/scheduler/jobs/{id}/run``).
        enabled: When False, the scheduler skips registering this job.
        interval_seconds: Trigger interval in seconds. Consumed by
            APScheduler's ``IntervalTrigger``.
    """

    id: str
    enabled: bool = True
    interval_seconds: int = 3600


@dataclass
class SchedulerConfig:
    """Top-level scheduler config.

    Attributes:
        enabled: Master switch. When False, :meth:`Scheduler.start` is
            a no-op (the scheduler can still be constructed, which keeps
            the API router mount safe during import).
        jobs: Per-job overrides. Lookup is by ``id``; jobs without an
            override keep their built-in defaults.
        max_history: Number of past runs retained in-memory per job.
            The ``/history`` API trims to this cap.
    """

    enabled: bool = False
    jobs: dict[str, JobConfig] = field(default_factory=dict)
    max_history: int = 100

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        """Build a :class:`SchedulerConfig` from the environment.

        Recognized env vars:
            - ``AEGIS_SCHEDULER_ENABLED`` — master on/off (default off)
            - ``AEGIS_SCHEDULER_MAX_HISTORY`` — per-job history depth
            - ``AEGIS_SCHEDULER_CONFLUENCE_MINUTES`` — override interval
            - ``AEGIS_SCHEDULER_CONFLUENCE_ENABLED`` — disable just this job
            - (same pattern for ``SIGNOZ``, ``STALENESS``, ``RECONCILIATION``)
        """
        enabled = _env_bool("AEGIS_SCHEDULER_ENABLED", False)
        max_history = _env_int("AEGIS_SCHEDULER_MAX_HISTORY", 100)

        jobs: dict[str, JobConfig] = {}
        for job_id, default_minutes, env_prefix in (
            ("confluence_sync", 60, "CONFLUENCE"),
            ("signoz_sync", 15, "SIGNOZ"),
            ("staleness_lint", 24 * 60, "STALENESS"),
            ("doc_reconciliation", 12 * 60, "RECONCILIATION"),
        ):
            job_enabled = _env_bool(
                f"AEGIS_SCHEDULER_{env_prefix}_ENABLED", True
            )
            minutes = _env_int(
                f"AEGIS_SCHEDULER_{env_prefix}_MINUTES", default_minutes
            )
            jobs[job_id] = JobConfig(
                id=job_id,
                enabled=job_enabled,
                interval_seconds=max(1, minutes) * 60,
            )

        return cls(enabled=enabled, jobs=jobs, max_history=max_history)
