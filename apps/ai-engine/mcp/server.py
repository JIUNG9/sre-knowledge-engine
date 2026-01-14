"""MCP server definition for the Aegis AI Engine.

This module defines the MCP server that exposes observability, infrastructure,
and workflow tools to Claude during agent-driven investigations. The server
aggregates all tool definitions and provides a unified interface for the
AI agents to interact with external systems.

Features:
- Tool execution routing to appropriate handlers
- Claude API tool_use format conversion
- Execution audit logging with timestamps
- Token budget tracking per tool call
- Approval checking for WRITE operations
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from mcp.tools.infrastructure import INFRASTRUCTURE_TOOLS
from mcp.tools.observability import OBSERVABILITY_TOOLS
from mcp.tools.workflow import WORKFLOW_TOOLS

logger = logging.getLogger("aegis.mcp")


class ToolExecutionAuditEntry:
    """Audit log entry for a tool execution."""

    def __init__(
        self,
        tool_name: str,
        params: dict,
        result: dict | None = None,
        error: str | None = None,
        duration_ms: int = 0,
        approved: bool = True,
        investigation_id: str = "",
    ):
        self.tool_name = tool_name
        self.params = params
        self.result = result
        self.error = error
        self.duration_ms = duration_ms
        self.approved = approved
        self.investigation_id = investigation_id
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "tool_name": self.tool_name,
            "params": self.params,
            "duration_ms": self.duration_ms,
            "approved": self.approved,
            "timestamp": self.timestamp,
        }
        if self.investigation_id:
            entry["investigation_id"] = self.investigation_id
        if self.error:
            entry["error"] = self.error
            entry["status"] = "error"
        else:
            entry["status"] = "success"
        # Truncate result for audit log readability
        if self.result:
            result_str = json.dumps(self.result, default=str)
            entry["result_preview"] = (
                result_str[:500] + "..." if len(result_str) > 500 else result_str
            )
        return entry


class MCPServer:
    """MCP server that provides tools for Claude AI agents.

    The server exposes three categories of tools:
    - Observability: Query logs, metrics, traces, and SigNoz dashboards
    - Infrastructure: Read Kubernetes state, describe AWS resources, run Terraform
    - Workflow: Notify Slack, create Jira tickets, open PRs, search runbooks

    It handles tool execution routing, audit logging, and approval enforcement
    for write operations.
    """

    def __init__(self):
        self.tools: list[dict] = []
        self._audit_log: list[ToolExecutionAuditEntry] = []
        self._max_audit_entries: int = 5000
        self._pending_approvals: dict[str, dict] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all available MCP tools."""
        self.tools.extend(OBSERVABILITY_TOOLS)
        self.tools.extend(INFRASTRUCTURE_TOOLS)
        self.tools.extend(WORKFLOW_TOOLS)

    def get_tools(self) -> list[dict]:
        """Return all registered tool schemas for Claude API tool_use."""
        return self.tools

    def get_tool(self, name: str) -> dict | None:
        """Look up a single tool schema by name."""
        for tool in self.tools:
            if tool["name"] == name:
                return tool
        return None

    def get_tools_requiring_approval(self) -> list[dict]:
        """Return tools that require human approval before execution."""
        return [t for t in self.tools if t.get("requires_approval", False)]

    def get_tools_for_claude(self) -> list[dict[str, Any]]:
        """Format tools for Claude API's tool_use format.

        Converts internal tool schemas to the format expected by the
        Claude API messages endpoint. Strips internal metadata fields
        like requires_approval that are not part of the API spec.

        Returns:
            List of tool definitions in Claude API format:
            [{"name": str, "description": str, "input_schema": dict}]
        """
        claude_tools: list[dict[str, Any]] = []

        for tool in self.tools:
            claude_tool: dict[str, Any] = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            claude_tools.append(claude_tool)

        return claude_tools

    async def execute_tool(
        self,
        name: str,
        params: dict,
        investigation_id: str = "",
        skip_approval_check: bool = False,
    ) -> dict:
        """Execute a tool call by routing to the appropriate handler.

        Validates that the tool exists, checks approval requirements for
        write operations, executes the tool, and logs the result.

        Args:
            name: Tool name to execute.
            params: Tool input parameters.
            investigation_id: Optional investigation ID for audit correlation.
            skip_approval_check: If True, bypass approval for testing.

        Returns:
            Tool execution result dictionary.

        Raises:
            ValueError: If the tool name is not found.
            PermissionError: If the tool requires approval and none is granted.
        """
        tool_schema = self.get_tool(name)
        if tool_schema is None:
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check approval requirement for write tools
        requires_approval = tool_schema.get("requires_approval", False)
        if requires_approval and not skip_approval_check:
            if not self._check_approval(name, params, investigation_id):
                audit_entry = ToolExecutionAuditEntry(
                    tool_name=name,
                    params=params,
                    error="Approval required but not granted",
                    approved=False,
                    investigation_id=investigation_id,
                )
                self._record_audit(audit_entry)

                logger.warning(
                    "Tool %s requires approval (investigation=%s)",
                    name,
                    investigation_id,
                )

                return {
                    "status": "pending_approval",
                    "tool": name,
                    "message": (
                        f"Tool '{name}' requires human approval before execution. "
                        f"The proposed action has been queued for review."
                    ),
                    "params": params,
                    "approval_id": self._queue_approval(name, params, investigation_id),
                }

        # Execute the tool
        start_time = time.monotonic()
        try:
            result = await self._route_tool_execution(name, params)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            audit_entry = ToolExecutionAuditEntry(
                tool_name=name,
                params=params,
                result=result,
                duration_ms=duration_ms,
                approved=True,
                investigation_id=investigation_id,
            )
            self._record_audit(audit_entry)

            logger.info(
                "Tool %s executed successfully in %dms (investigation=%s)",
                name,
                duration_ms,
                investigation_id,
            )

            return result

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)

            audit_entry = ToolExecutionAuditEntry(
                tool_name=name,
                params=params,
                error=str(exc),
                duration_ms=duration_ms,
                investigation_id=investigation_id,
            )
            self._record_audit(audit_entry)

            logger.error(
                "Tool %s execution failed in %dms: %s",
                name,
                duration_ms,
                exc,
            )
            raise

    async def _route_tool_execution(self, name: str, params: dict) -> dict:
        """Route tool execution to the appropriate backend handler.

        Currently provides mock responses with the real routing structure
        in place. Each tool category will be connected to its actual
        backend (SigNoz API, kubectl subprocess, AWS CLI, etc.) in
        production deployment.

        Args:
            name: Tool name to execute.
            params: Tool input parameters.

        Returns:
            Tool execution result dictionary.
        """
        # Observability tools
        if name == "query_logs":
            return await self._handle_query_logs(params)
        elif name == "query_metrics":
            return await self._handle_query_metrics(params)
        elif name == "query_traces":
            return await self._handle_query_traces(params)
        elif name == "query_signoz":
            return await self._handle_query_signoz(params)

        # Infrastructure tools
        elif name == "kubectl_read":
            return await self._handle_kubectl_read(params)
        elif name == "kubectl_action":
            return await self._handle_kubectl_action(params)
        elif name == "terraform_plan":
            return await self._handle_terraform_plan(params)
        elif name == "terraform_apply":
            return await self._handle_terraform_apply(params)
        elif name == "aws_describe":
            return await self._handle_aws_describe(params)

        # Workflow tools
        elif name == "slack_notify":
            return await self._handle_slack_notify(params)
        elif name == "jira_create":
            return await self._handle_jira_create(params)
        elif name == "github_pr":
            return await self._handle_github_pr(params)
        elif name == "runbook_search":
            return await self._handle_runbook_search(params)
        elif name == "pagerduty_escalate":
            return await self._handle_pagerduty_escalate(params)

        else:
            raise ValueError(f"No handler registered for tool: {name}")

    # ------------------------------------------------------------------ #
    # Observability tool handlers (mock implementations)
    # ------------------------------------------------------------------ #

    async def _handle_query_logs(self, params: dict) -> dict:
        """Query logs from the centralized logging system."""
        service = params.get("service", "unknown")
        severity = params.get("severity", "error")
        time_range = params.get("time_range", "1h")
        return {
            "status": "success",
            "service": service,
            "time_range": time_range,
            "total_entries": 247,
            "entries": [
                {
                    "timestamp": "2026-04-10T14:23:15Z",
                    "level": "error",
                    "service": service,
                    "message": f"Connection timeout to upstream dependency after 5000ms",
                    "trace_id": "abc123def456",
                },
                {
                    "timestamp": "2026-04-10T14:23:16Z",
                    "level": "error",
                    "service": service,
                    "message": "Database connection pool exhausted (50/50 connections in use)",
                    "trace_id": "abc123def457",
                },
                {
                    "timestamp": "2026-04-10T14:23:18Z",
                    "level": "warning",
                    "service": service,
                    "message": "Retry attempt 3/3 failed for database write operation",
                    "trace_id": "abc123def458",
                },
            ],
        }

    async def _handle_query_metrics(self, params: dict) -> dict:
        """Query time-series metrics from Prometheus/SigNoz."""
        service = params.get("service", "unknown")
        return {
            "status": "success",
            "service": service,
            "metrics": [
                {
                    "name": "http_request_duration_seconds_p99",
                    "values": [
                        {"timestamp": "2026-04-10T14:20:00Z", "value": 0.12},
                        {"timestamp": "2026-04-10T14:21:00Z", "value": 0.15},
                        {"timestamp": "2026-04-10T14:22:00Z", "value": 0.45},
                        {"timestamp": "2026-04-10T14:23:00Z", "value": 2.30},
                        {"timestamp": "2026-04-10T14:24:00Z", "value": 5.10},
                    ],
                },
                {
                    "name": "http_requests_total_5xx",
                    "values": [
                        {"timestamp": "2026-04-10T14:20:00Z", "value": 2},
                        {"timestamp": "2026-04-10T14:21:00Z", "value": 5},
                        {"timestamp": "2026-04-10T14:22:00Z", "value": 23},
                        {"timestamp": "2026-04-10T14:23:00Z", "value": 89},
                        {"timestamp": "2026-04-10T14:24:00Z", "value": 156},
                    ],
                },
                {
                    "name": "db_connection_pool_usage_ratio",
                    "values": [
                        {"timestamp": "2026-04-10T14:20:00Z", "value": 0.65},
                        {"timestamp": "2026-04-10T14:21:00Z", "value": 0.82},
                        {"timestamp": "2026-04-10T14:22:00Z", "value": 0.95},
                        {"timestamp": "2026-04-10T14:23:00Z", "value": 1.00},
                        {"timestamp": "2026-04-10T14:24:00Z", "value": 1.00},
                    ],
                },
            ],
        }

    async def _handle_query_traces(self, params: dict) -> dict:
        """Query distributed traces from the tracing backend."""
        service = params.get("service", "unknown")
        return {
            "status": "success",
            "service": service,
            "traces": [
                {
                    "trace_id": "abc123def456",
                    "duration_ms": 5023,
                    "status": "error",
                    "spans": [
                        {
                            "service": "api-gateway",
                            "operation": "POST /api/v1/orders",
                            "duration_ms": 5020,
                            "status": "error",
                        },
                        {
                            "service": service,
                            "operation": "processOrder",
                            "duration_ms": 5015,
                            "status": "error",
                            "error": "Connection timeout",
                        },
                        {
                            "service": "database",
                            "operation": "INSERT orders",
                            "duration_ms": 5000,
                            "status": "error",
                            "error": "Connection pool exhausted",
                        },
                    ],
                },
            ],
        }

    async def _handle_query_signoz(self, params: dict) -> dict:
        """Query SigNoz observability platform."""
        query_type = params.get("query_type", "logs")
        return {
            "status": "success",
            "query_type": query_type,
            "data": {
                "message": f"SigNoz {query_type} query executed successfully",
                "result_count": 42,
            },
        }

    # ------------------------------------------------------------------ #
    # Infrastructure tool handlers (mock implementations)
    # ------------------------------------------------------------------ #

    async def _handle_kubectl_read(self, params: dict) -> dict:
        """Execute a read-only kubectl command."""
        command = params.get("command", "")
        namespace = params.get("namespace", "default")
        return {
            "status": "success",
            "command": f"kubectl {command} -n {namespace}",
            "output": {
                "pods": [
                    {
                        "name": "payment-service-7d4b8c9f6-x2k9m",
                        "status": "Running",
                        "restarts": 3,
                        "age": "2h",
                        "cpu": "850m",
                        "memory": "1.2Gi",
                    },
                    {
                        "name": "payment-service-7d4b8c9f6-j8n3p",
                        "status": "Running",
                        "restarts": 2,
                        "age": "2h",
                        "cpu": "920m",
                        "memory": "1.4Gi",
                    },
                    {
                        "name": "payment-service-7d4b8c9f6-q5w1r",
                        "status": "CrashLoopBackOff",
                        "restarts": 8,
                        "age": "2h",
                        "cpu": "0m",
                        "memory": "0Mi",
                    },
                ],
            },
        }

    async def _handle_kubectl_action(self, params: dict) -> dict:
        """Execute a mutating kubectl command (requires approval)."""
        command = params.get("command", "")
        namespace = params.get("namespace", "default")
        dry_run = params.get("dry_run", True)
        return {
            "status": "success",
            "command": f"kubectl {command} -n {namespace}",
            "dry_run": dry_run,
            "output": f"{'(dry-run) ' if dry_run else ''}Command executed successfully",
        }

    async def _handle_terraform_plan(self, params: dict) -> dict:
        """Execute terraform plan."""
        workspace = params.get("workspace", "")
        return {
            "status": "success",
            "workspace": workspace,
            "changes": {
                "add": 0,
                "change": 1,
                "destroy": 0,
            },
            "plan_summary": "1 resource to change (db connection pool parameter)",
        }

    async def _handle_terraform_apply(self, params: dict) -> dict:
        """Execute terraform apply (requires approval)."""
        workspace = params.get("workspace", "")
        return {
            "status": "success",
            "workspace": workspace,
            "applied": True,
            "output": "Apply complete! Resources: 0 added, 1 changed, 0 destroyed.",
        }

    async def _handle_aws_describe(self, params: dict) -> dict:
        """Describe AWS resources."""
        service = params.get("service", "")
        command = params.get("command", "")
        return {
            "status": "success",
            "service": service,
            "command": command,
            "output": {
                "message": f"AWS {service} {command} executed successfully",
            },
        }

    # ------------------------------------------------------------------ #
    # Workflow tool handlers (mock implementations)
    # ------------------------------------------------------------------ #

    async def _handle_slack_notify(self, params: dict) -> dict:
        """Send Slack notification."""
        channel = params.get("channel", "")
        return {
            "status": "success",
            "channel": channel,
            "message_ts": "1712764800.000100",
            "message": "Notification sent successfully",
        }

    async def _handle_jira_create(self, params: dict) -> dict:
        """Create a Jira ticket."""
        project = params.get("project", "")
        summary = params.get("summary", "")
        return {
            "status": "success",
            "ticket_key": f"{project}-1234",
            "summary": summary,
            "url": f"https://jira.example.com/browse/{project}-1234",
        }

    async def _handle_github_pr(self, params: dict) -> dict:
        """Create a GitHub pull request."""
        repository = params.get("repository", "")
        title = params.get("title", "")
        return {
            "status": "success",
            "pr_number": 42,
            "title": title,
            "url": f"https://github.com/{repository}/pull/42",
        }

    async def _handle_runbook_search(self, params: dict) -> dict:
        """Search runbook knowledge base."""
        query = params.get("query", "")
        return {
            "status": "success",
            "query": query,
            "results": [
                {
                    "title": "Database Connection Pool Exhaustion",
                    "relevance_score": 0.95,
                    "steps": [
                        "Check current connection pool utilization",
                        "Identify long-running queries holding connections",
                        "Increase pool size as immediate mitigation",
                        "Review application connection management code",
                    ],
                    "tags": ["database", "connection-pool", "performance"],
                },
                {
                    "title": "Cascading Failure Recovery",
                    "relevance_score": 0.82,
                    "steps": [
                        "Enable circuit breakers on upstream calls",
                        "Scale affected services horizontally",
                        "Verify recovery with gradual traffic increase",
                    ],
                    "tags": ["resilience", "circuit-breaker", "scaling"],
                },
            ],
        }

    async def _handle_pagerduty_escalate(self, params: dict) -> dict:
        """Escalate via PagerDuty."""
        policy = params.get("escalation_policy", "")
        return {
            "status": "success",
            "escalation_policy": policy,
            "incident_id": "PD-12345",
            "message": "Escalation triggered successfully",
        }

    # ------------------------------------------------------------------ #
    # Approval management
    # ------------------------------------------------------------------ #

    def _check_approval(
        self,
        tool_name: str,
        params: dict,
        investigation_id: str,
    ) -> bool:
        """Check whether a tool execution has been approved.

        Args:
            tool_name: Name of the tool requesting approval.
            params: Tool parameters.
            investigation_id: Associated investigation ID.

        Returns:
            True if approved, False if pending.
        """
        approval_key = f"{investigation_id}:{tool_name}"
        approval = self._pending_approvals.get(approval_key)
        if approval and approval.get("approved"):
            # Consume the approval
            del self._pending_approvals[approval_key]
            return True
        return False

    def _queue_approval(
        self,
        tool_name: str,
        params: dict,
        investigation_id: str,
    ) -> str:
        """Queue a tool execution for approval.

        Args:
            tool_name: Name of the tool.
            params: Tool parameters.
            investigation_id: Associated investigation ID.

        Returns:
            Approval ID for tracking.
        """
        approval_key = f"{investigation_id}:{tool_name}"
        self._pending_approvals[approval_key] = {
            "tool_name": tool_name,
            "params": params,
            "investigation_id": investigation_id,
            "approved": False,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        return approval_key

    def grant_approval(self, approval_id: str) -> bool:
        """Grant approval for a queued tool execution.

        Args:
            approval_id: The approval ID returned from queue.

        Returns:
            True if approval was granted, False if not found.
        """
        if approval_id in self._pending_approvals:
            self._pending_approvals[approval_id]["approved"] = True
            return True
        return False

    # ------------------------------------------------------------------ #
    # Audit logging
    # ------------------------------------------------------------------ #

    def _record_audit(self, entry: ToolExecutionAuditEntry) -> None:
        """Record an audit log entry.

        Maintains a rolling buffer of audit entries, evicting the oldest
        when the maximum is reached.

        Args:
            entry: The audit entry to record.
        """
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries :]

    def get_audit_log(
        self,
        limit: int = 50,
        tool_name: str | None = None,
        investigation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries with optional filtering.

        Args:
            limit: Maximum number of entries to return.
            tool_name: Filter by tool name.
            investigation_id: Filter by investigation ID.

        Returns:
            List of audit log entry dictionaries, most recent first.
        """
        entries = self._audit_log[:]
        entries.reverse()

        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        if investigation_id:
            entries = [
                e for e in entries if e.investigation_id == investigation_id
            ]

        return [e.to_dict() for e in entries[:limit]]

    def get_audit_stats(self) -> dict[str, Any]:
        """Return aggregate statistics from the audit log.

        Returns:
            Dictionary with total executions, errors, and per-tool counts.
        """
        total = len(self._audit_log)
        errors = sum(1 for e in self._audit_log if e.error)
        denied = sum(1 for e in self._audit_log if not e.approved)

        tool_counts: dict[str, int] = {}
        for entry in self._audit_log:
            tool_counts[entry.tool_name] = tool_counts.get(entry.tool_name, 0) + 1

        avg_duration = 0.0
        durations = [e.duration_ms for e in self._audit_log if e.duration_ms > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)

        return {
            "total_executions": total,
            "total_errors": errors,
            "total_denied": denied,
            "average_duration_ms": round(avg_duration, 1),
            "tool_execution_counts": tool_counts,
        }


# Singleton instance
mcp_server = MCPServer()
