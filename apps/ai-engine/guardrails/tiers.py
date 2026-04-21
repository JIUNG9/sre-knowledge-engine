"""Automation tiers — the 4-rung ladder that gates every Aegis action.

Aegis never "just does things". Every action proposed by an agent is mapped
to one of four tiers below. The tier determines:

* whether anything side-effecting happens at all,
* what artifact (if any) is produced,
* which approval gate(s) must be satisfied, and
* how loud the audit record is.

The ladder is intentionally monotonic: ``SUGGEST < DRAFT < PROPOSE < EXECUTE``.
A policy can *downgrade* a requested tier (e.g. "this IAM change is capped at
``PROPOSE``") but never silently *upgrade* it. Upgrades require an explicit
approval flow.

Metadata on each tier is consulted by :mod:`guardrails.engine` and
:mod:`guardrails.policy`. It is NOT hardcoded business policy — it is the
minimum floor. Real risk/approval thresholds come from YAML policy files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class AutomationTier(IntEnum):
    """The 4 rungs of the automation ladder.

    Ordering is significant: higher int = more side effects. This lets the
    engine write clean comparisons like ``decision.tier <= policy.tier_cap``.
    """

    SUGGEST = 0  # propose an action, do nothing automatically
    DRAFT = 1  # create an artifact (ticket/PR comment/Slack draft), do not send
    PROPOSE = 2  # execute against dry-run / plan-only endpoint
    EXECUTE = 3  # run the real action (still audited + kill-switch checked)

    @property
    def label(self) -> str:
        return self.name

    @classmethod
    def from_str(cls, value: str | "AutomationTier") -> "AutomationTier":
        """Parse a tier from an arbitrary string (case-insensitive)."""
        if isinstance(value, AutomationTier):
            return value
        if not isinstance(value, str):
            raise TypeError(f"cannot coerce {type(value).__name__} to AutomationTier")
        try:
            return cls[value.strip().upper()]
        except KeyError as exc:
            raise ValueError(
                f"unknown automation tier '{value}'. "
                f"Valid: {', '.join(t.name for t in cls)}"
            ) from exc


@dataclass(frozen=True)
class TierMetadata:
    """Static metadata about a tier.

    Attributes:
        tier: The :class:`AutomationTier` this metadata describes.
        max_risk_score: Soft ceiling on the risk score a tier can carry
            before policy must downgrade it. This is the LADDER default —
            individual policies can tighten it further but not loosen it.
        requires_approvals: Minimum number of human approvals the ladder
            mandates at this tier, before any policy overrides.
        audit_level: ``low`` / ``medium`` / ``high``. Drives how much
            context the audit logger captures.
        description: Human-readable description used in READMEs and UIs.
    """

    tier: AutomationTier
    max_risk_score: int
    requires_approvals: int
    audit_level: str
    description: str
    extra: dict[str, Any] = field(default_factory=dict)

    def allows_risk(self, score: int) -> bool:
        """Return ``True`` if ``score`` fits under this tier's ceiling."""
        return score <= self.max_risk_score


# The ladder floor. Policies may tighten but not loosen these.
#
#   SUGGEST  — always safe, no approval ever.
#   DRAFT    — creating an artifact can still leak info; one approval.
#   PROPOSE  — plan-only execution can still hit rate limits / APIs; one approval.
#   EXECUTE  — real action, two approvals by default (can be tightened
#              further to "prod-only requires two", etc. in YAML).
#
# The risk-score ceilings are the *maximum* score a tier may carry. A risk
# assessment higher than the ceiling forces a downgrade.
TIER_METADATA: dict[AutomationTier, TierMetadata] = {
    AutomationTier.SUGGEST: TierMetadata(
        tier=AutomationTier.SUGGEST,
        max_risk_score=100,
        requires_approvals=0,
        audit_level="low",
        description="Propose the action to a human; take no side effects.",
    ),
    AutomationTier.DRAFT: TierMetadata(
        tier=AutomationTier.DRAFT,
        max_risk_score=80,
        requires_approvals=1,
        audit_level="medium",
        description=(
            "Produce an artifact (ticket, PR comment, Slack draft) but do "
            "not transmit / merge / send it."
        ),
    ),
    AutomationTier.PROPOSE: TierMetadata(
        tier=AutomationTier.PROPOSE,
        max_risk_score=60,
        requires_approvals=1,
        audit_level="medium",
        description=(
            "Run against a dry-run or plan-only endpoint and surface the "
            "result (terraform plan, kubectl --dry-run=server, etc.)."
        ),
    ),
    AutomationTier.EXECUTE: TierMetadata(
        tier=AutomationTier.EXECUTE,
        max_risk_score=40,
        requires_approvals=2,
        audit_level="high",
        description=(
            "Perform the real action. Still subject to kill switch + audit."
        ),
    ),
}


def metadata_for(tier: AutomationTier) -> TierMetadata:
    """Return the :class:`TierMetadata` for ``tier``."""
    return TIER_METADATA[tier]


def tier_cap_for_risk(score: int) -> AutomationTier:
    """Return the highest ladder tier whose ceiling admits ``score``.

    This is the ladder-level default cap. Policies may tighten it further,
    never loosen it. Scores are clamped to ``[0, 100]``.
    """
    clamped = max(0, min(100, int(score)))
    # Walk high -> low and pick the most permissive tier whose ceiling holds.
    for tier in (
        AutomationTier.EXECUTE,
        AutomationTier.PROPOSE,
        AutomationTier.DRAFT,
        AutomationTier.SUGGEST,
    ):
        if TIER_METADATA[tier].allows_risk(clamped):
            return tier
    return AutomationTier.SUGGEST  # unreachable — SUGGEST ceiling is 100
