"""Integration tests for the FastAPI :data:`control_tower_router`."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from control_tower.api import control_tower_router, get_control_tower
from control_tower.investigation import (
    Alert,
    Hypothesis,
    Investigation,
    InvestigationUsage,
    ProposedAction,
)


class _FakeTower:
    """In-memory tower stub for API tests."""

    def __init__(self) -> None:
        self.stored: dict[str, Investigation] = {}
        self.last_call: tuple | None = None

    async def investigate(self, alert, mode="standard"):
        inv = Investigation(
            id=f"inv-{len(self.stored) + 1}",
            mode=mode,
            alert=alert if isinstance(alert, Alert) else Alert.model_validate(alert),
            summary=f"stub summary for mode={mode}",
            hypotheses=[
                Hypothesis(title="cpu saturation", confidence=0.7),
            ],
            proposed_action=ProposedAction(
                name="scale up",
                verb="scale",
                target="deployment/acme-api",
                tier="PROPOSE",
                approved=True,
                risk_score=30,
            ),
            usage=InvestigationUsage(llm_calls=1),
            trace_id=f"trace-{len(self.stored) + 1:032x}",
        )
        self.stored[inv.id] = inv
        self.last_call = (alert, mode)
        return inv

    def lookup(self, key):
        if key in self.stored:
            return self.stored[key]
        for inv in self.stored.values():
            if inv.trace_id == key:
                return inv
        return None

    def modes(self):
        from control_tower.modes import all_modes

        return all_modes()


def _client(tower: _FakeTower) -> TestClient:
    app = FastAPI()
    app.include_router(control_tower_router)
    app.dependency_overrides[get_control_tower] = lambda: tower
    return TestClient(app)


def test_modes_endpoint_returns_three():
    client = _client(_FakeTower())
    resp = client.get("/api/v2/modes")
    assert resp.status_code == 200
    body = resp.json()
    assert [m["name"] for m in body] == ["eco", "standard", "deep"]
    assert "preferred_model" in body[0]


def test_investigate_endpoint_happy_path():
    tower = _FakeTower()
    client = _client(tower)
    resp = client.post(
        "/api/v2/investigate",
        json={
            "alert": {
                "service": "acme-api",
                "severity": "critical",
                "title": "5xx spike",
            },
            "mode": "standard",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "standard"
    assert data["alert"]["service"] == "acme-api"
    assert data["hypotheses"][0]["title"] == "cpu saturation"
    assert data["proposed_action"]["tier"] == "PROPOSE"
    assert data["id"].startswith("inv-")


def test_investigate_endpoint_default_mode():
    tower = _FakeTower()
    client = _client(tower)
    resp = client.post(
        "/api/v2/investigate",
        json={"alert": {"service": "billing", "severity": "warning"}},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "standard"


def test_lookup_endpoint_existing():
    tower = _FakeTower()
    client = _client(tower)
    created = client.post(
        "/api/v2/investigate",
        json={"alert": {"service": "a"}, "mode": "eco"},
    ).json()
    inv_id = created["id"]
    resp = client.get(f"/api/v2/investigations/{inv_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == inv_id


def test_lookup_endpoint_missing():
    tower = _FakeTower()
    client = _client(tower)
    resp = client.get("/api/v2/investigations/nope")
    assert resp.status_code == 404


def test_get_control_tower_default_raises_503():
    app = FastAPI()
    app.include_router(control_tower_router)
    client = TestClient(app)
    resp = client.get("/api/v2/investigations/anything")
    assert resp.status_code == 503


def test_investigate_endpoint_accepts_dict_alert_shape():
    tower = _FakeTower()
    client = _client(tower)
    resp = client.post(
        "/api/v2/investigate",
        json={
            "alert": {
                "question": "why did the deploy fail?",
            },
            "mode": "eco",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["alert"]["question"] == "why did the deploy fail?"


def test_modes_endpoint_is_json_serializable():
    client = _client(_FakeTower())
    resp = client.get("/api/v2/modes")
    # Round-trip through JSON to prove schema stability.
    body = json.loads(resp.content)
    assert isinstance(body, list)
    for spec in body:
        assert set(
            [
                "name",
                "description",
                "preferred_model",
                "max_tokens",
                "temperature",
                "include_wiki",
                "include_logs",
                "include_metrics",
                "include_traces",
                "include_alert_history",
                "run_pattern_analyzer",
                "max_llm_calls",
                "tools",
            ]
        ).issubset(spec.keys())
