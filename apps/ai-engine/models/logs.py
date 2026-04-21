"""Pydantic models for AI-powered log analysis endpoints.

Defines request and response schemas for log summarization, natural language
query translation, and anomaly detection features.
"""


from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Log summarization
# ------------------------------------------------------------------ #


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: str = Field(..., description="ISO-8601 timestamp of the log entry")
    level: str = Field(..., description="Log severity level (debug, info, warning, error, critical)")
    service: str = Field(default="unknown", description="Service that emitted the log")
    message: str = Field(..., description="Log message body")
    trace_id: str = Field(default="", description="Distributed trace identifier")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional key-value metadata")


class LogSummarizeRequest(BaseModel):
    """Request payload for log summarization."""

    logs: list[dict] = Field(
        ...,
        description="List of log entry dictionaries to summarize",
        min_length=1,
    )
    time_range: str = Field(
        default="1h",
        description="Human-readable time range the logs cover (e.g. '15m', '1h', '6h')",
    )
    context: dict | None = Field(
        default=None,
        description="Optional context such as deployment info or incident ID",
    )


class KeyEvent(BaseModel):
    """A significant event extracted from logs."""

    timestamp: str = Field(..., description="When the event occurred")
    service: str = Field(..., description="Service where the event originated")
    level: str = Field(..., description="Log level of the event")
    message: str = Field(..., description="Event description")


class ErrorPattern(BaseModel):
    """A grouped error pattern with frequency."""

    pattern: str = Field(..., description="Error message or template")
    count: int = Field(..., description="Number of occurrences")
    severity: str = Field(..., description="Severity level")


class LogSummary(BaseModel):
    """AI-generated summary of a batch of log entries."""

    overview: str = Field(
        ...,
        description="2-3 sentence high-level summary of the log batch",
    )
    key_events: list[KeyEvent] = Field(
        default_factory=list,
        description="Significant events with timestamps",
    )
    error_patterns: list[ErrorPattern] = Field(
        default_factory=list,
        description="Grouped errors with frequency",
    )
    security_concerns: list[str] = Field(
        default_factory=list,
        description="Security-relevant findings",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggested actions",
    )


# ------------------------------------------------------------------ #
# Natural language query translation
# ------------------------------------------------------------------ #


class NaturalLanguageQueryRequest(BaseModel):
    """Request payload for natural language to ClickHouse query conversion."""

    query: str = Field(
        ...,
        description="Natural language description of the desired query",
        min_length=3,
    )
    available_services: list[str] = Field(
        default_factory=list,
        description="List of known service names to aid query generation",
    )


class StructuredQuery(BaseModel):
    """A ClickHouse query generated from natural language."""

    query: str = Field(..., description="ClickHouse-compatible SQL query")
    explanation: str = Field(
        ...,
        description="Human-readable explanation of what the query does",
    )
    estimated_rows: int | None = Field(
        default=None,
        description="Rough estimate of rows the query may return",
    )


# ------------------------------------------------------------------ #
# Anomaly detection
# ------------------------------------------------------------------ #


class AnomalyDetectionRequest(BaseModel):
    """Request payload for log anomaly detection."""

    logs: list[dict] = Field(
        ...,
        description="List of log entry dictionaries to scan for anomalies",
        min_length=1,
    )
    baseline_period: str = Field(
        default="24h",
        description="Baseline period to compare against (e.g. '1h', '24h', '7d')",
    )


class DetectedAnomaly(BaseModel):
    """A single detected anomaly in log data."""

    anomaly_type: str = Field(
        ...,
        description="Type of anomaly: spike, pattern_break, new_error, or frequency_change",
    )
    severity: str = Field(
        ...,
        description="Severity level: critical, high, medium, or low",
    )
    description: str = Field(..., description="Human-readable description of the anomaly")
    affected_service: str = Field(..., description="Service affected by the anomaly")
    time_window: str = Field(..., description="Time window in which the anomaly was observed")
    evidence: list[dict] = Field(
        default_factory=list,
        description="Specific log entries that support the anomaly detection",
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )
