"""Pydantic models that flow in and out of the control tower.

These models are the public data shape of Layer 3. They are exposed by
the FastAPI router, serialized into audit records, and returned to
callers who drive the tower programmatically.

Design notes:

* All models inherit from :class:`pydantic.BaseModel` (v2). They are
  JSON-serialisable, copy-safe, and hashable by default.
* The :class:`Investigation` envelope is the single object the
  orchestrator returns. Halted, denied, and happy-path cases all use
  the same shape so downstream code never branches on success.
* Timestamps are timezone-aware UTC. Durations are in milliseconds.
* Evidence snippets are deliberately short — the orchestrator copies
  only the bits it needs into context, never the whole payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


InvestigationMode = Literal["eco", "standard", "deep", "halted"]

Severity = Literal["info", "warning", "critical", "unknown"]


class Alert(BaseModel):
    """A single alert / question handed to the control tower.

    Either ``service`` or ``question`` (or both) must be set. An
    ``Alert`` with only ``question`` represents a free-form SRE query
    (for example "why did the order-svc 5xx spike this morning?") —
    the tower still builds a context bundle, it just uses the question
    text to drive wiki + log queries rather than a specific service.
    """

    model_config = ConfigDict(extra="ignore")

    service: str | None = None
    severity: Severity = "unknown"
    title: str = ""
    description: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    fired_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    question: str | None = None
    source: str | None = None
    environment: str = "prod"


class WikiSnippet(BaseModel):
    """A single wiki page reference + a short snippet."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    title: str
    type: str = "concept"
    snippet: str = ""
    last_updated: datetime | None = None


class MetricSummary(BaseModel):
    """A single metric reference summarized for the LLM prompt."""

    model_config = ConfigDict(extra="ignore")

    promql: str
    series_count: int = 0
    last_value: float | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class LogSummary(BaseModel):
    """A single-line log summary."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    severity: str | None = None
    service: str | None = None
    body: str = ""


class TraceHint(BaseModel):
    """A single-line trace summary."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str
    service: str
    operation: str
    duration_ms: float = 0.0
    status_code: str | None = None


class PatternFinding(BaseModel):
    """Markdown-ready summary produced by Layer 2B."""

    model_config = ConfigDict(extra="ignore")

    total_events: int = 0
    markdown: str = ""
    bursts: int = 0
    correlations: int = 0


class Context(BaseModel):
    """Everything the LLM needs to reason about the alert.

    The tower feeds this object into a rendering step
    (:meth:`Context.render`) that produces a textual block suitable for
    a chat prompt. It is kept as structured data so downstream audit
    tools can inspect *exactly* what the LLM saw.
    """

    model_config = ConfigDict(extra="ignore")

    mode: InvestigationMode
    budget_tokens: int = 0
    wiki_pages: list[WikiSnippet] = Field(default_factory=list)
    metrics: list[MetricSummary] = Field(default_factory=list)
    logs: list[LogSummary] = Field(default_factory=list)
    traces: list[TraceHint] = Field(default_factory=list)
    alert_history: list[str] = Field(default_factory=list)
    patterns: PatternFinding | None = None
    notes: list[str] = Field(default_factory=list)

    def render(self) -> str:
        """Produce the prompt-ready textual representation.

        The output is a markdown-ish block ordered most-important first:
        wiki pages, metrics, logs, traces, patterns, notes. Empty
        sections are skipped so the prompt stays compact in eco mode.
        """
        parts: list[str] = []
        if self.wiki_pages:
            parts.append("## Wiki references")
            for page in self.wiki_pages:
                snippet = page.snippet.strip()
                if len(snippet) > 400:
                    snippet = snippet[:397] + "..."
                parts.append(f"- [[{page.slug}]] {page.title}: {snippet}")
        if self.metrics:
            parts.append("\n## Metric signals")
            for metric in self.metrics:
                last = (
                    f"{metric.last_value:.3f}"
                    if metric.last_value is not None
                    else "n/a"
                )
                parts.append(
                    f"- `{metric.promql}` — series={metric.series_count} "
                    f"last={last}"
                )
        if self.logs:
            parts.append("\n## Recent log lines")
            for line in self.logs:
                stamp = line.timestamp.isoformat(timespec="seconds")
                sev = line.severity or "?"
                body = line.body[:200]
                parts.append(f"- [{stamp}] {sev} {line.service or '-'}: {body}")
        if self.traces:
            parts.append("\n## Trace hints")
            for trace in self.traces:
                parts.append(
                    f"- {trace.trace_id} {trace.service} "
                    f"{trace.operation} dur={trace.duration_ms:.1f}ms "
                    f"status={trace.status_code or 'ok'}"
                )
        if self.alert_history:
            parts.append("\n## Alert history")
            for line in self.alert_history:
                parts.append(f"- {line}")
        if self.patterns and self.patterns.markdown:
            parts.append("\n## Pattern analysis")
            parts.append(self.patterns.markdown.strip())
        if self.notes:
            parts.append("\n## Context notes")
            for note in self.notes:
                parts.append(f"- {note}")
        return "\n".join(parts).strip()


class Evidence(BaseModel):
    """A single piece of evidence supporting a hypothesis."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["wiki", "metric", "log", "trace", "pattern", "other"] = "other"
    summary: str
    source_ref: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Hypothesis(BaseModel):
    """One possible root cause the LLM is considering."""

    model_config = ConfigDict(extra="ignore")

    title: str
    rationale: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)


class ProposedAction(BaseModel):
    """An action the control tower would like to take.

    This is the DECISION as adjudicated by Layer 4 guardrails, not a
    raw LLM suggestion. ``tier`` indicates what automation rung the
    action is permitted to run at — if guardrails denied the action
    outright, ``tier`` is ``SUGGEST`` and ``approved`` is ``False``.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    verb: str
    target: str
    environment: str = "prod"
    category: str = "deployment"
    blast_radius: int = 1
    reversible: bool = True

    tier: str = "SUGGEST"
    approved: bool = False
    risk_score: int = 0
    required_approvals: int = 0
    reasons: list[str] = Field(default_factory=list)
    approver_groups: list[str] = Field(default_factory=list)
    explanation: str = ""


class InvestigationUsage(BaseModel):
    """Token + cost accounting for a single investigation."""

    model_config = ConfigDict(extra="ignore")

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0


class Investigation(BaseModel):
    """The root object returned by :meth:`ControlTower.investigate`.

    A ``halted`` investigation (kill-switch active) carries no
    hypotheses and no action. A fully-successful investigation carries
    one-or-more hypotheses, evidence, and optionally a proposed action.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    mode: InvestigationMode
    alert: Alert
    summary: str = ""
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    proposed_action: ProposedAction | None = None
    context: Context | None = None

    trace_id: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    usage: InvestigationUsage = Field(default_factory=InvestigationUsage)

    routing_backend: str | None = None
    halted_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def halted(self) -> bool:
        """Convenience: True when the tower refused to run."""
        return self.mode == "halted"
