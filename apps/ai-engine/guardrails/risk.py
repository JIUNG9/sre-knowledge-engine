"""Risk assessment — how dangerous is a proposed action?

``RiskAssessment.assess`` takes an :class:`Action` and a context dict and
returns a :class:`RiskScore` in ``[0, 100]`` plus a ladder tier cap. The
engine uses that score in two ways:

1. *Cap* the action at whatever tier the ladder says fits the score (see
   :func:`guardrails.tiers.tier_cap_for_risk`).
2. *Explain* the decision back to the operator — every score ships with a
   list of human-readable reasons so "this got downgraded to PROPOSE" is
   never opaque.

This module is intentionally small and heuristic. Real weights live in the
YAML policy so ops can tune per environment. The scorer here enforces the
floor: prod is never < dev, destructive is never < read-only, IAM/RBAC
always carries a penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .tiers import AutomationTier, tier_cap_for_risk

# Verbs that indicate a destructive / mutating operation. Matched
# case-insensitively against ``Action.verb`` and the lowercased first word
# of ``Action.name``.
DESTRUCTIVE_VERBS: frozenset[str] = frozenset(
    {
        "delete",
        "destroy",
        "drop",
        "remove",
        "terminate",
        "revoke",
        "purge",
        "truncate",
        "rm",
        "rmdir",
        "kill",
        "force-delete",
        "scale-to-zero",
    }
)

# Environments in escalating risk order. Anything not in this table is
# treated as the most restrictive tier (``prod``) to fail safe.
ENV_RISK: dict[str, int] = {
    "sandbox": 0,
    "dev": 5,
    "development": 5,
    "test": 10,
    "qa": 10,
    "staging": 20,
    "stage": 20,
    "preprod": 25,
    "pre-prod": 25,
    "prod": 40,
    "production": 40,
}

# Categories of target resource that carry a permanent risk premium.
# IAM/RBAC/SECRETS are capped at PROPOSE by the default policy — the score
# just explains *why*.
SENSITIVE_CATEGORIES: dict[str, int] = {
    "iam": 30,
    "rbac": 30,
    "secret": 25,
    "secrets": 25,
    "kms": 25,
    "database": 20,
    "db": 20,
    "dns": 20,
    "network": 15,
    "vpc": 15,
    "cloudfront": 15,
    "s3": 15,
    "load-balancer": 10,
    "deployment": 5,
    "pod": 5,
    "configmap": 5,
}


@dataclass(frozen=True)
class Action:
    """A proposed action the agent would like to take.

    Intentionally lightweight — this is the shape we expect every MCP tool
    call to be reducible to before it hits the guardrails. Callers build
    one of these, hand it to :func:`RiskAssessment.assess`, and pass the
    result to :meth:`guardrails.engine.GuardrailsEngine.evaluate`.
    """

    name: str
    verb: str
    target: str
    environment: str = "dev"
    category: str = "deployment"
    blast_radius: int = 1  # how many resources / services affected
    reversible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_destructive(self) -> bool:
        verb = self.verb.strip().lower()
        first = self.name.strip().lower().split(" ", 1)[0] if self.name else ""
        if verb in DESTRUCTIVE_VERBS or first in DESTRUCTIVE_VERBS:
            return True
        # Handle phrases like "scale to 0" / "scale to zero".
        hay = f"{self.name} {self.verb}".lower()
        if "scale" in hay and ("to 0" in hay or "to zero" in hay):
            return True
        return False


@dataclass(frozen=True)
class RiskScore:
    """Output of a risk assessment.

    Attributes:
        score: ``[0, 100]``. Higher = riskier.
        tier_cap: Highest ladder tier the score admits.
        reasons: Ordered, human-readable explanations for each contribution.
    """

    score: int
    tier_cap: AutomationTier
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", max(0, min(100, int(self.score))))

    def with_additional(self, delta: int, reason: str) -> "RiskScore":
        """Return a new :class:`RiskScore` with ``delta`` added."""
        new_score = max(0, min(100, self.score + int(delta)))
        return RiskScore(
            score=new_score,
            tier_cap=tier_cap_for_risk(new_score),
            reasons=tuple(self.reasons) + (reason,),
        )


class RiskAssessment:
    """Stateless risk scorer.

    All methods are classmethods so callers don't need to construct
    anything. The class exists for namespacing + easier mocking in tests.
    """

    @classmethod
    def assess(cls, action: Action, context: dict[str, Any] | None = None) -> RiskScore:
        """Score ``action`` in ``[0, 100]`` and return the matching tier cap.

        The scoring is additive and explainable:

        - Environment penalty (``prod`` > ``stage`` > ``dev``)
        - Category penalty (IAM / RBAC / secrets / DB > plain deployment)
        - Destructive-verb penalty
        - Blast-radius scaling (log-ish, capped at 25)
        - Reversibility penalty (irreversible ops always +10)
        - Context-supplied extras (``context['extra_risk'] = [(+n, reason), ...]``)
        """
        context = context or {}
        reasons: list[str] = []
        score = 0

        # --- environment
        env_key = (action.environment or "").strip().lower()
        if env_key in ENV_RISK:
            penalty = ENV_RISK[env_key]
        else:
            penalty = ENV_RISK["prod"]
            reasons.append(
                f"unknown environment '{action.environment}' treated as prod (+40)"
            )
        score += penalty
        if penalty and env_key in ENV_RISK:
            reasons.append(f"environment={env_key} (+{penalty})")

        # --- category
        cat_key = (action.category or "").strip().lower()
        cat_penalty = SENSITIVE_CATEGORIES.get(cat_key, 0)
        if cat_penalty:
            score += cat_penalty
            reasons.append(f"category={cat_key} (+{cat_penalty})")

        # --- destructive verb
        if action.is_destructive:
            score += 25
            reasons.append(f"destructive verb '{action.verb}' (+25)")

        # --- blast radius — log-ish bucket up to +25
        br = max(0, int(action.blast_radius))
        if br <= 1:
            br_pen = 0
        elif br <= 5:
            br_pen = 5
        elif br <= 20:
            br_pen = 10
        elif br <= 100:
            br_pen = 15
        elif br <= 500:
            br_pen = 20
        else:
            br_pen = 25
        if br_pen:
            score += br_pen
            reasons.append(f"blast_radius={br} (+{br_pen})")

        # --- reversibility
        if not action.reversible:
            score += 10
            reasons.append("action is irreversible (+10)")

        # --- caller-supplied extras
        extras: Iterable[Any] = context.get("extra_risk", ()) or ()
        for item in extras:
            try:
                delta, why = item
            except (TypeError, ValueError):
                continue
            delta = int(delta)
            if delta == 0:
                continue
            score += delta
            sign = "+" if delta > 0 else ""
            reasons.append(f"{why} ({sign}{delta})")

        score = max(0, min(100, score))
        return RiskScore(
            score=score,
            tier_cap=tier_cap_for_risk(score),
            reasons=tuple(reasons),
        )
