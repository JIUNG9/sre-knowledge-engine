"""YAML-driven policy engine.

Policy files define the *organisational* rules that sit above the ladder
floor. A single policy is a list of rules; each rule has a ``match`` block
(which actions it applies to) and an ``effect`` block (what to do when it
matches).

Rules are data-driven — the engine code never hardcodes thresholds. Every
rule type here maps to a single dispatchable handler so rules compose: a
single action can pick up multiple ``require_approvals`` bumps, be forced
to ``cap_tier: PROPOSE``, AND be blocked by a ``never_execute`` sentinel.

A rule shape::

    - id: prod-requires-two-approvals
      description: "Any action targeting prod needs 2 approvals."
      match:
        environment: prod
      effect:
        require_approvals: 2

    - id: iam-never-execute
      match:
        category: [iam, rbac]
      effect:
        cap_tier: PROPOSE

    - id: destructive-prod-block
      match:
        environment: prod
        destructive: true
      effect:
        cap_tier: PROPOSE
        reason: "destructive ops capped at PROPOSE in prod"

    - id: after-hours-needs-oncall
      match:
        after_hours: true
      effect:
        require_approvals: 1
        approver_group: oncall

The loader validates structure; unknown match/effect keys raise
:class:`PolicyValidationError` up front rather than silently passing.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .risk import Action
from .tiers import AutomationTier


class PolicyValidationError(ValueError):
    """Raised when a YAML policy file has a structural problem."""


# Keys allowed inside a rule ``match`` block. Unknown keys => validation
# error. Kept as a module-level set for easy discoverability.
_MATCH_KEYS: frozenset[str] = frozenset(
    {
        "environment",
        "category",
        "verb",
        "destructive",
        "target",
        "reversible",
        "after_hours",
        "blast_radius_gte",
        "any",
    }
)

_EFFECT_KEYS: frozenset[str] = frozenset(
    {
        "cap_tier",
        "require_approvals",
        "approver_group",
        "deny",
        "reason",
        "add_risk",
    }
)


@dataclass(frozen=True)
class PolicyEffect:
    """Resolved effect of one rule matching one action."""

    cap_tier: AutomationTier | None = None
    require_approvals: int = 0
    approver_groups: tuple[str, ...] = ()
    deny: bool = False
    reason: str | None = None
    add_risk: int = 0


@dataclass(frozen=True)
class PolicyRule:
    """A single compiled policy rule."""

    id: str
    description: str
    match: dict[str, Any]
    effect: dict[str, Any]

    def applies(self, action: Action, context: dict[str, Any]) -> bool:
        """Return ``True`` if this rule matches the action + context."""
        return _match(self.match, action, context)

    def resolve(self) -> PolicyEffect:
        """Turn the raw effect dict into a typed :class:`PolicyEffect`."""
        raw = self.effect
        cap = raw.get("cap_tier")
        cap_tier = AutomationTier.from_str(cap) if cap is not None else None
        groups_raw = raw.get("approver_group")
        if groups_raw is None:
            groups: tuple[str, ...] = ()
        elif isinstance(groups_raw, str):
            groups = (groups_raw,)
        else:
            groups = tuple(str(g) for g in groups_raw)
        return PolicyEffect(
            cap_tier=cap_tier,
            require_approvals=int(raw.get("require_approvals", 0)),
            approver_groups=groups,
            deny=bool(raw.get("deny", False)),
            reason=raw.get("reason") or self.description or self.id,
            add_risk=int(raw.get("add_risk", 0)),
        )


@dataclass(frozen=True)
class PolicyDecision:
    """Combined outcome of evaluating all rules for one action."""

    cap_tier: AutomationTier
    required_approvals: int
    approver_groups: tuple[str, ...]
    denied: bool
    added_risk: int
    matched_rule_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass
class GuardrailsPolicy:
    """A compiled, ready-to-evaluate policy."""

    rules: list[PolicyRule]
    source_path: Path | None = None
    after_hours_start: int = 18  # 18:00
    after_hours_end: int = 8  # 08:00

    # ---------------------- loading ----------------------

    @classmethod
    def load(cls, path: str | Path) -> "GuardrailsPolicy":
        """Load a policy file from disk."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"policy file not found: {p}")
        data = yaml.safe_load(p.read_text()) or {}
        return cls.from_dict(data, source_path=p)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, source_path: Path | None = None
    ) -> "GuardrailsPolicy":
        """Compile a raw dict (typically from YAML) into a policy."""
        if not isinstance(data, dict):
            raise PolicyValidationError("policy root must be a mapping")

        raw_rules: Iterable[Any] = data.get("rules", []) or []
        if not isinstance(raw_rules, list):
            raise PolicyValidationError("'rules' must be a list")

        compiled: list[PolicyRule] = []
        seen_ids: set[str] = set()
        for idx, raw in enumerate(raw_rules):
            if not isinstance(raw, dict):
                raise PolicyValidationError(f"rule[{idx}] must be a mapping")
            rid = raw.get("id")
            if not rid:
                raise PolicyValidationError(f"rule[{idx}] missing 'id'")
            if rid in seen_ids:
                raise PolicyValidationError(f"duplicate rule id '{rid}'")
            seen_ids.add(rid)

            match = raw.get("match", {}) or {}
            effect = raw.get("effect", {}) or {}
            if not isinstance(match, dict):
                raise PolicyValidationError(f"rule '{rid}': match must be a mapping")
            if not isinstance(effect, dict):
                raise PolicyValidationError(f"rule '{rid}': effect must be a mapping")

            bad_match = set(match.keys()) - _MATCH_KEYS
            if bad_match:
                raise PolicyValidationError(
                    f"rule '{rid}': unknown match keys: {sorted(bad_match)}"
                )
            bad_effect = set(effect.keys()) - _EFFECT_KEYS
            if bad_effect:
                raise PolicyValidationError(
                    f"rule '{rid}': unknown effect keys: {sorted(bad_effect)}"
                )

            cap = effect.get("cap_tier")
            if cap is not None:
                # Validate early so a bad policy fails load, not evaluate.
                AutomationTier.from_str(cap)

            compiled.append(
                PolicyRule(
                    id=str(rid),
                    description=str(raw.get("description", "")),
                    match=match,
                    effect=effect,
                )
            )

        cfg = data.get("config", {}) or {}
        ahs = int(cfg.get("after_hours_start", 18))
        ahe = int(cfg.get("after_hours_end", 8))
        return cls(
            rules=compiled,
            source_path=source_path,
            after_hours_start=ahs,
            after_hours_end=ahe,
        )

    # ---------------------- evaluation ----------------------

    def evaluate(
        self,
        action: Action,
        context: dict[str, Any] | None = None,
        *,
        now: _dt.datetime | None = None,
    ) -> PolicyDecision:
        """Walk all rules, collect their effects, produce a decision.

        Effects compose as follows:

        - ``cap_tier``: the *lowest* cap across all matched rules wins.
        - ``require_approvals``: the *maximum* required count wins.
        - ``approver_group``: the union of all matched groups.
        - ``deny``: any matched deny wins.
        - ``add_risk``: summed across matched rules.
        - ``reason``: each matched rule contributes one reason string.
        """
        ctx = dict(context or {})
        ctx.setdefault("after_hours", self._is_after_hours(now))

        cap: AutomationTier = AutomationTier.EXECUTE
        approvals = 0
        groups: list[str] = []
        denied = False
        add_risk = 0
        ids: list[str] = []
        reasons: list[str] = []

        for rule in self.rules:
            if not rule.applies(action, ctx):
                continue
            eff = rule.resolve()
            ids.append(rule.id)
            if eff.cap_tier is not None and eff.cap_tier < cap:
                cap = eff.cap_tier
            if eff.require_approvals > approvals:
                approvals = eff.require_approvals
            for g in eff.approver_groups:
                if g not in groups:
                    groups.append(g)
            if eff.deny:
                denied = True
            add_risk += eff.add_risk
            if eff.reason:
                reasons.append(f"[{rule.id}] {eff.reason}")

        return PolicyDecision(
            cap_tier=cap,
            required_approvals=approvals,
            approver_groups=tuple(groups),
            denied=denied,
            added_risk=add_risk,
            matched_rule_ids=tuple(ids),
            reasons=tuple(reasons),
        )

    # ---------------------- helpers ----------------------

    def _is_after_hours(self, now: _dt.datetime | None) -> bool:
        t = (now or _dt.datetime.now()).time().hour
        start = self.after_hours_start
        end = self.after_hours_end
        if start == end:
            return False
        if start < end:
            # Daytime window defined by [start, end); anything outside = after hours
            return not (start <= t < end)
        # Wraparound window: [start..24) or [0..end)
        return t >= start or t < end


