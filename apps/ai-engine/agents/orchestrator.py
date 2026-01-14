"""LangGraph-based multi-agent orchestration for incident investigation.

Coordinates the full investigation lifecycle using a state machine:
    receive_alert -> gather_context -> investigate -> generate_rca ->
    propose_remediation -> await_approval

Each state uses Claude API with specific system prompts tailored to that
phase of the investigation. MCP tools are used to gather observability
data and inspect infrastructure state.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import anthropic

from config import settings
from mcp.server import MCPServer
from services.token_tracker import TokenTracker

logger = logging.getLogger("aegis.orchestrator")


class InvestigationState(str, Enum):
    """States in the investigation state machine."""

    RECEIVE_ALERT = "receive_alert"
    GATHER_CONTEXT = "gather_context"
    INVESTIGATE = "investigate"
    GENERATE_RCA = "generate_rca"
    PROPOSE_REMEDIATION = "propose_remediation"
    AWAIT_APPROVAL = "await_approval"
    COMPLETED = "completed"
    FAILED = "failed"


# State transition map
STATE_TRANSITIONS: dict[InvestigationState, InvestigationState] = {
    InvestigationState.RECEIVE_ALERT: InvestigationState.GATHER_CONTEXT,
    InvestigationState.GATHER_CONTEXT: InvestigationState.INVESTIGATE,
    InvestigationState.INVESTIGATE: InvestigationState.GENERATE_RCA,
    InvestigationState.GENERATE_RCA: InvestigationState.PROPOSE_REMEDIATION,
    InvestigationState.PROPOSE_REMEDIATION: InvestigationState.AWAIT_APPROVAL,
    InvestigationState.AWAIT_APPROVAL: InvestigationState.COMPLETED,
}

# System prompts for each investigation phase
SYSTEM_PROMPTS: dict[InvestigationState, str] = {
    InvestigationState.GATHER_CONTEXT: (
        "You are an expert SRE performing initial triage of a production incident. "
        "Your goal is to gather context about the incident by:\n"
        "1. Identifying the affected services and their dependencies\n"
        "2. Determining the blast radius and user impact\n"
        "3. Checking for recent deployments or configuration changes\n"
        "4. Establishing a preliminary timeline\n\n"
        "Use the available tools to query logs, metrics, and infrastructure state. "
        "Be systematic and thorough in your data gathering."
    ),
    InvestigationState.INVESTIGATE: (
        "You are an expert SRE performing deep investigation of a production incident. "
        "You have initial context from the triage phase. Now you need to:\n"
        "1. Query detailed logs around the incident timeframe to find error patterns\n"
        "2. Check metrics for anomalies (latency spikes, error rate increases, resource exhaustion)\n"
        "3. Trace request flows to identify where failures originate\n"
        "4. Inspect Kubernetes pod/deployment state for the affected services\n"
        "5. Check for correlated infrastructure events (node issues, network problems)\n\n"
        "Use the available tools systematically. Start with the most likely failure points "
        "and expand your investigation based on what you find. Document your reasoning."
    ),
    InvestigationState.GENERATE_RCA: (
        "You are an expert SRE generating a root cause analysis for a production incident. "
        "Based on the investigation data gathered, you need to:\n"
        "1. Identify the primary root cause with supporting evidence\n"
        "2. Determine contributing factors\n"
        "3. Build a complete incident timeline\n"
        "4. Assess the confidence level of your analysis\n"
        "5. Identify what additional data would increase confidence\n\n"
        "Respond with a structured JSON object containing:\n"
        "- root_cause: {category, description, evidence[]}\n"
        "- contributing_factors: [{factor, description}]\n"
        "- timeline: [{time, event, source}]\n"
        "- confidence_score: float between 0.0 and 1.0\n"
        "- data_gaps: string[] of missing information"
    ),
    InvestigationState.PROPOSE_REMEDIATION: (
        "You are an expert SRE proposing remediation for a production incident. "
        "Based on the root cause analysis, propose specific, actionable steps to:\n"
        "1. Mitigate the immediate impact (quick fixes)\n"
        "2. Resolve the root cause (permanent fixes)\n"
        "3. Prevent recurrence (preventive measures)\n\n"
        "For each remediation step, provide:\n"
        "- description: What needs to be done\n"
        "- command: The exact command or change (kubectl, terraform, config change)\n"
        "- risk_level: low, medium, or high\n"
        "- requires_approval: boolean (true for medium/high risk)\n"
        "- estimated_impact: What improvement is expected\n"
        "- category: immediate_mitigation, root_cause_fix, or prevention\n\n"
        "Respond with a JSON object containing:\n"
        "- remediation_steps: [{description, command, risk_level, requires_approval, "
        "estimated_impact, category}]\n"
        "- estimated_recovery_time: string\n"
        "- rollback_plan: string"
    ),
}


class IncidentOrchestrator:
    """Orchestrates incident investigation using Claude API and MCP tools.

    Coordinates a multi-step investigation workflow where each phase uses
    Claude with specific system prompts and MCP tools to gather data,
    analyze findings, and propose remediations.
    """

    def __init__(self):
        self.model = settings.model_name or "claude-sonnet-4-6"
        self.mcp_server = MCPServer()
        self.token_tracker = TokenTracker()
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    @property
    def api_available(self) -> bool:
        """Check whether the Anthropic API key is configured."""
        return bool(settings.anthropic_api_key)

    async def investigate(self, incident_context: dict) -> dict:
        """Run a full investigation workflow.

        Multi-step investigation:
        1. Receive and validate the alert
        2. Gather context using MCP tools (logs, metrics, infrastructure)
        3. Deep investigation with Claude reasoning
        4. Generate root cause analysis
        5. Propose remediation steps

        Args:
            incident_context: Dictionary containing incident details:
                - incident_id: Unique identifier
                - alert_data: Raw alert payload
                - severity: critical/high/medium/low
                - affected_services: List of impacted services
                - title: Short description
                - description: Detailed description

        Returns:
            Complete investigation result with RCA, remediation, and token usage.
        """
        investigation_id = incident_context.get("incident_id", str(uuid.uuid4()))
        start_time = time.monotonic()

        logger.info(
            "Starting investigation %s (severity=%s, services=%s)",
            investigation_id,
            incident_context.get("severity", "unknown"),
            incident_context.get("affected_services", []),
        )

        if not self.api_available:
            logger.warning(
                "ANTHROPIC_API_KEY not set; falling back to mock investigation "
                "for %s",
                investigation_id,
            )
            return self._mock_investigation(incident_context, start_time)

        self.token_tracker.start_tracking(investigation_id, self.model)

        try:
            # Phase 1: Gather context
            logger.info("[%s] Phase: gather_context", investigation_id)
            context_result = await self._run_phase(
                investigation_id=investigation_id,
                state=InvestigationState.GATHER_CONTEXT,
                incident_context=incident_context,
                previous_findings=None,
            )

            # Phase 2: Deep investigation
            logger.info("[%s] Phase: investigate", investigation_id)
            investigation_result = await self._run_phase(
                investigation_id=investigation_id,
                state=InvestigationState.INVESTIGATE,
                incident_context=incident_context,
                previous_findings=context_result,
            )

            # Phase 3: Generate RCA
            logger.info("[%s] Phase: generate_rca", investigation_id)
            rca_result = await self._run_phase(
                investigation_id=investigation_id,
                state=InvestigationState.GENERATE_RCA,
                incident_context=incident_context,
                previous_findings=investigation_result,
            )

            # Phase 4: Propose remediation
            logger.info("[%s] Phase: propose_remediation", investigation_id)
            remediation_result = await self._run_phase(
                investigation_id=investigation_id,
                state=InvestigationState.PROPOSE_REMEDIATION,
                incident_context=incident_context,
                previous_findings=rca_result,
            )

            # Finalize token tracking
            usage_record = self.token_tracker.finish_tracking(investigation_id)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            result = self._build_result(
                incident_context=incident_context,
                rca_result=rca_result,
                remediation_result=remediation_result,
                duration_ms=duration_ms,
                usage_record=usage_record,
            )

            logger.info(
                "[%s] Investigation completed in %dms (api_calls=%d, tokens=%d)",
                investigation_id,
                duration_ms,
                usage_record.api_calls if usage_record else 0,
                usage_record.usage.total_tokens if usage_record else 0,
            )

            return result

        except anthropic.APIError as exc:
            logger.error(
                "[%s] Claude API error during investigation: %s",
                investigation_id,
                exc,
            )
            self.token_tracker.finish_tracking(investigation_id)
            return self._error_result(
                incident_context,
                f"Claude API error: {exc}",
                start_time,
            )
        except Exception as exc:
            logger.exception(
                "[%s] Unexpected error during investigation",
                investigation_id,
            )
            self.token_tracker.finish_tracking(investigation_id)
            return self._error_result(
                incident_context,
                f"Investigation failed: {exc}",
                start_time,
            )

    async def _run_phase(
        self,
        investigation_id: str,
        state: InvestigationState,
        incident_context: dict,
        previous_findings: str | None,
    ) -> str:
        """Run a single investigation phase with Claude API.

        Uses the tool-use loop pattern: sends the request to Claude, processes
        any tool calls, and continues until Claude produces a final text response.

        Args:
            investigation_id: Investigation identifier for tracking.
            state: Current investigation state/phase.
            incident_context: Original incident details.
            previous_findings: Text output from previous phases.

        Returns:
            Claude's text response for this phase.
        """
        system_prompt = SYSTEM_PROMPTS.get(state, "You are an expert SRE.")

        # Build the user message with incident context and previous findings
        user_content = f"Incident context:\n{json.dumps(incident_context, indent=2)}"
        if previous_findings:
            user_content += f"\n\nFindings from previous investigation phases:\n{previous_findings}"

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_content},
        ]

        tools = self._format_tools()

        # Initial API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Track token usage
        self.token_tracker.record_api_call(
            investigation_id=investigation_id,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cached_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            ) or 0,
        )

        # Tool-use loop: continue until Claude stops requesting tools
        while response.stop_reason == "tool_use":
            # Extract tool use blocks from the response
            tool_use_blocks = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            # Execute each tool call
            tool_results = await self._execute_tools(tool_use_blocks)

            # Build the assistant message (Claude's response) and tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            logger.debug(
                "[%s][%s] Executed %d tool calls, continuing conversation",
                investigation_id,
                state.value,
                len(tool_use_blocks),
            )

            # Continue the conversation
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            # Track token usage for continuation
            self.token_tracker.record_api_call(
                investigation_id=investigation_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cached_input_tokens=getattr(
                    response.usage, "cache_read_input_tokens", 0
                ) or 0,
            )

        # Extract the final text response
        return self._extract_text(response)

    def _format_tools(self) -> list[dict[str, Any]]:
        """Convert MCP tool schemas to Claude API tool format.

        The MCP tools use `input_schema` for their parameter definitions.
        Claude API expects tools in the format:
        {
            "name": str,
            "description": str,
            "input_schema": {JSON Schema}
        }

        Returns:
            List of tool definitions formatted for Claude API.
        """
        claude_tools: list[dict[str, Any]] = []

        for tool in self.mcp_server.get_tools():
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            claude_tools.append(claude_tool)

        return claude_tools

    async def _execute_tools(
        self,
        tool_use_blocks: list,
    ) -> list[dict[str, Any]]:
        """Execute tool calls from Claude's response and return results.

        Routes each tool call to the MCP server for execution. Currently
        uses mock responses with the real routing structure in place for
        when MCP tool backends are connected.

        Args:
            tool_use_blocks: List of ToolUseBlock objects from Claude's response.

        Returns:
            List of tool_result content blocks for the next API call.
        """
        tool_results: list[dict[str, Any]] = []

        for block in tool_use_blocks:
            tool_name = block.name
            tool_input = block.input
            tool_use_id = block.id

            logger.info(
                "Executing tool: %s (params=%s)",
                tool_name,
                json.dumps(tool_input, default=str)[:200],
            )

            try:
                result = await self._route_tool_call(tool_name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result, default=str),
                })
            except Exception as exc:
                logger.error("Tool execution failed for %s: %s", tool_name, exc)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps({
                        "error": str(exc),
                        "tool": tool_name,
                    }),
                    "is_error": True,
                })

        return tool_results

    async def _route_tool_call(self, name: str, params: dict) -> dict:
        """Route a tool call to the appropriate MCP handler.

        This method delegates to the MCP server's execute_tool method,
        which handles routing to the correct backend (observability,
        infrastructure, or workflow).

        Args:
            name: Tool name to execute.
            params: Tool input parameters.

        Returns:
            Tool execution result as a dictionary.
        """
        return await self.mcp_server.execute_tool(name, params)

    def _extract_text(self, response: Any) -> str:
        """Extract text content from Claude's response.

        Args:
            response: Claude API message response.

        Returns:
            Concatenated text from all TextBlock content blocks.
        """
        text_parts: list[str] = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _parse_investigation_result(self, response: Any) -> dict:
        """Extract structured result from Claude's response.

        Attempts to parse JSON from Claude's text response. Falls back to
        wrapping the raw text if JSON parsing fails.

        Args:
            response: Claude API message response.

        Returns:
            Parsed investigation result dictionary.
        """
        text = self._extract_text(response)

        # Try to extract JSON from the response (Claude may wrap it in markdown)
        json_start = text.find("{")
        json_end = text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return {"raw_analysis": text}

    def _build_result(
        self,
        incident_context: dict,
        rca_result: str,
        remediation_result: str,
        duration_ms: int,
        usage_record: Any,
    ) -> dict:
        """Build the final investigation result from phase outputs.

        Parses the RCA and remediation phase outputs and assembles them
        into the standard InvestigationResult format.

        Args:
            incident_context: Original incident data.
            rca_result: Raw text from the RCA phase.
            remediation_result: Raw text from the remediation phase.
            duration_ms: Total investigation duration in milliseconds.
            usage_record: Token usage record from the tracker.

        Returns:
            Complete investigation result dictionary.
        """
        incident_id = incident_context.get("incident_id", "unknown")
        severity = incident_context.get("severity", "medium")
        affected_services = incident_context.get("affected_services", [])

        # Parse RCA JSON from Claude's response
        rca = self._try_parse_json(rca_result)
        remediation = self._try_parse_json(remediation_result)

        # Extract root cause
        root_cause = rca.get("root_cause", {})
        if not root_cause:
            root_cause = {
                "category": "under_investigation",
                "description": rca.get("raw_analysis", rca_result[:500]),
                "evidence": rca.get("evidence", []),
            }

        # Extract timeline
        timeline = rca.get("timeline", [])

        # Extract remediation steps
        remediation_steps = remediation.get("remediation_steps", [])
        proposed_remediation = []
        for step in remediation_steps:
            proposed_remediation.append({
                "action": step.get("description", step.get("action", "")),
                "command": step.get("command", ""),
                "risk": step.get("risk_level", "medium"),
                "requires_approval": step.get("requires_approval", True),
                "estimated_impact": step.get("estimated_impact", ""),
            })

        # Build token usage summary
        token_usage = {}
        if usage_record:
            token_usage = usage_record.usage.to_dict()

        # Build summary from RCA
        summary = rca.get("summary", "")
        if not summary:
            summary = (
                f"Investigation of incident {incident_id} completed. "
                f"Root cause: {root_cause.get('description', 'See detailed analysis.')}"
            )

        return {
            "incident_id": incident_id,
            "status": "completed",
            "summary": summary,
            "root_cause": root_cause,
            "affected_services": affected_services or rca.get("affected_services", []),
            "timeline": timeline,
            "proposed_remediation": proposed_remediation,
            "confidence_score": rca.get("confidence_score", 0.75),
            "severity": severity,
            "investigated_at": datetime.now(timezone.utc).isoformat(),
            "token_usage": token_usage,
            "duration_ms": duration_ms,
        }

    def _try_parse_json(self, text: str) -> dict:
        """Attempt to parse JSON from a text string.

        Handles cases where JSON is embedded in markdown code blocks
        or surrounded by explanatory text.

        Args:
            text: Raw text that may contain JSON.

        Returns:
            Parsed dictionary, or dict with raw_analysis key on failure.
        """
        # Try direct parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        if not isinstance(text, str):
            return {"raw_analysis": str(text)}

        # Try to find JSON block in markdown
        for marker in ("```json", "```"):
            start = text.find(marker)
            if start >= 0:
                start = text.find("\n", start) + 1
                end = text.find("```", start)
                if end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        pass

        # Try to find a JSON object
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return {"raw_analysis": text[:2000]}

    def _mock_investigation(self, incident_context: dict, start_time: float) -> dict:
        """Return a mock investigation result when API key is not available.

        Provides a realistic-looking result for development and testing
        without making actual API calls.

        Args:
            incident_context: Original incident data.
            start_time: Monotonic clock start time for duration calculation.

        Returns:
            Mock investigation result.
        """
        incident_id = incident_context.get("incident_id", "unknown")
        severity = incident_context.get("severity", "medium")
        affected_services = incident_context.get("affected_services", [])
        duration_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "incident_id": incident_id,
            "status": "completed",
            "summary": (
                f"Investigation of incident {incident_id} completed (mock mode). "
                f"Elevated error rates detected in "
                f"{', '.join(affected_services) if affected_services else 'affected services'}. "
                f"Root cause identified as cascading failure originating from "
                f"upstream dependency timeout."
            ),
            "root_cause": {
                "category": "dependency_failure",
                "description": (
                    "Upstream payment service experienced increased latency "
                    "(p99 > 5s) due to database connection pool exhaustion, "
                    "causing cascading timeouts in downstream services."
                ),
                "evidence": [
                    "Error rate spike correlates with payment-service latency "
                    "increase at 14:23 UTC",
                    "Database connection pool utilization reached 100% at 14:21 UTC",
                    "Downstream services began returning 503s at 14:24 UTC",
                ],
            },
            "affected_services": (
                affected_services
                or ["payment-service", "order-service", "api-gateway"]
            ),
            "timeline": [
                {
                    "time": "14:21 UTC",
                    "event": "DB connection pool exhaustion detected",
                },
                {
                    "time": "14:23 UTC",
                    "event": "Payment service p99 latency exceeds 5s",
                },
                {
                    "time": "14:24 UTC",
                    "event": "Cascading 503 errors in downstream services",
                },
                {
                    "time": "14:25 UTC",
                    "event": "Alert triggered by monitoring system",
                },
            ],
            "proposed_remediation": [
                {
                    "action": "Increase database connection pool size from 50 to 100",
                    "command": "kubectl set env deployment/payment-service DB_POOL_SIZE=100 -n production",
                    "risk": "low",
                    "requires_approval": False,
                    "estimated_impact": "Restore connection availability",
                },
                {
                    "action": "Add circuit breaker to payment-service upstream calls",
                    "command": "",
                    "risk": "medium",
                    "requires_approval": True,
                    "estimated_impact": "Prevent cascading failures",
                },
                {
                    "action": "Scale payment-service horizontally (3 -> 5 replicas)",
                    "command": "kubectl scale deployment/payment-service --replicas=5 -n production",
                    "risk": "low",
                    "requires_approval": False,
                    "estimated_impact": "Distribute load across more instances",
                },
            ],
            "confidence_score": 0.87,
            "severity": severity,
            "investigated_at": datetime.now(timezone.utc).isoformat(),
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_input_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
            "duration_ms": duration_ms,
        }

    def _error_result(
        self,
        incident_context: dict,
        error_message: str,
        start_time: float,
    ) -> dict:
        """Build an error result when investigation fails.

        Args:
            incident_context: Original incident data.
            error_message: Description of what went wrong.
            start_time: Monotonic clock start time for duration calculation.

        Returns:
            Investigation result with failed status.
        """
        incident_id = incident_context.get("incident_id", "unknown")
        duration_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "incident_id": incident_id,
            "status": "failed",
            "summary": f"Investigation failed: {error_message}",
            "root_cause": {
                "category": "investigation_error",
                "description": error_message,
                "evidence": [],
            },
            "affected_services": incident_context.get("affected_services", []),
            "timeline": [],
            "proposed_remediation": [],
            "confidence_score": 0.0,
            "severity": incident_context.get("severity", "medium"),
            "investigated_at": datetime.now(timezone.utc).isoformat(),
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_input_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
            "duration_ms": duration_ms,
        }
