"""Executor-level integration tests.

Each test verifies one gate or dispatch path. Tests use the ``FakeAction``
and ``FakeDecision`` doubles from ``conftest.py`` so we don't depend on
the heavier control_tower / guardrails modules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from executor.executor import Executor
from executor.result import ExecutionResult
from executor.tests.conftest import FakeAction, make_decision


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #


def test_execute_kubectl_rollout_restart_with_two_approvals(executor: Executor) -> None:
    """The signature happy path: EXECUTE + 2 approvals + supported verb."""
    action = FakeAction(
        name="restart-payment",
        verb="kubectl rollout-restart",
        target="deployment/payment-svc",
        environment="prod",
        category="kubectl",
    )
    decision = make_decision()

    result = executor.execute(action, decision, investigation_id="inv-1")

    assert result.outcome == "executed"  # dry-run is also "executed"
    assert result.dry_run is True
    assert "rollout restart" in result.stdout
    assert "deployment/payment-svc" in result.stdout
    assert result.audit_id is not None


def test_execute_records_audit_id_on_success(executor: Executor) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision, investigation_id="inv-2")

    assert result.audit_id is not None
    assert result.investigation_id == "inv-2"


def test_dry_run_does_not_invoke_subprocess(make_executor) -> None:
    """Dry-run mode never invokes the binary, returns argv as stdout."""
    executor = make_executor(dry_run_default=True)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.dry_run is True
    assert result.exit_code == 0
    assert result.stdout.startswith("kubectl ")


def test_caller_can_force_dry_run_off_via_argument(make_executor) -> None:
    """When the caller passes ``dry_run=False`` we honour it (subject
    to wrappers — kubectl might not be on PATH in CI, in which case
    the result is ``failed``, but it's NOT dry-run)."""
    executor = make_executor(dry_run_default=True)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision, dry_run=False)

    assert result.dry_run is False
    # outcome may be 'executed' or 'failed' depending on whether
    # kubectl is on PATH; both are valid (gate did not refuse).
    assert result.outcome in ("executed", "failed")


# --------------------------------------------------------------------------- #
# Gate 1: config disabled
# --------------------------------------------------------------------------- #


def test_executor_disabled_refuses_everything(make_executor) -> None:
    executor = make_executor(enabled=False)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason == "executor_disabled"


# --------------------------------------------------------------------------- #
# Gate 2: tier
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tier", ["SUGGEST", "DRAFT", "PROPOSE"])
def test_non_execute_tiers_refused(executor: Executor, tier: str) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision(tier=tier)

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason == "not_approved_for_execution"


# --------------------------------------------------------------------------- #
# Gate 3: approvals
# --------------------------------------------------------------------------- #


def test_zero_approvals_refused(executor: Executor) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision(approvers=(), required=2, approved=False)

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason in (
        "approval_gate_not_satisfied",
        "insufficient_approvals",
        "execute_requires_two_approvals",
    )


def test_one_approval_refused_when_two_required(executor: Executor) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision(approvers=("alice",), required=2)

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason == "insufficient_approvals"


def test_two_approval_floor_independent_of_policy(make_executor) -> None:
    """Even if policy says 1 is enough, the executor floor demands 2."""
    executor = make_executor(require_two=True)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision(approvers=("alice",), required=1)

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason == "execute_requires_two_approvals"


def test_two_approval_floor_can_be_disabled(make_executor) -> None:
    """Operators can disable the executor's two-approval floor."""
    executor = make_executor(require_two=False)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision(approvers=("alice",), required=1)

    result = executor.execute(action, decision)

    assert result.outcome == "executed"


# --------------------------------------------------------------------------- #
# Gate 4: verb / wrapper
# --------------------------------------------------------------------------- #


def test_kubectl_delete_default_blocked(executor: Executor) -> None:
    """kubectl delete is in blocked_verbs — refused permanently."""
    action = FakeAction(verb="kubectl delete", target="deployment/x")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and result.refused_reason.startswith(
        "verb_permanently_blocked"
    )


def test_terraform_destroy_not_loadable(executor: Executor) -> None:
    """terraform destroy is in blocked_verbs of the terraform wrapper."""
    action = FakeAction(
        verb="terraform destroy",
        target="acme-corp-prod",
        category="terraform",
    )
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and result.refused_reason.startswith(
        "verb_permanently_blocked"
    )


def test_unknown_verb_refused(executor: Executor) -> None:
    action = FakeAction(verb="kubectl warp-drive", target="cluster/foo")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and result.refused_reason.startswith(
        "verb_not_supported"
    )


