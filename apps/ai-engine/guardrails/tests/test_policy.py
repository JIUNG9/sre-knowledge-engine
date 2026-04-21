"""Policy engine tests — each rule must be testable in isolation."""

from __future__ import annotations

import datetime as _dt

import pytest

from guardrails.policy import GuardrailsPolicy, PolicyValidationError
from guardrails.risk import Action
from guardrails.tiers import AutomationTier

from .conftest import DEFAULT_POLICY_PATH, TEST_POLICY_PATH


def _action(**overrides):
    base = dict(
        name="scale deployment",
        verb="scale",
        target="payment-svc",
        environment="dev",
        category="deployment",
        blast_radius=1,
        reversible=True,
    )
    base.update(overrides)
    return Action(**base)


def test_load_default_policy_compiles():
    policy = GuardrailsPolicy.load(DEFAULT_POLICY_PATH)
    assert len(policy.rules) >= 5
    assert policy.source_path == DEFAULT_POLICY_PATH


def test_load_test_policy_compiles():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    ids = [r.id for r in policy.rules]
    assert "test-prod-two-approvals" in ids
    assert "test-iam-cap-propose" in ids


def test_prod_two_approvals_rule():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    decision = policy.evaluate(_action(environment="prod"))
    assert decision.required_approvals == 2
    assert "test-prod-two-approvals" in decision.matched_rule_ids


def test_iam_cap_rule_applies_in_any_env():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    decision = policy.evaluate(_action(category="iam", environment="dev"))
    assert decision.cap_tier == AutomationTier.PROPOSE


def test_destructive_prod_rule_caps_tier():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    action = _action(environment="prod", verb="delete", name="delete svc")
    decision = policy.evaluate(action)
    assert decision.cap_tier <= AutomationTier.PROPOSE


def test_after_hours_rule_matches_only_late():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    action = _action(environment="prod")

    # 10:00 local = daytime => after-hours rule should NOT match
    daytime = policy.evaluate(
        action, now=_dt.datetime(2026, 4, 21, 10, 0, 0)
    )
    assert "test-after-hours-approval" not in daytime.matched_rule_ids

    # 22:00 local = after hours => rule matches
    night = policy.evaluate(
        action, now=_dt.datetime(2026, 4, 21, 22, 0, 0)
    )
    assert "test-after-hours-approval" in night.matched_rule_ids


def test_wide_blast_radius_adds_risk():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    small = policy.evaluate(_action(blast_radius=10))
    wide = policy.evaluate(_action(blast_radius=200))
    assert small.added_risk == 0
    assert wide.added_risk == 15


def test_deny_rule_blocks_prod_db_destroy():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    action = _action(
        environment="prod", category="database", verb="drop", name="drop users"
    )
    decision = policy.evaluate(action)
    assert decision.denied is True
    assert "test-deny-prod-db-drop" in decision.matched_rule_ids


def test_any_match_block_matches_either_branch():
    policy = GuardrailsPolicy.load(TEST_POLICY_PATH)
    # First branch of `any` matches:
    a = _action(target="prod-secret-sauce-bucket")
    d1 = policy.evaluate(a)
    assert d1.cap_tier == AutomationTier.DRAFT
    # Second branch:
    b = _action(target="service-crown-jewels")
    d2 = policy.evaluate(b)
    assert d2.cap_tier == AutomationTier.DRAFT
    # Neither:
    c = _action(target="boring-config")
    d3 = policy.evaluate(c)
    assert "test-any-block" not in d3.matched_rule_ids


def test_invalid_policy_unknown_match_key_fails_fast():
    with pytest.raises(PolicyValidationError):
        GuardrailsPolicy.from_dict(
            {
                "rules": [
                    {
                        "id": "bad",
                        "match": {"planet": "mars"},
                        "effect": {"cap_tier": "SUGGEST"},
                    }
                ]
            }
        )


def test_invalid_policy_missing_id_fails_fast():
    with pytest.raises(PolicyValidationError):
        GuardrailsPolicy.from_dict({"rules": [{"match": {}, "effect": {}}]})


def test_invalid_policy_duplicate_id_fails_fast():
    with pytest.raises(PolicyValidationError):
        GuardrailsPolicy.from_dict(
            {
                "rules": [
                    {"id": "x", "match": {}, "effect": {}},
                    {"id": "x", "match": {}, "effect": {}},
                ]
            }
        )


def test_invalid_policy_unknown_tier_fails_fast():
    with pytest.raises(ValueError):
        GuardrailsPolicy.from_dict(
            {
                "rules": [
                    {
                        "id": "x",
                        "match": {},
                        "effect": {"cap_tier": "NOPE"},
                    }
                ]
            }
        )


def test_effect_composition_max_approvals_wins():
    policy = GuardrailsPolicy.from_dict(
        {
            "rules": [
                {"id": "a", "match": {"environment": "prod"}, "effect": {"require_approvals": 1}},
                {"id": "b", "match": {"environment": "prod"}, "effect": {"require_approvals": 3}},
            ]
        }
    )
    d = policy.evaluate(_action(environment="prod"))
    assert d.required_approvals == 3


def test_effect_composition_lowest_cap_wins():
    policy = GuardrailsPolicy.from_dict(
        {
            "rules": [
                {"id": "a", "match": {"environment": "prod"}, "effect": {"cap_tier": "PROPOSE"}},
                {"id": "b", "match": {"environment": "prod"}, "effect": {"cap_tier": "DRAFT"}},
            ]
        }
    )
    d = policy.evaluate(_action(environment="prod"))
    assert d.cap_tier == AutomationTier.DRAFT
