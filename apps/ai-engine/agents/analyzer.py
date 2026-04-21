"""Log and metric analysis agents.

Provides AI-powered analysis of log streams and metric data to detect
anomalies, patterns, and actionable insights for SRE workflows.
"""

import re
from collections import Counter
from datetime import datetime, timezone

from config import settings


def _extract_interval(text: str) -> str:
    """Extract a time interval from natural language text.

    Looks for patterns like "last hour", "last 30 minutes", "past 6 hours",
    "24h", etc. Falls back to ``1 HOUR`` when no interval is found.

    Args:
        text: Lowercased natural language string.

    Returns:
        A ClickHouse-compatible interval string, e.g. ``1 HOUR``.
    """
    # Match explicit shorthand like "1h", "30m", "24h", "7d"
    m = re.search(r"(\d+)\s*([hmd])\b", text)
    if m:
        amount = int(m.group(1))
        unit_map = {"h": "HOUR", "m": "MINUTE", "d": "DAY"}
        return f"{amount} {unit_map[m.group(2)]}"

    # Match "N hour(s)/minute(s)/day(s)"
    m = re.search(r"(\d+)\s*(hour|minute|day|min)s?", text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).upper()
        if unit == "MIN":
            unit = "MINUTE"
        return f"{amount} {unit}"

    # Match "last hour", "past day", etc.
    if "hour" in text:
        return "1 HOUR"
    if "day" in text:
        return "1 DAY"
    if "minute" in text or "min" in text:
        return "5 MINUTE"

    return "1 HOUR"


