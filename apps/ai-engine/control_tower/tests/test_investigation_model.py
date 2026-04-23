"""Tests for the Pydantic models in :mod:`control_tower.investigation`."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from control_tower.investigation import (
    Alert,
    Context,
    Evidence,
    Hypothesis,
    Investigation,
    InvestigationUsage,
    LogSummary,
    MetricSummary,
    PatternFinding,
    ProposedAction,
    TraceHint,
    WikiSnippet,
)


def test_alert_minimum_fields():
    alert = Alert(service="acme-api", severity="critical")
    assert alert.service == "acme-api"
    assert alert.severity == "critical"
    assert alert.environment == "prod"
    assert alert.title == ""


def test_alert_round_trip_from_dict():
    payload = {
        "service": "payment-svc",
        "severity": "warning",
        "title": "5xx spike",
        "labels": {"rule_id": "r-1"},
        "environment": "stage",
    }
    alert = Alert.model_validate(payload)
    assert alert.service == "payment-svc"
    assert alert.environment == "stage"
    assert alert.labels["rule_id"] == "r-1"


def test_alert_accepts_question_only():
    alert = Alert(question="why did deploy fail at 09:17?")
    assert alert.question
    assert alert.service is None
    assert alert.severity == "unknown"


def test_evidence_confidence_clamped():
    ev = Evidence(kind="log", summary="spike", confidence=1.0)
    assert ev.confidence == 1.0
    with pytest.raises(Exception):
        Evidence(kind="log", summary="", confidence=1.5)


def test_hypothesis_default_confidence():
    h = Hypothesis(title="oom")
    assert 0.0 <= h.confidence <= 1.0
    assert h.evidence == []


def test_proposed_action_defaults_to_suggest():
    pa = ProposedAction(
        name="restart pod", verb="restart", target="pod/foo"
    )
    assert pa.tier == "SUGGEST"
    assert pa.approved is False
    assert pa.explanation == ""


def test_context_render_empty():
    ctx = Context(mode="eco")
    assert ctx.render() == ""


def test_context_render_has_sections():
    ctx = Context(
        mode="standard",
        wiki_pages=[
            WikiSnippet(
                slug="acme-api", title="Acme API", snippet="the api"
            )
        ],
        metrics=[
            MetricSummary(promql="up", series_count=1, last_value=1.0)
        ],
        logs=[
            LogSummary(
                timestamp=datetime.now(timezone.utc),
                severity="error",
                service="acme-api",
                body="boom",
            )
        ],
    )
    rendered = ctx.render()
    assert "Wiki references" in rendered
    assert "Metric signals" in rendered
    assert "Recent log lines" in rendered


def test_context_render_trims_long_snippets():
    long_snippet = "x" * 800
    ctx = Context(
        mode="deep",
        wiki_pages=[
            WikiSnippet(slug="acme-wiki", title="wiki", snippet=long_snippet)
        ],
    )
    rendered = ctx.render()
    assert "..." in rendered
    assert len(rendered) < len(long_snippet) + 200


def test_investigation_halted_property():
    inv = Investigation(
        id="inv-1", mode="halted", alert=Alert(service="x")
    )
    assert inv.halted is True


def test_investigation_happy_path_property():
    inv = Investigation(
        id="inv-2",
        mode="standard",
        alert=Alert(service="acme-api"),
        summary="looks like a deploy",
    )
    assert inv.halted is False
    assert inv.summary.startswith("looks")


def test_investigation_round_trips_as_json():
    inv = Investigation(
        id="inv-3",
        mode="standard",
        alert=Alert(service="acme-api"),
        hypotheses=[Hypothesis(title="cpu saturation")],
        proposed_action=ProposedAction(
            name="scale up", verb="scale", target="deployment/acme-api"
        ),
        usage=InvestigationUsage(llm_calls=1, input_tokens=100),
    )
    data = inv.model_dump()
    assert data["mode"] == "standard"
    assert len(data["hypotheses"]) == 1
    # Re-hydrate
    restored = Investigation.model_validate(data)
    assert restored.id == inv.id
    assert restored.proposed_action is not None
    assert restored.proposed_action.name == "scale up"


def test_pattern_finding_defaults():
    pf = PatternFinding()
    assert pf.total_events == 0
    assert pf.markdown == ""


def test_trace_hint_required_fields():
    th = TraceHint(
        trace_id="t-1", service="acme-api", operation="GET /health"
    )
    assert th.duration_ms == 0.0
    assert th.status_code is None
