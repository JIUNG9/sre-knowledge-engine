"""FastAPI router for the Aegis executor (Layer 4 / Phase 2.5).

Endpoints under ``/api/v1/executor``:

* ``POST /api/v1/executor/execute`` — body: investigation_id + the
  ProposedAction + a ``grant_id``. The grant was issued in-process by
  :meth:`Executor.issue_grant` after the real approval gate ran, and is
  bound to this exact action. A real run uses the grant up.
* ``POST /api/v1/executor/dry-run`` — same as ``/execute`` but with
  ``dry_run`` forced to True. Checks the grant without using it.
* ``GET  /api/v1/executor/audit`` — paginated audit rows.
* ``GET  /api/v1/executor/config`` — current config snapshot
  (allowed verbs, dry-run mode, terraform-apply gate state).

Like the scheduler and control-tower routers, the dependency
``get_executor`` returns 503 by default — ``main.py`` overrides it
once the lifespan hook builds an :class:`Executor`. This keeps the
router import-safe.

Callers never send an approval decision. An earlier version accepted
``decision`` in the body, which let any caller claim ``approved: true``;
a body that still carries ``decision`` now fails validation (422).

Every route requires ``Authorization: Bearer <AEGIS_EXECUTOR_API_TOKEN>``.

Nothing in this repo issues grants yet. Wiring the control tower's
approval step to :meth:`Executor.issue_grant` is the follow-up; until
then ``/execute`` refuses every call, which is the safe direction.
"""

from __future__ import annotations

import hmac
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from .executor import Executor
from .result import ExecutionResult

executor_router = APIRouter(prefix="/api/v1/executor", tags=["executor"])


# --------------------------------------------------------------------------- #
# Dependency
# --------------------------------------------------------------------------- #


def get_executor() -> Executor:
    """Return the active :class:`Executor`.

    Default implementation raises 503 so router import never starts a
    real executor. ``main.py`` overrides this in the lifespan hook
    when ``AEGIS_EXECUTOR_ENABLED=1``.
    """
    raise HTTPException(
        status_code=503,
        detail=(
            "executor not configured; set AEGIS_EXECUTOR_ENABLED=1 "
            "and override `get_executor` in the FastAPI app"
        ),
    )


def require_token(
    authorization: str | None = Header(default=None),
    executor: Executor = Depends(get_executor),
) -> Executor:
    """Check the bearer token, then hand back the executor.

    An executor with no token configured refuses every call, so a
    misconfigured deploy fails closed.
    """
    expected = executor.config.api_token
    if not expected:
        raise HTTPException(status_code=503, detail="executor API token not set")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return executor


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #


class ActionPayload(BaseModel):
    """The ProposedAction shape, as accepted over the wire."""

    model_config = ConfigDict(extra="ignore")

    name: str
    verb: str
    target: str = ""
    environment: str = "prod"
    category: str = "deployment"
    blast_radius: int = 1
    reversible: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    """Body for ``POST /api/v1/executor/execute``."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str | None = None
    action: ActionPayload
    grant_id: str = Field(min_length=1, max_length=128)
    dry_run: bool | None = None


class ConfigView(BaseModel):
    """Body for ``GET /api/v1/executor/config``."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    dry_run_default: bool
    terraform_apply_allowed: bool
    require_two_approvals_for_execute: bool
    audit_log_path: str
    allowed_verbs: dict[str, list[str]]
    blocked_verbs_per_wrapper: dict[str, list[str]]


# --------------------------------------------------------------------------- #
# Adapter — translate the Pydantic payload into the duck-typed shape the
# executor consumes (mirroring control_tower.investigation.ProposedAction).
# --------------------------------------------------------------------------- #


class _ActionAdapter:
    """Duck-typed wrapper around :class:`ActionPayload`."""

    def __init__(self, payload: ActionPayload) -> None:
        self.name = payload.name
        self.verb = payload.verb
        self.target = payload.target
        self.environment = payload.environment
        self.category = payload.category
        self.blast_radius = payload.blast_radius
        self.reversible = payload.reversible
        self.metadata = dict(payload.metadata)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@executor_router.post(
    "/execute",
    response_model=ExecutionResult,
    summary="Execute a ProposedAction under the 4-stage ladder",
)
def post_execute(
    body: ExecuteRequest,
    executor: Executor = Depends(require_token),
) -> ExecutionResult:
    """Run the full executor pipeline. May refuse, fail, or execute.

    ``dry_run`` in the body can only force a preview. It can't turn
    dry-run off when the operator left ``AEGIS_EXECUTOR_DRY_RUN`` on.
    """
    return executor.execute_with_grant(
        _ActionAdapter(body.action),
        body.grant_id,
        investigation_id=body.investigation_id,
        dry_run=True if body.dry_run else None,
    )


@executor_router.post(
    "/dry-run",
    response_model=ExecutionResult,
    summary="Dry-run an action — wrappers report what they would do",
)
def post_dry_run(
    body: ExecuteRequest,
    executor: Executor = Depends(require_token),
) -> ExecutionResult:
    """Identical to ``/execute`` but ``dry_run`` is forced True."""
    return executor.execute_with_grant(
        _ActionAdapter(body.action),
        body.grant_id,
        investigation_id=body.investigation_id,
        dry_run=True,
    )


@executor_router.get(
    "/audit",
    summary="Recent executor audit rows (newest first)",
)
def get_audit(
    executor: Executor = Depends(require_token),
    since: str | None = Query(default=None, description="ISO timestamp lower bound"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Return up to ``limit`` audit rows from the JSONL log."""
    cutoff: datetime | None = None
    if since:
        try:
            cutoff = datetime.fromisoformat(since)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"invalid 'since' (must be ISO-8601): {exc}",
            ) from exc
    return executor.audit.read_recent(since=cutoff, limit=limit)


@executor_router.get(
    "/config",
    response_model=ConfigView,
    summary="Current executor configuration",
)
def get_config(executor: Executor = Depends(require_token)) -> ConfigView:
    """Return the live ExecutorConfig snapshot, plus per-wrapper blocks."""
    blocked = {
        name: sorted(w.blocked_verbs) for name, w in executor.wrappers.items()
    }
    return ConfigView(
        enabled=executor.config.enabled,
        dry_run_default=executor.config.dry_run_default,
        terraform_apply_allowed=executor.config.terraform_apply_allowed,
        require_two_approvals_for_execute=executor.config.require_two_approvals_for_execute,
        audit_log_path=executor.config.audit_log_path,
        allowed_verbs={k: list(v) for k, v in executor.config.allowed_verbs.items()},
        blocked_verbs_per_wrapper=blocked,
    )