def test_verb_not_in_config_allow_list_refused(make_executor) -> None:
    executor = make_executor(
        allowed_verbs={
            "kubectl": ["get"],  # describe NOT in allow-list
            "terraform": ["plan"],
            "aws": [],
        }
    )
    action = FakeAction(verb="kubectl describe", target="pods/foo")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and result.refused_reason.startswith(
        "verb_not_in_allow_list"
    )


def test_terraform_apply_blocked_without_explicit_opt_in(make_executor) -> None:
    executor = make_executor(terraform_apply_allowed=False)
    action = FakeAction(
        verb="terraform apply",
        target="acme-corp-prod",
        category="terraform",
    )
    decision = make_decision()

    result = executor.execute(action, decision)

    # Apply is in supported_verbs but the wrapper raises WrapperError when
    # apply_allowed=False, so the wrapper returns a refusal.
    assert result.outcome in ("refused", "failed")
    if result.outcome == "refused":
        assert result.refused_reason


def test_aws_iam_blocked_permanently(executor: Executor) -> None:
    action = FakeAction(
        verb="create-role",
        target="iam",
        category="aws",
    )
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"


# --------------------------------------------------------------------------- #
# Gate 5: kill switch (LAST defense)
# --------------------------------------------------------------------------- #


def test_kill_switch_active_refuses_at_last_mile(make_executor) -> None:
    executor = make_executor(killswitch_check=lambda: (True, "incident_in_progress"))
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and result.refused_reason.startswith(
        "killswitch_active"
    )


def test_kill_switch_probe_failure_fails_closed(make_executor) -> None:
    """If we cannot probe the kill switch, the executor refuses (fail-closed)."""

    def _broken() -> tuple[bool, str | None]:
        raise RuntimeError("redis down")

    executor = make_executor(killswitch_check=_broken)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = executor.execute(action, decision)

    assert result.outcome == "refused"
    assert result.refused_reason and "killswitch" in result.refused_reason


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #


def test_audit_record_appended_on_execute(executor: Executor, audit_path: Path) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()
    executor.execute(action, decision, investigation_id="inv-audit-1")

    assert audit_path.exists()
    rows = [
        json.loads(line) for line in audit_path.read_text().splitlines() if line
    ]
    assert len(rows) == 1
    assert rows[0]["outcome"] == "executed"
    assert rows[0]["investigation_id"] == "inv-audit-1"
    assert "stdout_hash" in rows[0]
    assert "stderr_hash" in rows[0]


def test_audit_record_appended_on_refusal(make_executor, audit_path: Path) -> None:
    executor = make_executor(enabled=False)
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()
    executor.execute(action, decision, investigation_id="inv-r-1")

    rows = [
        json.loads(line) for line in audit_path.read_text().splitlines() if line
    ]
    assert len(rows) == 1
    assert rows[0]["outcome"] == "refused"
    assert rows[0]["refused_reason"] == "executor_disabled"


def test_idempotent_audit_for_same_investigation_action(
    executor: Executor, audit_path: Path
) -> None:
    """Same (investigation_id, action) is deduped within one process."""
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()
    executor.execute(action, decision, investigation_id="inv-dup")
    executor.execute(action, decision, investigation_id="inv-dup")

    rows = [
        json.loads(line) for line in audit_path.read_text().splitlines() if line
    ]
    # Only one durable row (the second call returned a stub).
    assert len(rows) == 1


# --------------------------------------------------------------------------- #
# Wrapper exception propagation
# --------------------------------------------------------------------------- #


def test_wrapper_exception_does_not_crash_executor(make_executor) -> None:
    from executor.wrappers.base import Wrapper, WrapperError

    class ExplodingWrapper(Wrapper):
        name = "kubectl"
        supported_verbs = frozenset({"get"})
        blocked_verbs = frozenset()

        def build_args(self, action):  # type: ignore[override]
            raise RuntimeError("kaboom")

    cfg_executor = make_executor()
    cfg_executor.wrappers["kubectl"] = ExplodingWrapper()

    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()

    result = cfg_executor.execute(action, decision)
    # WrapperError handled gracefully -> failed outcome with stderr.
    assert result.outcome == "failed"
    assert "kaboom" in result.stderr
    _ = WrapperError  # keep import used


# --------------------------------------------------------------------------- #
# ExecutionResult shape
# --------------------------------------------------------------------------- #


def test_result_is_pydantic_serializable(executor: Executor) -> None:
    action = FakeAction(verb="kubectl get", target="pods/all")
    decision = make_decision()
    result = executor.execute(action, decision, investigation_id="inv-p")

    payload = result.model_dump()
    assert payload["outcome"] in ("executed", "failed", "refused")
    # Roundtrip
    assert ExecutionResult.model_validate(payload).outcome == result.outcome
