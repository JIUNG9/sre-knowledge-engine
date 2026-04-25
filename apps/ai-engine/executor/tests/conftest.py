"""Shared pytest fixtures + helpers for the executor test suite."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# Ensure ``from executor.x import ...`` resolves to apps/ai-engine.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))

from executor.audit import AuditLogger  # noqa: E402
from executor.config import ExecutorConfig  # noqa: E402
from executor.executor import Executor  # noqa: E402


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #


@dataclass
class FakeAction:
    """Duck-typed substitute for ProposedAction."""

    name: str = "test-action"
    verb: str = "get"
    target: str = "deployment/payment-svc"
    environment: str = "staging"
    category: str = "kubectl"
    blast_radius: int = 1
    reversible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeTier:
    name: str = "EXECUTE"


@dataclass
class FakeApproval:
    approved: bool = True
    approvers: tuple[str, ...] = ("june", "alice")
    backend: str = "test"
    reason: str | None = None


@dataclass
class FakePolicy:
    required_approvals: int = 2
    approver_groups: tuple[str, ...] = ("sre",)


@dataclass
class FakeDecision:
    tier: FakeTier = field(default_factory=lambda: FakeTier(name="EXECUTE"))
    approved: bool = True
    approval: FakeApproval = field(default_factory=FakeApproval)
    policy: FakePolicy = field(default_factory=FakePolicy)
    reasons: tuple[str, ...] = ()


def make_decision(
    *,
    tier: str = "EXECUTE",
    approvers: tuple[str, ...] = ("june", "alice"),
    required: int = 2,
    approved: bool = True,
) -> FakeDecision:
    return FakeDecision(
        tier=FakeTier(name=tier),
        approved=approved,
        approval=FakeApproval(approved=approved, approvers=approvers),
        policy=FakePolicy(required_approvals=required),
    )


# --------------------------------------------------------------------------- #
# Executor fixture
# --------------------------------------------------------------------------- #


@pytest.fixture
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "executor-audit.jsonl"


@pytest.fixture
def killswitch_clear() -> Any:
    return lambda: (False, None)


@pytest.fixture
def killswitch_tripped() -> Any:
    return lambda: (True, "manual_trip_for_test")


@pytest.fixture
def make_executor(audit_path: Path, killswitch_clear: Any):
    """Factory fixture for Executor with overridable knobs."""

    def _factory(
        *,
        enabled: bool = True,
        dry_run_default: bool = True,
        terraform_apply_allowed: bool = False,
        require_two: bool = True,
        killswitch_check: Any | None = None,
        allowed_verbs: dict[str, list[str]] | None = None,
    ) -> Executor:
        config = ExecutorConfig(
            enabled=enabled,
            dry_run_default=dry_run_default,
            allowed_verbs=allowed_verbs
            or {
                "kubectl": [
                    "scale",
                    "rollout-restart",
                    "get",
                    "describe",
                    "logs",
                ],
                "terraform": ["plan", "apply"],
                "aws": ["describe-instances", "list-buckets", "get-object"],
            },
            terraform_apply_allowed=terraform_apply_allowed,
            audit_log_path=str(audit_path),
            require_two_approvals_for_execute=require_two,
        )
        executor = Executor(
            config=config,
            audit=AuditLogger(audit_path),
            killswitch_check=killswitch_check or killswitch_clear,
        )
        return executor

    return _factory


@pytest.fixture
def executor(make_executor) -> Executor:
    """Default executor: enabled, dry-run on, kill switch clear."""
    return make_executor()
