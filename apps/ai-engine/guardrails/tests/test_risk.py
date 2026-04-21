"""Risk assessment tests."""

from __future__ import annotations

from guardrails.risk import Action, RiskAssessment
from guardrails.tiers import AutomationTier


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


def test_dev_restart_pod_is_low_risk():
    score = RiskAssessment.assess(_action())
    assert score.score <= 20
    assert score.tier_cap == AutomationTier.EXECUTE


def test_prod_adds_significant_penalty():
    dev = RiskAssessment.assess(_action(environment="dev"))
    prod = RiskAssessment.assess(_action(environment="prod"))
    assert prod.score > dev.score
    # prod alone (+40) pushes above EXECUTE ceiling (40), so cap at PROPOSE
    assert prod.tier_cap <= AutomationTier.PROPOSE


def test_unknown_environment_treated_as_prod():
    # Fail-safe: unknown env should not sneak under the prod penalty.
    unknown = RiskAssessment.assess(_action(environment="weirdland"))
    assert unknown.score >= 40
    assert any("unknown environment" in r for r in unknown.reasons)


def test_destructive_verb_adds_penalty():
    delete_action = _action(verb="delete", name="delete deployment")
    score = RiskAssessment.assess(delete_action)
    assert any("destructive" in r for r in score.reasons)
    assert score.score >= 25  # 0 dev + 25 destructive


def test_scale_to_zero_detected_as_destructive():
    a = _action(name="scale deployment X to 0", verb="scale")
    assert a.is_destructive is True


def test_iam_category_penalty():
    iam = RiskAssessment.assess(_action(category="iam"))
    # deployment carries +5; iam carries +30 — gap is 25 in the defaults.
    base = RiskAssessment.assess(_action(category="deployment"))
    assert iam.score - base.score == 25
    assert any("category=iam" in r for r in iam.reasons)


def test_blast_radius_scales_score():
    small = RiskAssessment.assess(_action(blast_radius=1))
    big = RiskAssessment.assess(_action(blast_radius=600))
    assert big.score >= small.score + 20


def test_irreversible_adds_ten():
    rev = RiskAssessment.assess(_action(reversible=True))
    irr = RiskAssessment.assess(_action(reversible=False))
    assert irr.score == rev.score + 10
    assert any("irreversible" in r for r in irr.reasons)


def test_context_extra_risk_is_additive():
    score = RiskAssessment.assess(
        _action(), context={"extra_risk": [(7, "operator flagged"), (3, "new region")]}
    )
    # 5 (dev) + 5 (deployment category) + 7 + 3 = 20
    assert score.score == 20
    assert any("operator flagged" in r for r in score.reasons)
    assert any("new region" in r for r in score.reasons)


def test_score_is_clamped():
    score = RiskAssessment.assess(
        _action(
            environment="prod",
            category="iam",
            verb="delete",
            blast_radius=10000,
            reversible=False,
        ),
        context={"extra_risk": [(50, "disaster-mode")]},
    )
    assert score.score == 100
    assert score.tier_cap == AutomationTier.SUGGEST


def test_reasons_are_ordered_and_present():
    score = RiskAssessment.assess(_action(environment="prod", verb="delete"))
    # environment reason is added before destructive reason
    reasons = list(score.reasons)
    env_idx = next(i for i, r in enumerate(reasons) if "environment=prod" in r)
    des_idx = next(i for i, r in enumerate(reasons) if "destructive" in r)
    assert env_idx < des_idx
