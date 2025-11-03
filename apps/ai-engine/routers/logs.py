"""Log analysis endpoints for AI-powered log intelligence.

Provides endpoints for log summarization, natural language query translation,
and anomaly detection. These are consumed by the Aegis dashboard to deliver
AI-native observability features to SRE teams.
"""

from fastapi import APIRouter

from agents.analyzer import LogAnalyzer
from models.logs import (
    AnomalyDetectionRequest,
    DetectedAnomaly,
    LogSummarizeRequest,
    LogSummary,
    NaturalLanguageQueryRequest,
    StructuredQuery,
)

router = APIRouter(prefix="/api/v1/ai/logs", tags=["log-intelligence"])

log_analyzer = LogAnalyzer()


@router.post("/summarize", response_model=LogSummary)
async def summarize_logs(request: LogSummarizeRequest) -> LogSummary:
    """Summarize a batch of log entries using AI analysis.

    Accepts raw log data and returns a structured summary including:
    - **overview**: 2-3 sentence high-level summary
    - **key_events**: Significant events with timestamps
    - **error_patterns**: Grouped errors with frequency counts
    - **security_concerns**: Any security-relevant findings
    - **recommendations**: Suggested follow-up actions

    Future Claude API integration:
        Will use Claude to perform semantic summarization, understanding
        log context, causal relationships between events, and producing
        human-quality narrative summaries.
    """
    result = await log_analyzer.summarize_logs(
        logs=request.logs,
        time_range=request.time_range,
    )
    return LogSummary(**result)


@router.post("/query", response_model=StructuredQuery)
async def translate_query(request: NaturalLanguageQueryRequest) -> StructuredQuery:
    """Convert a natural language question into a ClickHouse query.

    Accepts a free-text question like "Show me all authentication failures
    in the last hour" and returns a structured ClickHouse SQL query with
    an explanation.

    The query targets the ``logs`` table with columns:
    ``timestamp``, ``level``, ``service``, ``message``, ``trace_id``,
    ``metadata``.

    Future Claude API integration:
        Will use Claude to handle arbitrary natural language queries with
        full understanding of ClickHouse SQL dialect, log schema, and
        service topology.
    """
    query_str = await log_analyzer.suggest_query(request.query)

    # Generate a human-readable explanation based on the query
    explanation = _explain_query(request.query, query_str)

    return StructuredQuery(
        query=query_str,
        explanation=explanation,
    )


@router.post("/anomalies", response_model=list[DetectedAnomaly])
async def detect_anomalies(request: AnomalyDetectionRequest) -> list[DetectedAnomaly]:
    """Detect anomalies in log data.

    Scans the provided log entries for unusual patterns and returns a list
    of detected anomalies, each containing:
    - **anomaly_type**: spike, pattern_break, new_error, or frequency_change
    - **severity**: critical, high, medium, or low
    - **description**: Human-readable explanation
    - **affected_service**: Which service is impacted
    - **time_window**: When the anomaly was observed
    - **evidence**: Specific log entries supporting the detection
    - **confidence_score**: 0.0 to 1.0 confidence rating

    Future Claude API integration:
        Will use Claude to perform semantic anomaly detection that
        understands the meaning of log messages, correlates events across
        services, and detects subtle pattern shifts that rule-based systems
        would miss.
    """
    raw_anomalies = await log_analyzer.detect_anomalies(request.logs)
    return [DetectedAnomaly(**a) for a in raw_anomalies]


def _explain_query(natural_language: str, query: str) -> str:
    """Generate a human-readable explanation of the generated query.

    Args:
        natural_language: The original natural language question.
        query: The generated ClickHouse SQL query.

    Returns:
        A concise explanation string.
    """
    nl = natural_language.lower()

    if "auth" in nl and ("fail" in nl or "error" in nl):
        return (
            "Filtering for error-level logs with authentication failure "
            "patterns in the requested time window"
        )

    if "500" in nl or "internal server error" in nl:
        return (
            "Searching for HTTP 500 / internal server error entries "
            "in the requested time window"
        )

    if "timeout" in nl:
        return (
            "Counting timeout occurrences grouped by service "
            "in the requested time window"
        )

    if "error" in nl and ("count" in nl or "frequency" in nl or "rate" in nl):
        return (
            "Aggregating error and critical log counts by service and level "
            "in the requested time window"
        )

    if "slow" in nl or "latency" in nl:
        return (
            "Searching for log entries mentioning slow responses or latency "
            "in the requested time window"
        )

    return (
        "Retrieving recent log entries matching the requested criteria, "
        "ordered by timestamp descending"
    )
