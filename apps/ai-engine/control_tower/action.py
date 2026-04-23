"""Convert an LLM action suggestion into a :class:`ProposedAction`.

The control tower never hands raw LLM text to any side-effecting
subsystem. Instead, the LLM is asked to emit a structured action blob
(name, verb, target, environment, category, blast_radius, reversible).
We parse that blob, build a :class:`guardrails.risk.Action`, run it
through :class:`guardrails.engine.GuardrailsEngine`, and finally
render the :class:`guardrails.engine.GuardrailDecision` as a
:class:`ProposedAction` that the API surface can return.

If no action was suggested — or the suggestion was malformed — the
function returns ``None`` and leaves the Investigation unmodified.
"""

from __future__ import annotations

import logging
from typing import Any

from .investigation import ProposedAction

logger = logging.getLogger("aegis.control_tower.action")


def _coerce_action_dict(suggestion: Any) -> dict[str, Any] | None:
    """Return a plain dict if the suggestion looks like one, else None."""
    if not isinstance(suggestion, dict):
        return None
    if not suggestion.get("name") or not suggestion.get("verb"):
        return None
    return {
        "name": str(suggestion.get("name", ""))[:120],
        "verb": str(suggestion.get("verb", ""))[:40],
        "target": str(suggestion.get("target", ""))[:200],
        "environment": str(
            suggestion.get("environment", "prod") or "prod"
        )[:40],
        "category": str(
            suggestion.get("category", "deployment") or "deployment"
        )[:40],
        "blast_radius": int(suggestion.get("blast_radius", 1) or 1),
        "reversible": bool(suggestion.get("reversible", True)),
        "explanation": str(suggestion.get("explanation", ""))[:1000],
        "requested_tier": str(
            suggestion.get("requested_tier", "SUGGEST") or "SUGGEST"
        ),
    }


def propose_action(
    suggestion: Any,
    *,
    guardrails: Any | None,
    context: dict[str, Any] | None = None,
) -> ProposedAction | None:
    """Run ``suggestion`` through the Layer 4 guardrails engine.

    Args:
        suggestion: Dict-like object emitted by Claude. Must contain
            at least ``name`` and ``verb``.
        guardrails: Optional :class:`guardrails.engine.GuardrailsEngine`.
            When ``None``, the function builds a SUGGEST-tier action
            directly — useful for tests and for deployments that
            haven't wired Layer 4 yet.
        context: Optional context dict forwarded to the engine.

    Returns:
        A :class:`ProposedAction`, or ``None`` if the suggestion is
        unparseable.
    """
    parsed = _coerce_action_dict(suggestion)
    if parsed is None:
        return None

    explanation = parsed.pop("explanation", "")
    requested_tier = parsed.pop("requested_tier", "SUGGEST")

    if guardrails is None:
        return ProposedAction(
            name=parsed["name"],
            verb=parsed["verb"],
            target=parsed["target"],
            environment=parsed["environment"],
            category=parsed["category"],
            blast_radius=parsed["blast_radius"],
            reversible=parsed["reversible"],
            tier="SUGGEST",
            approved=False,
            risk_score=0,
            required_approvals=0,
            reasons=["guardrails engine not configured; action left as SUGGEST"],
            approver_groups=[],
            explanation=explanation,
        )

    try:
        from guardrails.risk import Action
    except Exception as exc:  # noqa: BLE001
        logger.warning("guardrails unavailable at import time: %s", exc)
        return ProposedAction(
            name=parsed["name"],
            verb=parsed["verb"],
            target=parsed["target"],
            environment=parsed["environment"],
            category=parsed["category"],
            blast_radius=parsed["blast_radius"],
            reversible=parsed["reversible"],
            tier="SUGGEST",
            approved=False,
            risk_score=0,
            required_approvals=0,
            reasons=[f"guardrails import failed: {exc}"],
            approver_groups=[],
            explanation=explanation,
        )

    action = Action(
        name=parsed["name"],
        verb=parsed["verb"],
        target=parsed["target"],
        environment=parsed["environment"],
        category=parsed["category"],
        blast_radius=parsed["blast_radius"],
        reversible=parsed["reversible"],
    )
    try:
        decision = guardrails.evaluate(
            action,
            context=context or {},
            requested_tier=requested_tier,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("guardrails.evaluate failed: %s", exc)
        return ProposedAction(
            name=parsed["name"],
            verb=parsed["verb"],
            target=parsed["target"],
            environment=parsed["environment"],
            category=parsed["category"],
            blast_radius=parsed["blast_radius"],
            reversible=parsed["reversible"],
            tier="SUGGEST",
            approved=False,
            risk_score=0,
            required_approvals=0,
            reasons=[f"guardrails evaluation error: {exc}"],
            approver_groups=[],
            explanation=explanation,
        )

    # The decision object exposes `tier`, `approved`, `risk`, `policy`,
    # and `reasons` attributes. Each of these may be produced by an
    # older Layer 4 build, so we access them defensively.
    tier = getattr(decision, "tier", None)
    tier_name = getattr(tier, "name", "SUGGEST") if tier is not None else "SUGGEST"
    risk = getattr(decision, "risk", None)
    risk_score = int(getattr(risk, "score", 0) or 0)
    policy = getattr(decision, "policy", None)
    required_approvals = int(getattr(policy, "required_approvals", 0) or 0)
    approver_groups = list(getattr(policy, "approver_groups", ()) or ())
    reasons = list(getattr(decision, "reasons", ()) or ())

    return ProposedAction(
        name=parsed["name"],
        verb=parsed["verb"],
        target=parsed["target"],
        environment=parsed["environment"],
        category=parsed["category"],
        blast_radius=parsed["blast_radius"],
        reversible=parsed["reversible"],
        tier=str(tier_name),
        approved=bool(getattr(decision, "approved", False)),
        risk_score=risk_score,
        required_approvals=required_approvals,
        reasons=reasons,
        approver_groups=approver_groups,
        explanation=explanation,
    )
