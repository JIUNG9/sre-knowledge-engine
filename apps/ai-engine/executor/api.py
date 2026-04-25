"""FastAPI router for the Aegis executor (Layer 4 / Phase 2.5).

Endpoints under ``/api/v1/executor``:

* ``POST /api/v1/executor/execute`` — body: investigation_id + the
  ProposedAction + the GuardrailDecision (as a dict). Runs through
  every gate and returns an :class:`ExecutionResult`.
* ``POST /api/v1/executor/dry-run`` — same as ``/execute`` but with
  ``dry_run`` forced to True.
* ``GET  /api/v1/executor/audit`` — paginated audit rows.
* ``GET  /api/v1/executor/config`` — current config snapshot
  (allowed verbs, dry-run mode, terraform-apply gate state).

Like the scheduler and control-tower routers, the dependency
``get_executor`` returns 503 by default — ``main.py`` overrides it
once the lifespan hook builds an :class:`Executor`. This keeps the
router import-safe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
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


class ApprovalPayload(BaseModel):
    """Mirror of guardrails.approval.ApprovalResult — only the fields
    the executor actually consults.
    """

    model_config = ConfigDict(extra="ignore")

    approved: bool = False
    approvers: list[str] = Field(default_factory=list)
    backend: str = "none"
    reason: str | None = None


class PolicyPayload(BaseModel):
    """Mirror of guardrails.policy.PolicyDecision — only the fields
    the executor reads.
    """

    model_config = ConfigDict(extra="ignore")

    required_approvals: int = 0
    approver_groups: list[str] = Field(default_factory=list)


class DecisionPayload(BaseModel):
    """The Layer 4 decision, as accepted over the wire."""

    model_config = ConfigDict(extra="ignore")

    tier: str = "SUGGEST"
    approved: bool = False
    approval: ApprovalPayload | None = None
    policy: PolicyPayload | None = None
    reasons: list[str] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    """Body for ``POST /api/v1/executor/execute``."""

    model_config = ConfigDict(extra="ignore")

    investigation_id: str | None = None
    action: ActionPayload
    decision: DecisionPayload
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
# Adapters — translate Pydantic payloads into the duck-typed shape the
# executor consumes (mirroring control_tower.investigation.ProposedAction
# + guardrails.engine.GuardrailDecision).
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


class _TierAdapter:
    def __init__(self, name: str) -> None:
        self.name = name


class _ApprovalAdapter:
    def __init__(self, payload: ApprovalPayload | None) -> None:
        if payload is None:
            self.approved = False
            self.approvers = ()
            self.backend = "none"
            self.reason = None
        else:
            self.approved = payload.approved
            self.approvers = tuple(payload.approvers)
            self.backend = payload.backend
            self.reason = payload.reason


class _PolicyAdapter:
    def __init__(self, payload: PolicyPayload | None) -> None:
        if payload is None:
            self.required_approvals = 0
            self.approver_groups = ()
        else:
            self.required_approvals = payload.required_approvals
            self.approver_groups = tuple(payload.approver_groups)


class _DecisionAdapter:
    def __init__(self, payload: DecisionPayload) -> None:
        self.tier = _TierAdapter(payload.tier)
        self.approved = payload.approved
        self.approval = _ApprovalAdapter(payload.approval)
        self.policy = _PolicyAdapter(payload.policy)
        self.reasons = tuple(payload.reasons)


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
    executor: Executor = Depends(get_executor),
) -> ExecutionResult:
    """Run the full executor pipeline. May refuse, fail, or execute."""
    return executor.execute(
        _ActionAdapter(body.action),
        _DecisionAdapter(body.decision),
        investigation_id=body.investigation_id,
        dry_run=body.dry_run,
    )


@executor_router.post(
    "/dry-run",
    response_model=ExecutionResult,
    summary="Dry-run an action — wrappers report what they would do",
)
def post_dry_run(
    body: ExecuteRequest,
    executor: Executor = Depends(get_executor),
) -> ExecutionResult:
    """Identical to ``/execute`` but ``dry_run`` is forced True."""
    return executor.execute(
        _ActionAdapter(body.action),
        _DecisionAdapter(body.decision),
        investigation_id=body.investigation_id,
        dry_run=True,
    )


@executor_router.get(
    "/audit",
    summary="Recent executor audit rows (newest first)",
)
def get_audit(
    executor: Executor = Depends(get_executor),
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
def get_config(executor: Executor = Depends(get_executor)) -> ConfigView:
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
