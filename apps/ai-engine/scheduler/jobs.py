"""Job specs + factories for the four built-in scheduler jobs.

Each factory accepts a callable (``func``) that performs the actual work.
The scheduler does NOT instantiate engines. This dependency-injection
shape means:

- Tests can pass an ``AsyncMock`` and assert call shape without standing
  up Confluence/SigNoz/Reconciler.
- Production code in ``main.py`` builds the engine once and binds the
  factories to it, then registers each :class:`Job` with the scheduler.
- Adding a fifth job (e.g. honeytoken refresh) is a matter of writing
  another factory + adding it to :func:`default_jobs`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("aegis.scheduler.jobs")

# A scheduled job's work function: takes nothing, returns an awaitable
# whose value (if any) ends up in the run record's ``detail`` field.
# Returning a dict is encouraged but not required.
JobFunc = Callable[[], Awaitable[Any]]


@dataclass
class Job:
    """Typed handle for a single scheduled job.

    Attributes:
        id: Stable identifier — referenced by API paths and history.
        name: Human-friendly label for logs and dashboards.
        interval_seconds: How often to fire. Wrapped into
            APScheduler's ``IntervalTrigger`` by :class:`Scheduler`.
        func: The async work function. Wrapped by :class:`JobRunner`
            with kill-switch + OTel + exception isolation.
        enabled: Toggle. Disabled jobs are not registered with APScheduler
            but remain visible in :meth:`Scheduler.list_jobs` so operators
            see what *would* run.
        metadata: Free-form attributes copied into the OTel span and the
            run record's ``detail``. A common use is the lookback window.
    """

    id: str
    name: str
    interval_seconds: int
    func: JobFunc
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def interval_minutes(self) -> float:
        """Convenience for OTel attribute reporting."""
        return self.interval_seconds / 60.0


# --------------------------------------------------------------------------- #
# Built-in factories
# --------------------------------------------------------------------------- #


def confluence_sync_job(
    *,
    func: JobFunc,
    interval_minutes: int = 60,
    enabled: bool = True,
) -> Job:
    """Factory: pull every Confluence page in the configured space.

    The injected ``func`` is expected to wrap ``ConfluenceSync.sync()``
    or the equivalent ``WikiEngine.ingest_confluence()`` shim. It must
    be self-contained — the scheduler passes no arguments.
    """
    return Job(
        id="confluence_sync",
        name="Confluence wiki sync",
        interval_seconds=max(1, interval_minutes) * 60,
        func=func,
        enabled=enabled,
        metadata={"connector": "confluence"},
    )


def signoz_sync_job(
    *,
    func: JobFunc,
    interval_minutes: int = 15,
    lookback_minutes: int = 60,
    enabled: bool = True,
) -> Job:
    """Factory: ingest resolved SigNoz incidents from a sliding window.

    ``lookback_minutes`` is recorded in the job's metadata so operators
    can read it back from the OTel span and the history API; the
    injected ``func`` is responsible for actually applying the window
    when it calls the underlying ``SignozSync.sync()``.
    """
    return Job(
        id="signoz_sync",
        name="SigNoz incident sync",
        interval_seconds=max(1, interval_minutes) * 60,
        func=func,
        enabled=enabled,
        metadata={
            "connector": "signoz",
            "lookback_minutes": lookback_minutes,
        },
    )


def staleness_lint_job(
    *,
    func: JobFunc,
    interval_hours: int = 24,
    enabled: bool = True,
) -> Job:
    """Factory: walk the vault, compute freshness labels, archive expired pages.

    The injected ``func`` typically wraps
    ``StalenessLinter.scan_vault(pages)`` after a ``WikiEngine.load_vault()``.
    """
    return Job(
        id="staleness_lint",
        name="Wiki staleness lint",
        interval_seconds=max(1, interval_hours) * 3600,
        func=func,
        enabled=enabled,
        metadata={"connector": "staleness_linter"},
    )


def doc_reconciliation_job(
    *,
    func: JobFunc,
    interval_hours: int = 12,
    topics: list[str] | None = None,
    enabled: bool = True,
) -> Job:
    """Factory: run :meth:`Reconciler.compare` for each watched topic.

    The injected ``func`` is expected to iterate over ``topics`` itself
    so the scheduler stays uniform — each scheduled tick is "one job =
    one work function". Topics are reflected as metadata so operators
    can see the active watch list without reading code.
    """
    if topics is None:
        topics = ["all"]
    return Job(
        id="doc_reconciliation",
        name="Cross-source doc reconciliation",
        interval_seconds=max(1, interval_hours) * 3600,
        func=func,
        enabled=enabled,
        metadata={"connector": "reconciler", "topics": list(topics)},
    )


# --------------------------------------------------------------------------- #
# Default-jobs convenience
# --------------------------------------------------------------------------- #


def default_jobs(*, deps: dict[str, Any]) -> list[Job]:
    """Build the four built-in jobs from injected dependencies.

    Required keys in ``deps``:
        - ``confluence_sync``: callable returning awaitable; calls
          ``ConfluenceSync.sync()`` (or the engine wrapper).
        - ``signoz_sync``: callable; calls ``SignozSync.sync()``.
        - ``staleness_lint``: callable; calls ``StalenessLinter.scan_vault``.
        - ``doc_reconciliation``: callable; iterates topics + calls
          ``Reconciler.compare(topic)``.

    Missing keys produce *disabled* jobs so the operator still sees them
    in ``GET /api/v1/scheduler/jobs`` with ``enabled=false`` rather than
    a silent gap. This is friendlier than crashing on startup when, e.g.,
    SigNoz creds aren't configured yet.
    """
    jobs: list[Job] = []

    func_confluence = deps.get("confluence_sync")
    jobs.append(
        confluence_sync_job(
            func=func_confluence or _missing_dep("confluence_sync"),
            enabled=func_confluence is not None,
        )
    )

    func_signoz = deps.get("signoz_sync")
    jobs.append(
        signoz_sync_job(
            func=func_signoz or _missing_dep("signoz_sync"),
            enabled=func_signoz is not None,
        )
    )

    func_staleness = deps.get("staleness_lint")
    jobs.append(
        staleness_lint_job(
            func=func_staleness or _missing_dep("staleness_lint"),
            enabled=func_staleness is not None,
        )
    )

    func_reconcile = deps.get("doc_reconciliation")
    topics = deps.get("reconciliation_topics") or ["all"]
    jobs.append(
        doc_reconciliation_job(
            func=func_reconcile or _missing_dep("doc_reconciliation"),
            topics=topics,
            enabled=func_reconcile is not None,
        )
    )

    return jobs


def _missing_dep(name: str) -> JobFunc:
    """Stub func used for disabled-by-default jobs.

    The job is registered with ``enabled=False`` so this never actually
    runs; it exists only so the :class:`Job` dataclass invariants (a
    callable in ``func``) are satisfied.
    """

    async def _stub() -> dict[str, Any]:  # pragma: no cover - never invoked
        logger.warning("scheduler: %s job has no dependency wired", name)
        return {"skipped": True, "reason": f"{name} dependency missing"}

    return _stub
