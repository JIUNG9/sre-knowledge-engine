"""Aegis AI Engine — FastAPI entry point.

The AI Engine is the core intelligence layer of the Aegis DevSecOps Command
Center. It provides endpoints for incident investigation, log/metric analysis,
and interfaces with Claude API via MCP tools for autonomous SRE workflows.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from control_tower.api import control_tower_router, get_control_tower
from executor import Executor, ExecutorConfig
from executor.api import executor_router, get_executor
from executor.audit import AuditLogger
from routers import analyze, health, investigate, logs, mcp, wiki
from scheduler import Scheduler, SchedulerConfig, default_jobs
from scheduler.api import get_scheduler, scheduler_router

# Layer 0.1 — PII Redaction Proxy for Claude API.
#
# To enable PII redaction for every outbound Claude call, wrap the SDK client
# at instantiation time. Because the proxy is a drop-in for
# ``anthropic.Anthropic`` (same ``messages.create`` signature, same response
# shape, streaming preserved), no downstream code needs to change:
#
#     import anthropic
#     from proxy import AnthropicProxy, PIIProxyConfig
#
#     claude = AnthropicProxy(
#         anthropic.Anthropic(api_key=settings.anthropic_api_key),
#         PIIProxyConfig(),   # enabled=True by default
#     )
#     # ... hand ``claude`` to orchestrator / remediator / analyzer as usual.
#
# See ``apps/ai-engine/proxy/README.md`` for usage patterns.

logger = logging.getLogger("aegis")


def _build_executor() -> Executor | None:
    """Construct an Executor when AEGIS_EXECUTOR_ENABLED is truthy.

    Returns None otherwise. The audit log path defaults to
    ./aegis-executor-audit.jsonl in the current working directory; set
    AEGIS_EXECUTOR_AUDIT_PATH to override. Init failures degrade to None
    so the API mounts the default 503 dependency rather than crashing.

    Production wiring should also set AEGIS_EXECUTOR_DRY_RUN=0 once an
    operator has opted into real execution. The default is dry-run on,
    which means kubectl/terraform/aws commands report what they WOULD
    have done without invoking the binaries.
    """
    if os.environ.get("AEGIS_EXECUTOR_ENABLED", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        config = ExecutorConfig.from_env()
        from pathlib import Path
        return Executor(
            config=config,
            audit=AuditLogger(Path(config.audit_log_path)),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("executor unavailable (init): %s", exc)
        return None


def _build_scheduler() -> Scheduler | None:
    """Construct a Scheduler from env + default jobs.

    Returns None when ``AEGIS_SCHEDULER_ENABLED`` is not truthy. We do
    not wire engine deps here — the WikiEngine / Reconciler instances
    live elsewhere in the lifespan. Each :class:`Job` whose dependency
    has not been injected is registered with ``enabled=False`` so it
    appears in ``GET /api/v1/scheduler/jobs`` for visibility but never
    actually fires.

    Production wiring should extend this function: pass the real
    ``deps`` dict (``confluence_sync``, ``signoz_sync``, etc.) to
    :func:`scheduler.default_jobs` so the jobs are actually live.
    """
    config = SchedulerConfig.from_env()
    if not config.enabled:
        return None
    try:
        scheduler = Scheduler(config=config)
        # No engine deps injected by default — operators must extend this
        # function for their environment. The jobs still register so the
        # control plane is visible.
        for job in default_jobs(deps={}):
            scheduler.add_job(job)
        return scheduler
    except Exception as exc:  # noqa: BLE001
        logger.warning("scheduler unavailable (init): %s", exc)
        return None


def _build_control_tower():
    """Construct a ControlTower instance for production use.

    Lazy import keeps the FastAPI startup path lightweight when the
    Control Tower's heavier deps (anthropic SDK, ollama client) are
    not yet installed. Returns None if construction fails — the API
    layer falls back to the default 503 dependency.
    """
    try:
        from control_tower import ControlTower, ControlTowerConfig
    except Exception as exc:
        logger.warning("control tower unavailable (import): %s", exc)
        return None
    try:
        return ControlTower(config=ControlTowerConfig())
    except Exception as exc:
        logger.warning("control tower unavailable (init): %s", exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("Aegis AI Engine started")

    # Layer 3 — Claude Control Tower. Build a tower if the env asks for
    # it and stash on app.state so the dependency below can return it.
    # Disabled by default so unit tests / CI / cold starts don't try to
    # connect to Anthropic. Set AEGIS_CONTROL_TOWER=1 to enable.
    if os.environ.get("AEGIS_CONTROL_TOWER", "").lower() in ("1", "true", "yes"):
        tower = _build_control_tower()
        if tower is not None:
            app.state.control_tower = tower
            app.dependency_overrides[get_control_tower] = lambda: tower
            logger.info("control tower attached to /api/v1/investigate")

    # Phase 2.4 — periodic sync scheduler. Disabled by default so CI and
    # cold starts never fire. Enable via ``AEGIS_SCHEDULER_ENABLED=1``;
    # see ``apps/ai-engine/scheduler/README.md`` for env vars and how to
    # extend ``_build_scheduler`` with real engine deps.
    scheduler = _build_scheduler()
    if scheduler is not None:
        try:
            await scheduler.start()
            app.state.scheduler = scheduler
            app.dependency_overrides[get_scheduler] = lambda: scheduler
            logger.info("scheduler attached to /api/v1/scheduler")
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler failed to start: %s", exc)

    # Phase 2.5 — Layer 4 executor. Disabled by default; opt-in via
    # ``AEGIS_EXECUTOR_ENABLED=1``. Even when enabled, dry-run is on by
    # default — set ``AEGIS_EXECUTOR_DRY_RUN=0`` to run real commands.
    # The executor only dispatches actions that have already cleared
    # Layer 3 (Control Tower) + Layer 4 (Guardrails) gates AND have a
    # decision tier of EXECUTE. Kill switch is checked one final time
    # at the moment of execution, after every other gate has cleared.
    executor = _build_executor()
    if executor is not None:
        app.state.executor = executor
        app.dependency_overrides[get_executor] = lambda: executor
        logger.info("executor attached to /api/v1/executor")

    try:
        yield
    finally:
        # Graceful shutdown: drain in-flight jobs.
        active_scheduler = getattr(app.state, "scheduler", None)
        if active_scheduler is not None:
            try:
                await active_scheduler.stop()
            except Exception as exc:  # noqa: BLE001
                logger.warning("scheduler shutdown raised: %s", exc)
        logger.info("Aegis AI Engine shutting down")


app = FastAPI(
    title="Aegis AI Engine",
    version="0.1.0",
    description="AI-Native DevSecOps Command Center — Intelligence Layer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(investigate.router)
app.include_router(analyze.router)
app.include_router(logs.router)
app.include_router(mcp.router)
app.include_router(wiki.router)
# Layer 3 — Claude Control Tower. The dependency returns 503 until the
# lifespan hook above attaches a real ControlTower instance (gated on
# AEGIS_CONTROL_TOWER env). This keeps OpenAPI complete in dev while
# preventing accidental network calls at startup.
app.include_router(control_tower_router)
# Phase 2.4 — scheduler control plane. Default ``get_scheduler`` returns
# 503 until the lifespan hook above attaches a real ``Scheduler`` instance
# (gated on ``AEGIS_SCHEDULER_ENABLED`` env). Mount unconditionally so the
# OpenAPI schema is complete and CI smoke tests can introspect endpoints
# without needing the scheduler running.
app.include_router(scheduler_router)
# Phase 2.5 — Layer 4 executor. Default ``get_executor`` returns 503 until
# the lifespan hook above attaches a real ``Executor`` instance (gated on
# ``AEGIS_EXECUTOR_ENABLED`` env, additionally gated on per-deployment
# opt-in to leave dry-run mode). Mount unconditionally so OpenAPI surfaces
# the executor endpoints in dev environments.
app.include_router(executor_router)
