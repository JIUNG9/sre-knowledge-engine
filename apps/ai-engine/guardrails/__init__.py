"""Aegis Guardrails — Layer 4.

Public API:

* :class:`GuardrailsEngine` — orchestrator; one ``.evaluate()`` call per action.
* :class:`AutomationTier` — the 4-rung ladder (SUGGEST < DRAFT < PROPOSE < EXECUTE).
* :class:`RiskAssessment` / :class:`RiskScore` — action scoring.
* :class:`GuardrailsPolicy` — YAML-driven rule evaluator.
* :class:`ApprovalGate` (+ Slack / GitHub / CLI / None implementations).
* :class:`AuditLogger` / :class:`AuditRecord` — append-only JSONL audit.
* :class:`GuardrailDecision` — final verdict returned by the engine.

Design goals:

* Policies are **data**, not code. The YAML file is the source of truth.
* Audit records are **append-only** — never rewritten after write.
* The kill switch is consulted **before** ``EXECUTE`` is returned — if
  tripped, the decision is downgraded to ``SUGGEST``.
* Thread-safe: concurrent ``evaluate()`` calls never corrupt the audit log.
"""

from __future__ import annotations

from .approval import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalResult,
    GithubApprovalGate,
    LocalCLIApprovalGate,
    NoneApprovalGate,
    SlackApprovalGate,
)
from .audit import AuditLogger, AuditRecord
from .engine import GuardrailDecision, GuardrailsEngine
from .policy import (
    GuardrailsPolicy,
    PolicyDecision,
    PolicyEffect,
    PolicyRule,
    PolicyValidationError,
)
from .risk import Action, RiskAssessment, RiskScore
from .tiers import (
    TIER_METADATA,
    AutomationTier,
    TierMetadata,
    metadata_for,
    tier_cap_for_risk,
)

__all__ = [
    # tiers
    "AutomationTier",
    "TierMetadata",
    "TIER_METADATA",
    "metadata_for",
    "tier_cap_for_risk",
    # risk
    "Action",
    "RiskAssessment",
    "RiskScore",
    # policy
    "GuardrailsPolicy",
    "PolicyDecision",
    "PolicyEffect",
    "PolicyRule",
    "PolicyValidationError",
    # approvals
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalResult",
    "LocalCLIApprovalGate",
    "NoneApprovalGate",
    "SlackApprovalGate",
    "GithubApprovalGate",
    # audit
    "AuditLogger",
    "AuditRecord",
    # engine
    "GuardrailsEngine",
    "GuardrailDecision",
]
