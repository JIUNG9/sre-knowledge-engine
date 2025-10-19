"""Observability MCP tool schemas.

These tools allow Claude to query logs, metrics, traces, and dashboards
during incident investigation. Each tool is defined with its JSON Schema
input specification for the Anthropic tool_use API.
"""

OBSERVABILITY_TOOLS: list[dict] = [
    {
        "name": "query_logs",
        "description": (
            "Query application and infrastructure logs from the centralized logging system. "
            "Supports filtering by service, severity, time range, and free-text search. "
            "Returns structured log entries with timestamps, service names, and log levels."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to query logs for (e.g., 'payment-service', 'api-gateway')",
                },
                "severity": {
                    "type": "string",
                    "enum": ["debug", "info", "warning", "error", "critical"],
                    "description": "Minimum log severity level to include",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the query (e.g., '15m', '1h', '6h', '24h')",
                    "default": "1h",
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query to filter log content",
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace to scope the query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log entries to return",
                    "default": 100,
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "query_metrics",
        "description": (
            "Query time-series metrics from the monitoring system (Prometheus/SigNoz). "
            "Supports PromQL queries and predefined metric names. Returns metric values "
            "with timestamps suitable for anomaly detection and trend analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "PromQL query string (e.g., 'rate(http_requests_total{service=\"api\"}[5m])')",
                },
                "metric_name": {
                    "type": "string",
                    "description": "Predefined metric name as alternative to raw PromQL",
                },
                "service": {
                    "type": "string",
                    "description": "Service name to filter metrics by",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the query (e.g., '15m', '1h', '6h')",
                    "default": "1h",
                },
                "step": {
                    "type": "string",
                    "description": "Query resolution step (e.g., '15s', '1m', '5m')",
                    "default": "1m",
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "query_traces",
        "description": (
            "Query distributed traces to analyze request flows across services. "
            "Useful for identifying latency bottlenecks, error propagation, and "
            "understanding service dependencies during an incident."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to query traces for",
                },
                "trace_id": {
                    "type": "string",
                    "description": "Specific trace ID to look up",
                },
                "operation": {
                    "type": "string",
                    "description": "Operation/endpoint name to filter traces",
                },
                "min_duration_ms": {
                    "type": "integer",
                    "description": "Minimum trace duration in milliseconds (for slow request analysis)",
                },
                "status": {
                    "type": "string",
                    "enum": ["ok", "error"],
                    "description": "Filter traces by status",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the query",
                    "default": "1h",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of traces to return",
                    "default": 20,
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "query_signoz",
        "description": (
            "Query SigNoz observability platform for unified logs, metrics, and traces. "
            "Provides access to SigNoz-specific features like composite queries, "
            "dashboard data, and alert history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["logs", "metrics", "traces", "dashboards", "alerts"],
                    "description": "Type of SigNoz query to execute",
                },
                "query": {
                    "type": "string",
                    "description": "SigNoz query expression",
                },
                "dashboard_id": {
                    "type": "string",
                    "description": "SigNoz dashboard ID for dashboard queries",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the query",
                    "default": "1h",
                },
            },
            "required": ["query_type"],
        },
    },
]