# --------------------------------------------------------------------------
# Matching primitives — small enough to stay in this module, data-driven.
# --------------------------------------------------------------------------

def _as_iterable(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def _match(block: dict[str, Any], action: Action, context: dict[str, Any]) -> bool:
    """Evaluate one rule ``match`` block against ``action`` + ``context``."""
    for key, expected in block.items():
        if key == "any":
            # any: list of sub-match-blocks, OR semantics.
            if not isinstance(expected, list):
                return False
            if not any(_match(sub or {}, action, context) for sub in expected):
                return False
            continue

        if key == "environment":
            if action.environment.lower() not in {
                v.lower() for v in _as_iterable(expected)
            }:
                return False
            continue

        if key == "category":
            if action.category.lower() not in {
                v.lower() for v in _as_iterable(expected)
            }:
                return False
            continue

        if key == "verb":
            if action.verb.lower() not in {
                v.lower() for v in _as_iterable(expected)
            }:
                return False
            continue

        if key == "target":
            targets = _as_iterable(expected)
            if not any(t.lower() in action.target.lower() for t in targets):
                return False
            continue

        if key == "destructive":
            if bool(expected) is not bool(action.is_destructive):
                return False
            continue

        if key == "reversible":
            if bool(expected) is not bool(action.reversible):
                return False
            continue

        if key == "after_hours":
            if bool(expected) is not bool(context.get("after_hours", False)):
                return False
            continue

        if key == "blast_radius_gte":
            try:
                threshold = int(expected)
            except (TypeError, ValueError):
                return False
            if int(action.blast_radius) < threshold:
                return False
            continue

        return False  # unknown key — fail the match defensively

    return True
