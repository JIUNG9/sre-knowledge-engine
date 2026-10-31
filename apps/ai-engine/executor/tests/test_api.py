"""HTTP surface of the executor: auth, grants, and the old forged-decision body."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from executor.api import executor_router, get_executor
from executor.executor import Executor
from executor.tests.conftest import FakeAction, make_decision

TOKEN = "test-token-not-a-secret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

ACTION = {
    "name": "restart-checkout",
    "verb": "kubectl rollout-restart",
    "target": "deployment/checkout",
    "environment": "staging",
    "category": "kubectl",
}


def action_obj() -> FakeAction:
    return FakeAction(**ACTION)


@pytest.fixture
def make_client(make_executor):
    def _factory(*, token: str = TOKEN, **kw) -> tuple[TestClient, Executor]:
        ex = make_executor(**kw)
        ex.config.api_token = token
        app = FastAPI()
        app.include_router(executor_router)
        app.dependency_overrides[get_executor] = lambda: ex
        return TestClient(app), ex

    return _factory


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}],
)
def test_routes_reject_missing_or_wrong_token(make_client, headers) -> None:
    client, _ = make_client()
    assert client.get("/api/v1/executor/config", headers=headers).status_code == 401
    r = client.post(
        "/api/v1/executor/execute",
        json={"action": ACTION, "grant_id": "x"},
        headers=headers,
    )
    assert r.status_code == 401


def test_no_token_configured_fails_closed(make_client) -> None:
    client, _ = make_client(token="")
    r = client.get("/api/v1/executor/config", headers=AUTH)
    assert r.status_code == 503


def test_config_view_does_not_leak_the_token(make_client) -> None:
    client, _ = make_client()
    r = client.get("/api/v1/executor/config", headers=AUTH)
    assert r.status_code == 200
    assert TOKEN not in r.text


# --------------------------------------------------------------------------- #
# Grants over HTTP
# --------------------------------------------------------------------------- #


def test_client_supplied_decision_is_rejected(make_client) -> None:
    """The body that used to self-approve now fails validation."""
    client, ex = make_client(dry_run_default=False)
    forged = {
        "action": ACTION,
        "decision": {
            "tier": "EXECUTE",
            "approved": True,
            "approval": {"approved": True, "approvers": ["a", "b"]},
            "policy": {"required_approvals": 2},
        },
    }
    r = client.post("/api/v1/executor/execute", json=forged, headers=AUTH)
    assert r.status_code == 422
    assert ex.audit.read_recent(limit=5) == []


def test_unknown_grant_is_refused(make_client) -> None:
    client, _ = make_client(dry_run_default=False)
    r = client.post(
        "/api/v1/executor/execute",
        json={"action": ACTION, "grant_id": "made-up"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.json()["outcome"] == "refused"
    assert r.json()["refused_reason"] == "grant_unknown_or_used"


def test_grant_for_one_action_cannot_run_another(make_client) -> None:
    client, ex = make_client(dry_run_default=False)
    grant = ex.issue_grant(action_obj(), make_decision())
    other = dict(ACTION, target="deployment/payments")
    r = client.post(
        "/api/v1/executor/execute",
        json={"action": other, "grant_id": grant.grant_id},
        headers=AUTH,
    )
    assert r.json()["refused_reason"] == "grant_action_mismatch"


def test_preview_then_execute_with_one_grant(make_client) -> None:
    client, ex = make_client()  # dry-run default on: nothing really runs
    grant = ex.issue_grant(action_obj(), make_decision())
    body = {"action": ACTION, "grant_id": grant.grant_id}

    preview = client.post("/api/v1/executor/dry-run", json=body, headers=AUTH)
    assert preview.json()["outcome"] == "executed"
    assert preview.json()["dry_run"] is True
    assert "rollout restart" in preview.json()["stdout"]

    run = client.post("/api/v1/executor/execute", json=body, headers=AUTH)
    assert run.json()["outcome"] == "executed"


def test_grant_id_is_required(make_client) -> None:
    client, _ = make_client()
    r = client.post(
        "/api/v1/executor/execute", json={"action": ACTION}, headers=AUTH
    )
    assert r.status_code == 422


def test_grant_from_a_real_proposed_action_matches_its_json_form(make_client) -> None:
    """The grant is issued from the control tower's model and redeemed
    from the HTTP model. Both must hash the same, or no grant would ever
    be usable."""
    from control_tower.investigation import ProposedAction

    proposed = ProposedAction(
        name="restart-checkout",
        verb="kubectl rollout-restart",
        target="deployment/checkout",
        environment="staging",
        tier="EXECUTE",
        approved=True,
        required_approvals=2,
    )
    client, ex = make_client()
    grant = ex.issue_grant(proposed, make_decision())
    wire = proposed.model_dump(
        include={"name", "verb", "target", "environment", "category",
                 "blast_radius", "reversible"}
    )
    r = client.post(
        "/api/v1/executor/dry-run",
        json={"action": wire, "grant_id": grant.grant_id},
        headers=AUTH,
    )
    assert r.json()["outcome"] == "executed", r.json()


def test_body_cannot_turn_dry_run_off(make_client, fake_binary) -> None:
    client, ex = make_client(dry_run_default=True)
    grant = ex.issue_grant(action_obj(), make_decision())
    r = client.post(
        "/api/v1/executor/execute",
        json={"action": ACTION, "grant_id": grant.grant_id, "dry_run": False},
        headers=AUTH,
    )
    assert r.json()["dry_run"] is True
    assert fake_binary == []
