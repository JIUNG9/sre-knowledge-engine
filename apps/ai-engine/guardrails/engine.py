"""Guardrails engine — the orchestrator that ties everything together.

One method drives the whole ladder::

    decision = engine.evaluate(action, context, requested_tier)

Internally ``evaluate`` does:

1. Risk assess the action via :class:`guardrails.risk.RiskAssessment`.
2. Run the YAML policy via :meth:`guardrails.policy.GuardrailsPolicy.evaluate`.
3. Pick the effective tier cap (min of requested, ladder cap, policy cap).
4. Short-circuit on outright deny.
5. If the effective tier needs approvals, ask the :class:`ApprovalGate`.
6. **Before** returning ``EXECUTE``, consult the kill switch — if tripped,
   downgrade to ``SUGGEST`` with a clear reason.
7. Write one :class:`AuditRecord`. Always. Even on deny.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .approval import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalResult,
    LocalCLIApprovalGate,
    NoneApprovalGate,
)
from .audit import AuditLogger, AuditRecord
from .policy import GuardrailsPolicy, PolicyDecision
from .risk import Action, RiskAssessment, RiskScore
from .tiers import AutomationTier, tier_cap_for_risk


# Kill-switch dependency is *optional* at import time — the engine works
# fine without a switch wired up (useful for unit tests that don't want to
# stand up Redis). In real deployments, the main app passes a
# ``killswitch_check`` callable that returns ``(active, reason)``.
KillSwitchCheck = Callable[[], "tuple[bool, str | None]"]


def _default_killswitch_check() -> tuple[bool, str | None]:
    """Default kill-switch probe — imports Layer 0.3 lazily."""
    try:
        from killswitch import KillSwitch  # type: ignore[import-not-found]

        status = KillSwitch().status()
        return bool(status.active), getattr(status, "reason", None)
    except Exception:
        # No switch configured or unreachable — fail *open* here so missing
        # infra doesn't permanently block demos. The engine still logs the
        # condition.
        return False, None


@dataclass(frozen=True)
class GuardrailDecision:
    """Final verdict returned by :meth:`GuardrailsEngine.evaluate`."""

    tier: AutomationTier
    approved: bool
    risk: RiskScore
    policy: PolicyDecision
    approval: ApprovalResult | None
    audit: AuditRecord
    reasons: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        """True if the decision resulted in an actionable tier."""
        return self.approved and not self.policy.denied


@dataclass
class GuardrailsEngine:
    """Stateful orchestrator.

    Attributes:
        policy: compiled :class:`GuardrailsPolicy`.
        audit: :class:`AuditLogger`. Required — the engine refuses to run
            without an audit sink, by design.
        approval_gate: default gate used when a tier requires approvals. May
            be overridden per-call via ``approval_gate=`` kwarg on
            :meth:`evaluate`.
        killswitch_check: callable returning ``(active, reason)``. Defaults
            to the real Layer 0.3 switch.
    """

    policy: GuardrailsPolicy
    audit: AuditLogger
    approval_gate: ApprovalGate = field(default_factory=LocalCLIApprovalGate)
    killswitch_check: KillSwitchCheck = field(default=_default_killswitch_check)

    # --------------------- construction helpers ---------------------

    @classmethod
    def from_paths(
        cls,
        *,
        policy_path: str | Path,
        audit_path: str | Path,
        approval_gate: ApprovalGate | None = None,
        killswitch_check: KillSwitchCheck | None = None,
    ) -> "GuardrailsEngine":
        """Convenience constructor — one call to wire everything up."""
        return cls(
            policy=GuardrailsPolicy.load(policy_path),
            audit=AuditLogger(audit_path),
            approval_gate=approval_gate or LocalCLIApprovalGate(),
            killswitch_check=killswitch_check or _default_killswitch_check,
        )

    # --------------------- public API ---------------------

    def evaluate(
        self,
        action: Action,
        context: dict[str, Any] | None = None,
        requested_tier: AutomationTier | str = AutomationTier.SUGGEST,
        *,
        actor: str = "aegis.agent",
        approval_gate: ApprovalGate | None = None,
    ) -> GuardrailDecision:
        """Run the full guardrails pipeline for one action."""
        context = dict(context or {})
        req_tier = AutomationTier.from_str(requested_tier)
        reasons: list[str] = []

        # --- 1) Risk
        risk = RiskAssessment.assess(action, context)
        reasons.extend(risk.reasons)

        # --- 2) Policy
        policy_decision = self.policy.evaluate(action, context)
        # Policy-added risk feeds back into the score so the audit row is honest.
        if policy_decision.added_risk:
            risk = risk.with_additional(
                policy_decision.added_risk,
                f"policy added risk (+{policy_decision.added_risk})",
            )
            reasons.append(f"policy added +{policy_decision.added_risk} risk")
        reasons.extend(policy_decision.reasons)

        # --- 3) Cap tier (ladder floor + policy + request)
        ladder_cap = tier_cap_for_risk(risk.score)
        effective = min(req_tier, ladder_cap, policy_decision.cap_tier)
        if effective < req_tier:
            reasons.append(
                f"capped from {req_tier.name} to {effective.name} "
                f"(ladder={ladder_cap.name}, policy={policy_decision.cap_tier.name})"
            )

        # --- 4) Outright deny
        if policy_decision.denied:
            reasons.append("policy DENY rule matched")
            rec = self._audit(
                action=action,
                actor=actor,
                risk_score=risk.score,
                requested_tier=req_tier,
                decision_tier=AutomationTier.SUGGEST,
                approvals=(),
                outcome="denied",
                reasons=reasons,
                metadata={
                    "matched_rules": list(policy_decision.matched_rule_ids),
                    "blast_radius": action.blast_radius,
                    "reversible": action.reversible,
                },
            )
            return GuardrailDecision(
                tier=AutomationTier.SUGGEST,
                approved=False,
                risk=risk,
                policy=policy_decision,
                approval=None,
                audit=rec,
                reasons=tuple(reasons),
            )

        # --- 5) Approvals
        gate = approval_gate or (
            NoneApprovalGate() if effective == AutomationTier.SUGGEST else self.approval_gate
        )
        required = self._approvals_required(effective, policy_decision)
        approval: ApprovalResult | None = None
        if required > 0:
            approval = gate.request(
                ApprovalRequest(
                    action_name=action.name,
                    tier=effective.name,
                    environment=action.environment,
                    required=required,
                    groups=policy_decision.approver_groups,
                    context=context,
                )
            )
            if not approval.approved:
                reasons.append(
                    f"approval gate '{approval.backend}' did not produce "
                    f"{required} approvals: {approval.reason}"
                )
                rec = self._audit(
                    action=action,
                    actor=actor,
                    risk_score=risk.score,
                    requested_tier=req_tier,
                    decision_tier=AutomationTier.SUGGEST,
                    approvals=approval.approvers,
                    outcome="approval_denied",
                    reasons=reasons,
                )
                return GuardrailDecision(
                    tier=AutomationTier.SUGGEST,
                    approved=False,
                    risk=risk,
                    policy=policy_decision,
                    approval=approval,
                    audit=rec,
                    reasons=tuple(reasons),
                )
        else:
            approval = ApprovalResult(
                approved=True, approvers=(), backend="none",
                reason="no approvals required",
            )

        # --- 6) Kill-switch check is REQUIRED before EXECUTE
        if effective == AutomationTier.EXECUTE:
            active, ks_reason = self.killswitch_check()
            if active:
                reasons.append(
                    f"kill switch ACTIVE ({ks_reason or 'no reason'}); "
                    f"downgrading EXECUTE -> SUGGEST"
                )
                rec = self._audit(
                    action=action,
                    actor=actor,
                    risk_score=risk.score,
                    requested_tier=req_tier,
                    decision_tier=AutomationTier.SUGGEST,
                    approvals=approval.approvers,
                    outcome="killswitch_downgrade",
                    reasons=reasons,
                )
                return GuardrailDecision(
                    tier=AutomationTier.SUGGEST,
                    approved=False,
                    risk=risk,
                    policy=policy_decision,
                    approval=approval,
                    audit=rec,
                    reasons=tuple(reasons),
                )

        # --- 7) Success path — audit + return
        rec = self._audit(
            action=action,
            actor=actor,
            risk_score=risk.score,
            requested_tier=req_tier,
            decision_tier=effective,
            approvals=approval.approvers,
            outcome="approved",
            reasons=reasons,
        )
        return GuardrailDecision(
            tier=effective,
            approved=True,
            risk=risk,
            policy=policy_decision,
            approval=approval,
            audit=rec,
            reasons=tuple(reasons),
        )

    # --------------------- internals ---------------------

    def _approvals_required(
        self, tier: AutomationTier, policy: PolicyDecision
    ) -> int:
        from .tiers import metadata_for

        ladder = metadata_for(tier).requires_approvals
        return max(ladder, policy.required_approvals)

    def _audit(
        self,
        *,
        action: Action,
        actor: str,
        risk_score: int,
        requested_tier: AutomationTier,
        decision_tier: AutomationTier,
        approvals: tuple[str, ...] | list[str],
        outcome: str,
        reasons: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        md = {
            "category": action.category,
            "verb": action.verb,
            "target": action.target,
            "blast_radius": action.blast_radius,
            "reversible": action.reversible,
        }
        if metadata:
            md.update(metadata)
        return self.audit.record(
            actor=actor,
            action=action.name,
            environment=action.environment,
            risk_score=risk_score,
            requested_tier=requested_tier.name,
            decision_tier=decision_tier.name,
            approvals_received=tuple(approvals or ()),
            outcome=outcome,
            reasons=tuple(reasons),
            metadata=md,
        )
