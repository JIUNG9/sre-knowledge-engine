# Aegis Scheduler (Phase 2.4)

A small APScheduler-driven background runner that pulls from each upstream
connector on its own cadence: Confluence wiki ingest, SigNoz incident
ingest, vault staleness lint, and cross-source doc reconciliation. Until
this layer landed, every sync was on-demand only — somebody had to POST
to `/api/v1/sync/...` for anything to happen.

## Default jobs

| Job ID | Default interval | Work |
| --- | --- | --- |
| `confluence_sync` | 60 minutes | Pull every page in the configured Confluence space |
| `signoz_sync` | 15 minutes | Ingest resolved SigNoz incidents from a `lookback_minutes` window |
| `staleness_lint` | 24 hours | Walk the vault, label freshness, archive expired pages |
| `doc_reconciliation` | 12 hours | Run `Reconciler.compare(topic)` for each watched topic |

## Enabling in production

The scheduler is **disabled by default** so CI and unit tests never fire
syncs. Production deployments opt in via env vars:

```bash
# Master switch
export AEGIS_SCHEDULER_ENABLED=1

# Per-job overrides (all optional)
export AEGIS_SCHEDULER_CONFLUENCE_MINUTES=30
export AEGIS_SCHEDULER_SIGNOZ_MINUTES=5
export AEGIS_SCHEDULER_STALENESS_MINUTES=1440
export AEGIS_SCHEDULER_RECONCILIATION_MINUTES=720

# Per-job kill (useful when one connector is unconfigured)
export AEGIS_SCHEDULER_SIGNOZ_ENABLED=0
```

`main.py` reads `SchedulerConfig.from_env()` in its lifespan hook,
constructs a `Scheduler` from `default_jobs(deps=...)`, and calls
`start()`. On shutdown, `stop()` waits for in-flight jobs.

## Adding a custom job

```python
from scheduler import Scheduler, Job

async def my_job() -> dict:
    ...
    return {"items_processed": 42}

scheduler.add_job(Job(
    id="my_custom_job",
    name="My periodic task",
    interval_seconds=300,
    func=my_job,
    metadata={"connector": "acme-corp"},
))
```

Anything the function returns as a dict is merged into the run record's
`detail` field, surfaced via the history API, and visible to operators.

## Inspecting job history

```bash
# Live job state
curl localhost:8000/api/v1/scheduler/jobs

# Recent runs (newest first)
curl 'localhost:8000/api/v1/scheduler/history?job_id=signoz_sync&limit=20'

# Trigger off-schedule
curl -X POST localhost:8000/api/v1/scheduler/jobs/confluence_sync/run
```

## Safety guarantees

Every tick passes through `JobRunner` which:

1. Checks the kill switch — if active, the run is recorded as `skipped`
   and the work function is **never called**.
2. Opens an OTel span `aegis.scheduler.job` with `aegis.job.outcome`,
   `aegis.job.duration_ms`, and connector metadata.
3. Catches every exception. A failing job logs and records `failed` —
   but it never stops the scheduler.

History is in-memory (per-process). For durable audit, the underlying
sync modules (Confluence, SigNoz) write JSONL to `_meta/` in the vault.
