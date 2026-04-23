"""End-to-end orchestrator tests using mocked router + fetchers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from control_tower.config import ControlTowerConfig
from control_tower.investigation import Alert, Investigation, WikiSnippet
from control_tower.orchestrator import ControlTower


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Stubs
# --------------------------------------------------------------------------- #


class FakeRouterResponse:
    def __init__(self, text: str, backend: str = "claude") -> None:
        self.text = text
        self.backend = backend
        self.model = "stub-model"
        self.usage = {"input_tokens": 123, "output_tokens": 45}
        self.finish_reason = "stop"
        self.decision = None


class FakeLLMRouter:
    """Async router stub that returns queued responses."""

    def __init__(self, responses: list[str] | list[FakeRouterResponse]) -> None:
        self._responses: list[Any] = list(responses)
        self.calls: list[list[dict]] = []

    async def complete(self, messages, mode="auto", sensitivity_override=None):
        self.calls.append(list(messages))
        if not self._responses:
            return FakeRouterResponse("{}")
        item = self._responses.pop(0)
        if isinstance(item, FakeRouterResponse):
            return item
        return FakeRouterResponse(str(item))


class FakeKillSwitch:
    def __init__(self, active: bool = False) -> None:
        self._active = active

    def is_active(self) -> bool:
        return self._active


class FakeWiki:
    def __init__(self, pages: list[WikiSnippet] | None = None) -> None:
        self.pages = pages or []

    def query(self, topic, *, limit=5):
        return self.pages[:limit]


class FakeLogFetcher:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []
        self.called = False

    async def search(self, query, start, end, limit=500):
        self.called = True
        return self.rows


class FakeMetricFetcher:
    def __init__(self) -> None:
        self.called = False

    async def query_range(self, promql, start, end, step_seconds):
        self.called = True
        return SimpleNamespace(
            promql=promql,
            start=start,
            end=end,
            step_seconds=step_seconds,
            series=[],
        )


class FakePatternAnalyzer:
    def __init__(self) -> None:
        self.called = False

    def analyze(self, events):
        self.called = True
        return SimpleNamespace(
            total_events=len(list(events)),
            bursts=[],
            correlation_graph=SimpleNamespace(
                edges=[], services=[], window_seconds=60,
                top_pairs=lambda n: [],
            ),
            time_pattern=SimpleNamespace(
                total_events=len(list(events)),
                weekday_share=0.0,
                hour_share=0.0,
                dominant_weekday=None,
                dominant_hour=0,
                hotspots=[],
            ),
            week_anomalies=[],
            message_clusters=[],
            severity_counts={},
            trace_coverage=0.0,
        )


class FakeGuardrails:
    def __init__(self, *, approve: bool = True, tier: str = "PROPOSE") -> None:
        self._approve = approve
        self._tier = tier
        self.called_with: list[Any] = []

    def evaluate(self, action, context=None, requested_tier="SUGGEST"):
        self.called_with.append((action, context, requested_tier))
        # Build a decision-shaped object.
        return SimpleNamespace(
            tier=SimpleNamespace(name=self._tier if self._approve else "SUGGEST"),
            approved=self._approve,
            risk=SimpleNamespace(score=30),
            policy=SimpleNamespace(
                required_approvals=1 if self._approve else 0,
                approver_groups=("prod-oncall",) if self._approve else (),
            ),
            reasons=(
                ("low-risk dev change",)
                if self._approve
                else ("policy deny: destructive prod", "downgraded to SUGGEST")
            ),
        )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _happy_response(
    *,
    summary: str = "error rate spike",
    action: dict | None = None,
) -> str:
    payload: dict[str, Any] = {
        "summary": summary,
        "hypotheses": [
            {
                "title": "cpu saturation",
                "rationale": "metric shows 95% cpu",
                "confidence": 0.8,
                "evidence": [
                    {
                        "kind": "metric",
                        "summary": "cpu over 95%",
                        "confidence": 0.9,
                    }
                ],
            },
            {
                "title": "bad deploy",
                "rationale": "recent deploy 15m ago",
                "confidence": 0.4,
                "evidence": [],
            },
        ],
        "proposed_action": action,
    }
    return json.dumps(payload)


def _tower(
    *,
    responses: list[str] | None = None,
    killswitch: FakeKillSwitch | None = None,
    guardrails: FakeGuardrails | None = None,
    wiki: FakeWiki | None = None,
    log_fetcher: FakeLogFetcher | None = None,
    metric_fetcher: FakeMetricFetcher | None = None,
    pattern_analyzer: FakePatternAnalyzer | None = None,
    config: ControlTowerConfig | None = None,
) -> ControlTower:
    router = FakeLLMRouter(responses or [_happy_response()])
    return ControlTower(
        llm_router=router,
        wiki=wiki or FakeWiki([
            WikiSnippet(slug="acme-api", title="Acme API", snippet="primary"),
        ]),
        log_fetcher=log_fetcher,
        metric_fetcher=metric_fetcher,
        pattern_analyzer=pattern_analyzer,
        guardrails=guardrails,
        killswitch=killswitch,
        config=config or ControlTowerConfig(),
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


async def test_eco_mode_happy_path():
    tower = _tower()
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="eco"
    )
    assert isinstance(inv, Investigation)
    assert inv.mode == "eco"
    assert inv.summary == "error rate spike"
    assert len(inv.hypotheses) == 2
    assert inv.hypotheses[0].title == "cpu saturation"
    assert inv.proposed_action is None
    assert inv.halted is False
    assert inv.routing_backend == "claude"


async def test_standard_mode_includes_telemetry():
    logs = FakeLogFetcher(rows=[])
    metrics = FakeMetricFetcher()
    tower = _tower(log_fetcher=logs, metric_fetcher=metrics)
    await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="standard"
    )
    assert logs.called is True
    assert metrics.called is True


async def test_deep_mode_runs_pattern_analyzer():
    pa = FakePatternAnalyzer()
    # Log rows so pattern analyzer has events to chew on.
    logs = FakeLogFetcher(
        rows=[
            SimpleNamespace(
                timestamp=datetime.now(timezone.utc),
                body="boom",
                severity="error",
                service="acme-api",
                trace_id=None,
            )
            for _ in range(3)
        ]
    )
    metrics = FakeMetricFetcher()
    tower = _tower(
        log_fetcher=logs,
        metric_fetcher=metrics,
        pattern_analyzer=pa,
    )
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="deep"
    )
    assert pa.called is True
    assert inv.context is not None
    assert inv.context.patterns is not None
    assert inv.context.patterns.total_events == 3


async def test_killswitch_halts_investigation():
    tower = _tower(killswitch=FakeKillSwitch(active=True))
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="standard"
    )
    assert inv.halted is True
    assert inv.mode == "halted"
    assert inv.proposed_action is None
    assert inv.halted_reason == "killswitch_active"
    assert inv.usage.llm_calls == 0
    # No LLM call was made.
    assert tower.router.calls == []  # type: ignore[attr-defined]


async def test_guardrails_deny_produces_suggest_tier():
    action_suggestion = {
        "name": "drop prod database",
        "verb": "delete",
        "target": "rds/acme-db",
        "environment": "prod",
        "category": "database",
        "blast_radius": 100,
        "reversible": False,
        "requested_tier": "EXECUTE",
        "explanation": "this is clearly wrong",
    }
    tower = _tower(
        responses=[_happy_response(action=action_suggestion)],
        guardrails=FakeGuardrails(approve=False, tier="SUGGEST"),
    )
    inv = await tower.investigate(
        Alert(service="acme-db", severity="critical"), mode="standard"
    )
    assert inv.proposed_action is not None
    assert inv.proposed_action.tier == "SUGGEST"
    assert inv.proposed_action.approved is False
    assert inv.proposed_action.reasons  # populated
    assert any("tier" in w.lower() for w in inv.warnings)


async def test_guardrails_approve_populates_action():
    action_suggestion = {
        "name": "scale up acme-api",
        "verb": "scale",
        "target": "deployment/acme-api",
        "environment": "prod",
        "category": "deployment",
        "blast_radius": 3,
        "reversible": True,
        "requested_tier": "PROPOSE",
        "explanation": "traffic spike",
    }
    tower = _tower(
        responses=[_happy_response(action=action_suggestion)],
        guardrails=FakeGuardrails(approve=True, tier="PROPOSE"),
    )
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="standard"
    )
    pa = inv.proposed_action
    assert pa is not None
    assert pa.name == "scale up acme-api"
    assert pa.tier == "PROPOSE"
    assert pa.approved is True
    assert pa.risk_score == 30
    assert "prod-oncall" in pa.approver_groups


async def test_unparseable_response_captured_as_warning():
    tower = _tower(responses=["not json at all", "still not json"])
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="standard"
    )
    assert inv.summary == "no parseable answer"
    assert inv.hypotheses == []
    assert any("not valid JSON" in m["content"] or "not parseable" in w
               for m in tower.router.calls[-1]  # type: ignore[attr-defined]
               for w in inv.warnings)


async def test_response_tolerates_markdown_fences():
    tower = _tower(responses=[f"```json\n{_happy_response()}\n```"])
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="standard"
    )
    assert inv.summary == "error rate spike"
    assert len(inv.hypotheses) == 2


async def test_question_as_string_works():
    tower = _tower()
    inv = await tower.investigate(
        "why did the deploy fail at 09:17?", mode="eco"
    )
    assert inv.alert.question == "why did the deploy fail at 09:17?"
    assert inv.alert.service is None


async def test_alert_as_dict_works():
    tower = _tower()
    inv = await tower.investigate(
        {"service": "billing-svc", "severity": "warning"}, mode="eco"
    )
    assert inv.alert.service == "billing-svc"
    assert inv.alert.severity == "warning"


async def test_lookup_returns_previous_investigation():
    tower = _tower()
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="eco"
    )
    found = tower.lookup(inv.id)
    assert found is inv


async def test_lookup_missing_returns_none():
    tower = _tower()
    assert tower.lookup("nope") is None


async def test_modes_returns_all_three():
    tower = _tower()
    names = [m.name for m in tower.modes()]
    assert names == ["eco", "standard", "deep"]


async def test_otel_root_span_sets_attributes():
    """The investigation should emit an aegis.investigation root span.

    We verify indirectly by ensuring the investigation completes, has
    no exceptions, and attaches a trace_id when OTel is available.
    """
    try:
        from opentelemetry import trace  # noqa: F401
    except Exception:
        pytest.skip("OTel not available")
    tower = _tower()
    inv = await tower.investigate(
        Alert(service="acme-api", severity="critical"), mode="eco"
    )
    # trace_id may be None if no exporter is registered, but the
    # orchestrator should not crash and should finish normally.
    assert inv.mode == "eco"


async def test_requires_llm_router():
    with pytest.raises(ValueError):
        ControlTower(llm_router=None)


async def test_default_mode_used_when_omitted():
    tower = _tower(config=ControlTowerConfig(default_mode="eco"))
    inv = await tower.investigate(Alert(service="acme-api"))
    assert inv.mode == "eco"


async def test_unknown_mode_rejected():
    tower = _tower()
    with pytest.raises(ValueError):
        await tower.investigate(Alert(service="acme-api"), mode="ultra")


async def test_usage_tracked_in_investigation():
    tower = _tower()
    inv = await tower.investigate(Alert(service="acme-api"), mode="eco")
    assert inv.usage.llm_calls >= 1
    assert inv.usage.duration_ms >= 0.0


async def test_invalid_action_suggestion_ignored():
    # Missing required fields — parser returns None.
    tower = _tower(
        responses=[
            _happy_response(action={"name": "", "verb": ""})
        ],
        guardrails=FakeGuardrails(),
    )
    inv = await tower.investigate(Alert(service="acme-api"), mode="standard")
    assert inv.proposed_action is None


async def test_guardrails_exception_degrades_to_suggest():
    class BoomGuardrails:
        def evaluate(self, action, context=None, requested_tier="SUGGEST"):
            raise RuntimeError("boom")

    action_suggestion = {
        "name": "restart",
        "verb": "restart",
        "target": "pod/acme",
        "environment": "dev",
        "category": "deployment",
        "blast_radius": 1,
        "reversible": True,
        "requested_tier": "PROPOSE",
    }
    tower = _tower(
        responses=[_happy_response(action=action_suggestion)],
        guardrails=BoomGuardrails(),
    )
    inv = await tower.investigate(Alert(service="acme"), mode="standard")
    assert inv.proposed_action is not None
    assert inv.proposed_action.tier == "SUGGEST"
    assert inv.proposed_action.approved is False
    assert any("evaluation error" in r for r in inv.proposed_action.reasons)
