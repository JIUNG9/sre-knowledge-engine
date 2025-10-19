"""Analysis endpoints for logs and metrics.

Provides AI-powered analysis of log streams and metric data to detect
anomalies, patterns, and actionable insights. These endpoints are used
by the Aegis dashboard to surface intelligent observability insights.
"""

from fastapi import APIRouter

from agents.analyzer import LogAnalyzer, MetricAnalyzer
from models.analysis import AnomalyResult, LogAnalysisRequest, LogAnalysisResult

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])

log_analyzer = LogAnalyzer()
metric_analyzer = MetricAnalyzer()


@router.post("/logs", response_model=LogAnalysisResult)
async def analyze_logs(request: LogAnalysisRequest) -> LogAnalysisResult:
    """Analyze logs for a service and return patterns and anomalies.

    Uses AI to perform semantic analysis on log entries, identifying:
    - Recurring error patterns and their frequency
    - Anomalous log rate changes compared to baseline
    - New error types not seen in the historical window
    - Correlated log events across dependent services

    Future Claude API integration:
        The log analyzer will use Claude to understand log semantics,
        classify error types, and correlate events across services.
        It goes beyond regex pattern matching to understand the context
        and implications of log events.
    """
    result = await log_analyzer.analyze(request.model_dump())
    return LogAnalysisResult(**result)


@router.post("/metrics", response_model=AnomalyResult)
async def analyze_metrics(request: MetricAnalysisRequest) -> AnomalyResult:
    """Analyze metrics for a service and detect anomalies.

    Uses AI to perform intelligent anomaly detection that understands:
    - Seasonal patterns (daily/weekly traffic cycles)
    - Deployment impact windows
    - Cascading failure signatures across service metrics
    - Correlation between different metric dimensions

    Returns detected anomalies with severity assessment, metric correlations,
    an overall health score, and actionable recommendations.

    Future Claude API integration:
        The metric analyzer will use Claude to interpret metric patterns,
        distinguish genuine anomalies from expected variations, and provide
        context-aware recommendations based on the service architecture.
    """
    result = await metric_analyzer.analyze(request.model_dump())
    return AnomalyResult(**result)