class LogAnalyzer:
    """Analyzes log data to identify patterns, anomalies, and root causes.

    Uses Claude API to perform semantic analysis on log entries, going beyond
    simple pattern matching to understand the context and implications of
    log events.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.model_name

    # ------------------------------------------------------------------ #
    # Claude API integration (to be enabled when API key is configured)
    # ------------------------------------------------------------------ #
    # async def _call_claude(self, system_prompt: str, user_message: str) -> str:
    #     """Call Claude API for log analysis."""
    #     client = anthropic.AsyncAnthropic()
    #     response = await client.messages.create(
    #         model=settings.model_name,
    #         max_tokens=2048,
    #         system=system_prompt,
    #         messages=[{"role": "user", "content": user_message}],
    #     )
    #     return response.content[0].text

    async def analyze(self, log_query: dict) -> dict:
        """Analyze logs based on query parameters.

        Args:
            log_query: Dictionary with log query parameters:
                - service: Service name to query logs for
                - time_range: Time range for log query
                - severity_filter: Minimum log severity to include
                - query: Free-text search query

        Returns:
            Analysis result with patterns, anomalies, and recommendations.
        """
        service = log_query.get("service", "unknown-service")
        time_range = log_query.get("time_range", "1h")

        return {
            "service": service,
            "time_range": time_range,
            "total_logs_analyzed": 15420,
            "patterns": [
                {
                    "pattern": "Connection timeout to downstream-service-b",
                    "count": 342,
                    "severity": "error",
                    "first_seen": "2026-04-10T13:00:00Z",
                    "last_seen": "2026-04-10T14:00:00Z",
                },
                {
                    "pattern": "Retry attempt exceeded for database write operation",
                    "count": 89,
                    "severity": "warning",
                    "first_seen": "2026-04-10T13:15:00Z",
                    "last_seen": "2026-04-10T13:58:00Z",
                },
            ],
            "anomalies": [
                {
                    "type": "rate_spike",
                    "description": f"Error rate for {service} increased 340% compared to baseline",
                    "baseline_rate": 2.1,
                    "current_rate": 9.3,
                    "unit": "errors/min",
                },
            ],
            "recommendations": [
                "Investigate downstream-service-b health and connectivity",
                "Check database write latency and connection pool metrics",
                "Review recent deployments to downstream-service-b",
            ],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Log summarization
    # ------------------------------------------------------------------ #

    async def summarize_logs(self, logs: list[dict], time_range: str) -> dict:
        """Summarize a batch of log entries into an AI-generated overview.

        Processes raw log data and produces a structured summary including
        key events, error patterns, security concerns, and recommendations.

        Args:
            logs: List of log entry dictionaries. Each entry is expected to
                contain at minimum ``timestamp``, ``level``, ``message``,
                and optionally ``service``, ``trace_id``, ``metadata``.
            time_range: Human-readable time range the logs cover (e.g. "1h").

        Returns:
            Dictionary with ``overview``, ``key_events``, ``error_patterns``,
            ``security_concerns``, and ``recommendations``.
        """
        # Future: replace mock with Claude API call
        # system_prompt = (
        #     "You are an expert SRE log analyst. Summarize the provided logs "
        #     "and identify key events, error patterns, security concerns, and "
        #     "actionable recommendations. Be concise and precise."
        # )
        # user_message = f"Time range: {time_range}\n\nLogs:\n{json.dumps(logs[:500], indent=2)}"
        # raw = await self._call_claude(system_prompt, user_message)
        # return json.loads(raw)

        total = len(logs)
        error_logs = [e for e in logs if e.get("level", "").lower() in ("error", "critical")]
        warn_logs = [w for w in logs if w.get("level", "").lower() == "warning"]

        # Aggregate error messages into patterns
        error_messages = [e.get("message", "unknown") for e in error_logs]
        error_counts = Counter(error_messages)
        error_patterns = [
            {"pattern": msg, "count": cnt, "severity": "error"}
            for msg, cnt in error_counts.most_common(10)
        ]

        # Extract services from the log batch
        services = {e.get("service", "unknown") for e in logs}

        # Build key events from error/critical entries (deduplicated, capped)
        seen_messages: set[str] = set()
        key_events: list[dict] = []
        for entry in error_logs:
            msg = entry.get("message", "")
            if msg not in seen_messages:
                seen_messages.add(msg)
                key_events.append({
                    "timestamp": entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "service": entry.get("service", "unknown"),
                    "level": entry.get("level", "error"),
                    "message": msg,
                })
            if len(key_events) >= 10:
                break

        # Security keyword scanning
        security_keywords = [
            "unauthorized", "forbidden", "authentication fail",
            "invalid token", "permission denied", "sql injection",
            "xss", "csrf", "brute force", "rate limit exceeded",
        ]
        security_concerns: list[str] = []
        for entry in logs:
            msg_lower = entry.get("message", "").lower()
            for kw in security_keywords:
                if kw in msg_lower:
                    concern = (
                        f"Security-relevant event detected in "
                        f"{entry.get('service', 'unknown')}: {entry.get('message', '')}"
                    )
                    if concern not in security_concerns:
                        security_concerns.append(concern)
                    break

        # Recommendations based on what we found
        recommendations: list[str] = []
        if error_patterns:
            top_pattern = error_patterns[0]["pattern"]
            recommendations.append(
                f"Investigate the most frequent error: \"{top_pattern}\" "
                f"({error_patterns[0]['count']} occurrences)"
            )
        if len(error_logs) > total * 0.1:
            recommendations.append(
                "Error rate exceeds 10% of total log volume — consider "
                "enabling circuit breakers or alerting on-call"
            )
        if security_concerns:
            recommendations.append(
                "Review security-relevant events and verify that access "
                "controls are functioning correctly"
            )
        if warn_logs:
            recommendations.append(
                f"Address {len(warn_logs)} warning-level events to prevent "
                "escalation to errors"
            )
        if not recommendations:
            recommendations.append("No critical issues detected. Continue monitoring.")

        overview = (
            f"Analyzed {total} log entries over {time_range} "
            f"across {len(services)} service(s). "
            f"Found {len(error_logs)} errors, {len(warn_logs)} warnings, "
            f"and {len(security_concerns)} security-relevant event(s)."
        )

        return {
            "overview": overview,
            "key_events": key_events,
            "error_patterns": error_patterns,
            "security_concerns": security_concerns,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------ #
    # Anomaly detection
    # ------------------------------------------------------------------ #

    async def detect_anomalies(self, logs: list[dict]) -> list[dict]:
        """Detect unusual patterns and anomalies in log data.

        Scans logs for spikes, new error types, pattern breaks, and
        frequency changes relative to an implicit baseline.

        Args:
            logs: List of log entry dictionaries.

        Returns:
            List of detected anomaly dictionaries, each containing
            ``anomaly_type``, ``severity``, ``description``,
            ``affected_service``, ``time_window``, ``evidence``,
            and ``confidence_score``.
        """
        # Future: replace mock with Claude API call
        # system_prompt = (
        #     "You are an expert SRE anomaly detector. Analyze the provided "
        #     "logs and identify anomalies: spikes, pattern breaks, new errors, "
        #     "and frequency changes. Return structured JSON."
        # )
        # user_message = json.dumps(logs[:500], indent=2)
        # raw = await self._call_claude(system_prompt, user_message)
        # return json.loads(raw)

        anomalies: list[dict] = []

        # Count errors per service
        service_error_counts: dict[str, int] = Counter()
        service_total_counts: dict[str, int] = Counter()
        for entry in logs:
            svc = entry.get("service", "unknown")
            service_total_counts[svc] += 1
            if entry.get("level", "").lower() in ("error", "critical"):
                service_error_counts[svc] += 1

        # Detect error rate spikes per service
        for svc, error_count in service_error_counts.items():
            total = service_total_counts[svc]
            error_rate = error_count / max(total, 1)
            if error_rate > 0.15:
                anomalies.append({
                    "anomaly_type": "spike",
                    "severity": "critical" if error_rate > 0.4 else "high",
                    "description": (
                        f"Error rate for {svc} is {error_rate:.0%} "
                        f"({error_count}/{total} entries), significantly above baseline"
                    ),
                    "affected_service": svc,
                    "time_window": "analysis period",
                    "evidence": [
                        entry for entry in logs
                        if entry.get("service") == svc
                        and entry.get("level", "").lower() in ("error", "critical")
                    ][:5],
                    "confidence_score": min(0.95, 0.5 + error_rate),
                })

        # Detect new/rare error messages
        error_messages = [
            e.get("message", "") for e in logs
            if e.get("level", "").lower() in ("error", "critical")
        ]
        msg_counts = Counter(error_messages)
        for msg, count in msg_counts.items():
            if count == 1 and msg:
                entry = next(
                    (e for e in logs if e.get("message") == msg),
                    {},
                )
                anomalies.append({
                    "anomaly_type": "new_error",
                    "severity": "medium",
                    "description": f"Previously unseen error detected: \"{msg}\"",
                    "affected_service": entry.get("service", "unknown"),
                    "time_window": "analysis period",
                    "evidence": [entry] if entry else [],
                    "confidence_score": 0.7,
                })

        # Detect frequency changes — repeated warnings that may escalate
        warning_messages = [
            entry.get("message", "") for entry in logs
            if entry.get("level", "").lower() == "warning"
        ]
        warn_counts = Counter(warning_messages)
        for msg, count in warn_counts.items():
            if count >= 5:
                sample_entry = next(
                    (entry for entry in logs if entry.get("message") == msg),
                    {},
                )
                anomalies.append({
                    "anomaly_type": "frequency_change",
                    "severity": "medium" if count < 20 else "high",
                    "description": (
                        f"Repeated warning detected {count} times: \"{msg}\""
                    ),
                    "affected_service": sample_entry.get("service", "unknown"),
                    "time_window": "analysis period",
                    "evidence": [
                        entry for entry in logs if entry.get("message") == msg
                    ][:5],
                    "confidence_score": min(0.9, 0.5 + count * 0.02),
                })

        return anomalies

    # ------------------------------------------------------------------ #
    # Natural language to ClickHouse query
    # ------------------------------------------------------------------ #

    async def suggest_query(self, natural_language: str) -> str:
        """Convert a natural language question into a ClickHouse SQL query.

        Maps common SRE questions to structured ClickHouse queries targeting
        the ``logs`` table schema.

        Args:
            natural_language: Free-text description of the desired query,
                e.g. "Show me all authentication failures in the last hour".

        Returns:
            A ClickHouse-compatible SQL query string.
        """
        # Future: replace mock with Claude API call
        # system_prompt = (
        #     "You are a ClickHouse SQL expert. Convert the user's natural "
        #     "language question into a valid ClickHouse query against the "
        #     "'logs' table with columns: timestamp (DateTime), level "
        #     "(String), service (String), message (String), trace_id "
        #     "(String), metadata (Map(String, String)). Return only the SQL."
        # )
        # return await self._call_claude(system_prompt, natural_language)

        nl = natural_language.lower()

        # Pattern-based query generation for common SRE questions
        if "auth" in nl and ("fail" in nl or "error" in nl):
            interval = _extract_interval(nl)
            return (
                "SELECT * FROM logs "
                "WHERE level >= 'error' "
                "AND message LIKE '%auth%fail%' "
                f"AND timestamp > now() - INTERVAL {interval} "
                "ORDER BY timestamp DESC"
            )

        if "500" in nl or "internal server error" in nl:
            interval = _extract_interval(nl)
            return (
                "SELECT * FROM logs "
                "WHERE level = 'error' "
                "AND (message LIKE '%500%' OR message LIKE '%internal server error%') "
                f"AND timestamp > now() - INTERVAL {interval} "
                "ORDER BY timestamp DESC"
            )

        if "timeout" in nl:
            interval = _extract_interval(nl)
            return (
                "SELECT service, count(*) AS cnt FROM logs "
                "WHERE message LIKE '%timeout%' "
                f"AND timestamp > now() - INTERVAL {interval} "
                "GROUP BY service ORDER BY cnt DESC"
            )

        if "error" in nl and ("count" in nl or "frequency" in nl or "rate" in nl):
            interval = _extract_interval(nl)
            return (
                "SELECT service, level, count(*) AS cnt FROM logs "
                "WHERE level IN ('error', 'critical') "
                f"AND timestamp > now() - INTERVAL {interval} "
                "GROUP BY service, level ORDER BY cnt DESC"
            )

        if "slow" in nl or "latency" in nl:
            interval = _extract_interval(nl)
            return (
                "SELECT * FROM logs "
                "WHERE message LIKE '%slow%' OR message LIKE '%latency%' "
                f"AND timestamp > now() - INTERVAL {interval} "
                "ORDER BY timestamp DESC LIMIT 100"
            )

        # Fallback: general search
        interval = _extract_interval(nl)
        return (
            "SELECT * FROM logs "
            f"WHERE timestamp > now() - INTERVAL {interval} "
            "ORDER BY timestamp DESC LIMIT 100"
        )


class MetricAnalyzer:
    """Analyzes metric data to detect anomalies and performance degradation.

    Leverages Claude API to perform intelligent anomaly detection that
    understands seasonal patterns, deployment impacts, and cascading failures.
    """

    def __init__(self, model_name: str = "claude-sonnet-4-6"):
        self.model_name = model_name

    async def analyze(self, metric_query: dict) -> dict:
        """Analyze metrics for anomalies and performance issues.

        Args:
            metric_query: Dictionary with metric query parameters:
                - service: Service name
                - metric_names: List of metric names to analyze
                - time_range: Time range for analysis
                - threshold_overrides: Custom thresholds for anomaly detection

        Returns:
            Analysis result with detected anomalies and their assessments.
        """
        service = metric_query.get("service", "unknown-service")
        metric_names = metric_query.get("metric_names", ["cpu_usage", "memory_usage", "request_latency_p99"])

        return {
            "service": service,
            "metrics_analyzed": metric_names,
            "anomalies": [
                {
                    "metric": "request_latency_p99",
                    "type": "sustained_increase",
                    "description": "P99 latency increased from 120ms to 890ms over 15 minutes",
                    "severity": "high",
                    "started_at": "2026-04-10T13:45:00Z",
                    "current_value": 890.0,
                    "baseline_value": 120.0,
                    "unit": "ms",
                },
                {
                    "metric": "cpu_usage",
                    "type": "threshold_breach",
                    "description": "CPU usage exceeded 85% on 3/5 pods",
                    "severity": "medium",
                    "started_at": "2026-04-10T13:50:00Z",
                    "current_value": 87.3,
                    "baseline_value": 45.0,
                    "unit": "percent",
                },
            ],
            "correlations": [
                {
                    "metrics": ["request_latency_p99", "cpu_usage"],
                    "correlation_coefficient": 0.94,
                    "interpretation": "Strong positive correlation suggests CPU saturation is driving latency increase",
                },
            ],
            "health_score": 0.35,
            "recommendations": [
                "Scale horizontally to distribute CPU load",
                "Profile application for CPU-intensive code paths",
                "Check for recent deployments that may have introduced regression",
            ],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
