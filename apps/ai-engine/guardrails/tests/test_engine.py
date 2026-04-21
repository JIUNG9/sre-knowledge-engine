"""End-to-end engine tests — one ``evaluate`` call must orchestrate everything."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from guardrails.approval import (
    ApprovalRequest,
    ApprovalResult,
    ApprovalGate,
    LocalCLIApprovalGate,
)
from guardrails.audit import AuditLogger
from guardrails.engine import GuardrailsEngine
from guardrails.policy import GuardrailsPolicy
from guardrails.risk import Action
from guardrails.tiers import AutomationTier

from .conftest import DEFAULT_POLICY_PATH, TEST_POLICY_PATH


class _AlwaysYes(ApprovalGate):
    backend = "always-yes"

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        return ApprovalResult(
            approved=True,
            approvers=tuple(f"bot-{i}" for i in range(req.required)),
            backend=self.backend,
        )


class _AlwaysNo(ApprovalGate):
    backend = "always-no"

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        return ApprovalResult(
            approved=False,
            approvers=(),
            backend=self.backend,
            reason="never approves",
        )


def _engine(tmp_path: Path, *, policy=None, gate=None, ks=lambda: (False, None)):
    policy = policy or GuardrailsPolicy.load(TEST_POLICY_PATH)
    audit = AuditLogger(tmp_path / "audit.jsonl")
    return GuardrailsEngine(
        policy=policy,
        audit=audit,
        approval_gate=gate or _AlwaysYes(),
        killswitch_check=ks,
    )


def _action(**overrides):
    base = dict(
        name="restart pod",
        verb="restart",
        target="payment-svc",
        environment="dev",
        category="deployment",
        blast_radius=1,
        reversible=True,
    )
    base.update(overrides)
    return Action(**base)


def test_suggest_tier_never_needs_approvals(tmp_path: Path):
    engine = _engine(tmp_path)
    dec = engine.evaluate(
        _action(), requested_tier=AutomationTier.SUGGEST
    )
    assert dec.tier == AutomationTier.SUGGEST
    assert dec.approved
    assert dec.approval is not None
    assert dec.approval.approvers == ()


def test_dev_execute_succeeds(tmp_path: Path):
    engine = _engine(tmp_path)
    dec = engine.evaluate(
        _action(),
        requested_tier=AutomationTier.EXECUTE,
        actor="june",
    )
    assert dec.tier == AutomationTier.EXECUTE
    assert dec.approved


def test_prod_execute_requires_two_approvals(tmp_path: Path):
    engine = _engine(tmp_path, gate=_AlwaysNo())
    dec = engine.evaluate(
        _action(environment="prod"),
        requested_tier=AutomationTier.EXECUTE,
    )
    # Always-no gate => downgraded to SUGGEST
    assert dec.tier == AutomationTier.SUGGEST
    assert dec.approved is False


def test_iam_action_capped_at_propose(tmp_path: Path):
    engine = _engine(tmp_path)
    dec = engine.evaluate(
        _action(category="iam", verb="attach-policy", name="attach admin"),
        requested_tier=AutomationTier.EXECUTE,
    )
    assert dec.tier <= AutomationTier.PROPOSE


def test_scale_to_zero_in_prod_is_gated_heavily(tmp_path: Path):
    """The worked example: scale deployment X to 0 in prod.

    Expected path: destructive verb -> prod-destructive rule caps PROPOSE,
    risk score pushes ladder cap to PROPOSE or lower, needs >= 2 approvals.
    """
    engine = _engine(tmp_path)
    action = _action(
        name="scale deployment X to 0",
        verb="scale-to-zero",
        environment="prod",
        blast_radius=1,
    )
    dec = engine.evaluate(
        action,
        requested_tier=AutomationTier.EXECUTE,
        actor="june",
    )
    assert dec.tier <= AutomationTier.PROPOSE
    # Prod rule mandates 2 approvers
    assert dec.policy.required_approvals >= 2


def test_deny_rule_produces_suggest_and_not_approved(tmp_path: Path):
    engine = _engine(tmp_path)
    action = _action(
        name="drop users table",
        verb="drop",
        environment="prod",
        category="database",
    )
    dec = engine.evaluate(action, requested_tier=AutomationTier.EXECUTE)
    assert dec.tier == AutomationTier.SUGGEST
    assert dec.approved is False
    assert dec.policy.denied is True


def test_killswitch_downgrades_execute(tmp_path: Path):
    engine = _engine(
        tmp_path,
        ks=lambda: (True, "pagerduty SEV1"),
    )
    dec = engine.evaluate(
        _action(environment="dev"),
        requested_tier=AutomationTier.EXECUTE,
    )
    assert dec.tier == AutomationTier.SUGGEST
    assert dec.approved is False
    assert any("kill switch" in r.lower() for r in dec.reasons)


def test_killswitch_does_not_affect_propose(tmp_path: Path):
    engine = _engine(
        tmp_path,
        ks=lambda: (True, "tripped"),
    )
    dec = engine.evaluate(
        _action(environment="dev"),
        requested_tier=AutomationTier.PROPOSE,
    )
    # Kill switch only checked for EXECUTE; PROPOSE should proceed.
    assert dec.tier == AutomationTier.PROPOSE
    assert dec.approved is True


def test_audit_log_appends_one_record(tmp_path: Path):
    engine = _engine(tmp_path)
    engine.evaluate(_action(), requested_tier=AutomationTier.SUGGEST)
    engine.evaluate(_action(), requested_tier=AutomationTier.EXECUTE)
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        rec = json.loads(line)
        assert "timestamp" in rec
        assert rec["action"] == "restart pod"


def test_audit_log_is_append_only_across_concurrent_calls(tmp_path: Path):
    engine = _engine(tmp_path)
    errors: list[BaseException] = []

    def worker():
        try:
            for _ in range(20):
                engine.evaluate(
                    _action(), requested_tier=AutomationTier.EXECUTE, actor="t"
                )
        except BaseException as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 4 * 20
    # Every line must be valid JSON (no interleaved writes).
    for line in lines:
        json.loads(line)


def test_default_policy_loads_and_evaluates(tmp_path: Path):
    policy = GuardrailsPolicy.load(DEFAULT_POLICY_PATH)
    engine = _engine(tmp_path, policy=policy)
    dec = engine.evaluate(
        _action(
            name="scale deployment payments to 0",
            verb="scale-to-zero",
            environment="prod",
            category="deployment",
            blast_radius=10,
        ),
        requested_tier=AutomationTier.EXECUTE,
    )
    # Default policy caps scale-to-zero in prod at DRAFT
    assert dec.tier <= AutomationTier.DRAFT


def test_engine_rejects_unknown_tier_string(tmp_path: Path):
    engine = _engine(tmp_path)
    with pytest.raises(ValueError):
        engine.evaluate(_action(), requested_tier="YOLO")


def test_local_cli_gate_integrates_with_engine(tmp_path: Path):
    engine = _engine(
        tmp_path,
        gate=LocalCLIApprovalGate(prompt=lambda m: True, user=lambda: "demo"),
    )
    dec = engine.evaluate(
        _action(environment="prod", blast_radius=1),
        requested_tier=AutomationTier.EXECUTE,
    )
    # prod caps at 2 approvers via test policy
    assert dec.approved is True
    assert all(a.startswith("cli:demo") for a in dec.approval.approvers)
