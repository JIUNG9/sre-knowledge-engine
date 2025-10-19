"""Pydantic models for log and metric analysis."""

from datetime import datetime

from pydantic import BaseModel, Field


class LogAnalysisRequest(BaseModel):
    """Request payload for log analysis."""

    service: str = Field(..., description="Service name to analyze logs for")
    time_range: str = Field(default="1h", description="Time range for log query (e.g., '15m', '1h', '6h')")
    severity_filter: str = Field(
        default="warning",
        description="Minimum log severity to include",
        pattern="^(debug|info|warning|error|critical)$",
    )
    query: str = Field(default="", description="Free-text search query to filter logs")
    namespace: str = Field(default="", description="Kubernetes namespace to scope the query")


class LogPattern(BaseModel):
    """A detected pattern in log data."""

    pattern: str = Field(..., description="The log pattern/message template")
    count: int = Field(..., description="Number of occurrences")
    severity: str = Field(..., description="Log severity level")
    first_seen: datetime = Field(..., description="First occurrence timestamp")
    last_seen: datetime = Field(..., description="Last occurrence timestamp")
    sample_entries: list[str] = Field(default_factory=list, description="Sample log entries matching this pattern")


class LogAnomaly(BaseModel):
    """A detected anomaly in log data."""

    type: str = Field(..., description="Anomaly type (e.g., 'rate_spike', 'new_error', 'pattern_change')")
    description: str = Field(..., description="Human-readable anomaly description")
    baseline_rate: float = Field(default=0.0, description="Normal/expected rate")
    current_rate: float = Field(default=0.0, description="Current observed rate")
    unit: str = Field(default="events/min", description="Unit of measurement")


class LogAnalysisResult(BaseModel):
    """Result of AI-powered log analysis."""

    service: str = Field(..., description="Analyzed service name")
    time_range: str = Field(..., description="Time range that was analyzed")
    total_logs_analyzed: int = Field(..., description="Total number of log entries processed")
    patterns: list[LogPattern] = Field(default_factory=list, description="Detected log patterns")
    anomalies: list[LogAnomaly] = Field(default_factory=list, description="Detected anomalies")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    analyzed_at: datetime = Field(..., description="When the analysis was completed")


class MetricAnalysisRequest(BaseModel):
    """Request payload for metric analysis."""

    service: str = Field(..., description="Service name to analyze metrics for")
    metric_names: list[str] = Field(
        default_factory=lambda: ["cpu_usage", "memory_usage", "request_latency_p99"],
        description="List of metric names to analyze",
    )
    time_range: str = Field(default="1h", description="Time range for metric query")
    threshold_overrides: dict[str, float] = Field(
        default_factory=dict,
        description="Custom thresholds for anomaly detection (metric_name -> threshold_value)",
    )


class MetricAnomaly(BaseModel):
    """A detected anomaly in metric data."""

    metric: str = Field(..., description="Metric name where anomaly was detected")
    type: str = Field(
        ...,
        description="Anomaly type (e.g., 'sustained_increase', 'threshold_breach', 'sudden_drop')",
    )
    description: str = Field(..., description="Human-readable anomaly description")
    severity: str = Field(
        default="medium",
        description="Anomaly severity",
        pattern="^(critical|high|medium|low)$",
    )
    started_at: datetime = Field(..., description="When the anomaly started")
    current_value: float = Field(..., description="Current metric value")
    baseline_value: float = Field(..., description="Expected baseline value")
    unit: str = Field(..., description="Unit of measurement")


class MetricCorrelation(BaseModel):
    """A detected correlation between metrics."""

    metrics: list[str] = Field(..., description="Correlated metric names")
    correlation_coefficient: float = Field(
        ...,
        description="Pearson correlation coefficient (-1.0 to 1.0)",
        ge=-1.0,
        le=1.0,
    )
    interpretation: str = Field(..., description="Human-readable interpretation of the correlation")


class AnomalyResult(BaseModel):
    """Complete anomaly analysis result for metrics."""

    service: str = Field(..., description="Analyzed service name")
    metrics_analyzed: list[str] = Field(..., description="Metrics that were analyzed")
    anomalies: list[MetricAnomaly] = Field(default_factory=list, description="Detected metric anomalies")
    correlations: list[MetricCorrelation] = Field(
        default_factory=list, description="Detected correlations between metrics"
    )
    health_score: float = Field(
        ...,
        description="Overall service health score (0.0 = unhealthy, 1.0 = healthy)",
        ge=0.0,
        le=1.0,
    )
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    analyzed_at: datetime = Field(..., description="When the analysis was completed")
