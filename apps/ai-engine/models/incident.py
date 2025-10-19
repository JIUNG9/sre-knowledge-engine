"""Pydantic models for incident investigation."""

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentContext(BaseModel):
    """Context information about an incident under investigation."""

    incident_id: str = Field(..., description="Unique identifier for the incident")
    title: str = Field(default="", description="Short incident title")
    description: str = Field(default="", description="Detailed incident description")
    severity: str = Field(
        default="medium",
        description="Incident severity level",
        pattern="^(critical|high|medium|low)$",
    )
    source: str = Field(default="manual", description="Alert source (e.g., 'pagerduty', 'signoz', 'manual')")
    affected_services: list[str] = Field(default_factory=list, description="List of affected service names")
    alert_data: dict = Field(default_factory=dict, description="Raw alert payload from the monitoring system")
    started_at: datetime | None = Field(default=None, description="When the incident started")
    labels: dict[str, str] = Field(default_factory=dict, description="Key-value labels for the incident")


class InvestigationRequest(BaseModel):
    """Request payload for starting an incident investigation."""

    incident: IncidentContext = Field(..., description="Incident context to investigate")
    investigation_depth: str = Field(
        default="standard",
        description="Investigation depth: 'quick' (5 min), 'standard' (15 min), 'deep' (30 min)",
        pattern="^(quick|standard|deep)$",
    )
    auto_remediate: bool = Field(
        default=False,
        description="Whether to automatically apply low-risk remediations",
    )
    notify_channel: str | None = Field(
        default=None,
        description="Slack channel to post investigation updates to",
    )


class RootCause(BaseModel):
    """Root cause analysis result."""

    category: str = Field(..., description="Root cause category (e.g., 'dependency_failure', 'resource_exhaustion')")
    description: str = Field(..., description="Detailed root cause description")
    evidence: list[str] = Field(default_factory=list, description="Evidence supporting the root cause analysis")


class RemediationStep(BaseModel):
    """A proposed remediation action."""

    action: str = Field(..., description="Description of the remediation action")
    risk: str = Field(default="medium", description="Risk level of the action", pattern="^(low|medium|high)$")
    requires_approval: bool = Field(default=True, description="Whether human approval is needed")
    estimated_impact: str = Field(default="", description="Expected impact of the remediation")


class TimelineEvent(BaseModel):
    """A single event in the incident timeline."""

    time: str = Field(..., description="Timestamp of the event")
    event: str = Field(..., description="Description of what happened")
    source: str = Field(default="", description="Data source that reported this event")


class InvestigationResult(BaseModel):
    """Complete investigation result returned by the AI agent."""

    incident_id: str = Field(..., description="ID of the investigated incident")
    status: str = Field(
        default="completed",
        description="Investigation status",
        pattern="^(in_progress|completed|failed|needs_escalation)$",
    )
    summary: str = Field(..., description="Executive summary of the investigation findings")
    root_cause: RootCause = Field(..., description="Root cause analysis")
    affected_services: list[str] = Field(default_factory=list, description="Services impacted by the incident")
    timeline: list[TimelineEvent] = Field(default_factory=list, description="Chronological incident timeline")
    proposed_remediation: list[RemediationStep] = Field(
        default_factory=list, description="Ordered list of proposed remediation steps"
    )
    confidence_score: float = Field(
        ...,
        description="Confidence in the root cause analysis (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )
    severity: str = Field(default="medium", description="Assessed severity level")
    investigated_at: datetime = Field(..., description="When the investigation was completed")
