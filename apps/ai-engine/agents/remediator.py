"""Remediation proposal agent.

Generates specific, actionable remediation steps for incidents based on
root cause analysis. Each step includes the exact command or change needed,
risk assessment, and approval requirements.

Remediation categories:
- Kubernetes: kubectl commands for pod/deployment/service issues
- Terraform: Infrastructure changes for cloud resource issues
- Configuration: Application config changes
- Code: Fix suggestions with PR creation guidance
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import anthropic

from config import settings
from services.token_tracker import TokenTracker

logger = logging.getLogger("aegis.remediator")


REMEDIATION_SYSTEM_PROMPT = (
    "You are an expert SRE generating remediation plans for production incidents. "
    "Based on the root cause analysis and incident context, generate specific, "
    "actionable remediation steps.\n\n"
    "For each step, provide:\n"
    "1. description: Clear explanation of what needs to be done\n"
    "2. command: The exact command to execute (kubectl, terraform, aws cli, etc.)\n"
    "3. risk_level: 'low' (read-only or easily reversible), 'medium' (state change "
    "with rollback), or 'high' (destructive or hard to reverse)\n"
    "4. requires_approval: true for medium/high risk actions\n"
    "5. estimated_impact: What improvement to expect\n"
    "6. category: 'immediate_mitigation', 'root_cause_fix', or 'prevention'\n"
    "7. rollback_command: Command to undo this step if needed\n\n"
    "Prioritize steps by urgency: immediate mitigation first, then root cause fixes, "
    "then prevention. Always include rollback plans for risky operations.\n\n"
    "Respond with valid JSON in this format:\n"
    "{\n"
    '  "remediation_steps": [\n'
    "    {\n"
    '      "description": "...",\n'
    '      "command": "...",\n'
    '      "risk_level": "low|medium|high",\n'
    '      "requires_approval": true|false,\n'
    '      "estimated_impact": "...",\n'
    '      "category": "immediate_mitigation|root_cause_fix|prevention",\n'
    '      "rollback_command": "..."\n'
    "    }\n"
    "  ],\n"
    '  "estimated_recovery_time": "...",\n'
    '  "rollback_plan": "...",\n'
    '  "post_incident_actions": ["..."]\n'
    "}"
)

# Templates for common remediation patterns
KUBERNETES_TEMPLATES: dict[str, dict[str, Any]] = {
    "scale_deployment": {
        "description": "Scale deployment to handle increased load",
        "command": "kubectl scale deployment/{name} --replicas={replicas} -n {namespace}",
        "risk_level": "low",
        "requires_approval": False,
        "category": "immediate_mitigation",
    },
    "restart_deployment": {
        "description": "Rolling restart deployment to recover from bad state",
        "command": "kubectl rollout restart deployment/{name} -n {namespace}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "immediate_mitigation",
    },
    "rollback_deployment": {
        "description": "Rollback deployment to previous revision",
        "command": "kubectl rollout undo deployment/{name} -n {namespace}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "root_cause_fix",
    },
    "update_resource_limits": {
        "description": "Update resource limits/requests for pods",
        "command": "kubectl set resources deployment/{name} --limits=cpu={cpu},memory={memory} -n {namespace}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "root_cause_fix",
    },
    "cordon_node": {
        "description": "Cordon a problematic node to prevent scheduling",
        "command": "kubectl cordon {node_name}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "immediate_mitigation",
    },
}

TERRAFORM_TEMPLATES: dict[str, dict[str, Any]] = {
    "scale_rds": {
        "description": "Scale RDS instance class to handle connection load",
        "command": "terraform apply -target=aws_db_instance.{name} -var='instance_class={class}'",
        "risk_level": "high",
        "requires_approval": True,
        "category": "root_cause_fix",
    },
    "increase_connection_pool": {
        "description": "Increase RDS max connections parameter",
        "command": "terraform apply -target=aws_db_parameter_group.{name}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "root_cause_fix",
    },
    "scale_asg": {
        "description": "Increase Auto Scaling Group desired capacity",
        "command": "terraform apply -target=aws_autoscaling_group.{name} -var='desired_capacity={count}'",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "immediate_mitigation",
    },
}

CONFIG_TEMPLATES: dict[str, dict[str, Any]] = {
    "circuit_breaker": {
        "description": "Enable circuit breaker for upstream service calls",
        "command": "kubectl set env deployment/{name} CIRCUIT_BREAKER_ENABLED=true CIRCUIT_BREAKER_THRESHOLD={threshold} -n {namespace}",
        "risk_level": "low",
        "requires_approval": False,
        "category": "immediate_mitigation",
    },
    "connection_pool_size": {
        "description": "Adjust database connection pool size",
        "command": "kubectl set env deployment/{name} DB_POOL_SIZE={size} -n {namespace}",
        "risk_level": "low",
        "requires_approval": False,
        "category": "root_cause_fix",
    },
    "timeout_adjustment": {
        "description": "Adjust request timeout thresholds",
        "command": "kubectl set env deployment/{name} REQUEST_TIMEOUT_MS={timeout} -n {namespace}",
        "risk_level": "low",
        "requires_approval": False,
        "category": "immediate_mitigation",
    },
    "rate_limit": {
        "description": "Adjust rate limiting thresholds",
        "command": "kubectl set env deployment/{name} RATE_LIMIT_RPS={rps} -n {namespace}",
        "risk_level": "medium",
        "requires_approval": True,
        "category": "immediate_mitigation",
    },
}


class RemediationStep:
    """A single remediation action with metadata."""

    def __init__(
        self,
        description: str,
        command: str,
        risk_level: str = "medium",
        requires_approval: bool = True,
        estimated_impact: str = "",
        category: str = "root_cause_fix",
        rollback_command: str = "",
    ):
        self.description = description
        self.command = command
        self.risk_level = risk_level
        self.requires_approval = requires_approval
        self.estimated_impact = estimated_impact
        self.category = category
        self.rollback_command = rollback_command

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "command": self.command,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "estimated_impact": self.estimated_impact,
            "category": self.category,
            "rollback_command": self.rollback_command,
        }


class RemediationPlan:
    """Complete remediation plan for an incident."""

    def __init__(
        self,
        incident_id: str,
        steps: list[RemediationStep] | None = None,
        estimated_recovery_time: str = "",
        rollback_plan: str = "",
        post_incident_actions: list[str] | None = None,
    ):
        self.incident_id = incident_id
        self.steps = steps or []
        self.estimated_recovery_time = estimated_recovery_time
        self.rollback_plan = rollback_plan
        self.post_incident_actions = post_incident_actions or []
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "remediation_steps": [s.to_dict() for s in self.steps],
            "estimated_recovery_time": self.estimated_recovery_time,
            "rollback_plan": self.rollback_plan,
            "post_incident_actions": self.post_incident_actions,
            "created_at": self.created_at,
            "total_steps": len(self.steps),
            "steps_requiring_approval": sum(
                1 for s in self.steps if s.requires_approval
            ),
            "risk_summary": self._risk_summary(),
        }

    def _risk_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        for step in self.steps:
            counts[step.risk_level] = counts.get(step.risk_level, 0) + 1
        return counts


class RemediationAgent:
    """Agent that generates context-aware remediation proposals.

    Uses Claude API to analyze the root cause and generate specific,
    actionable remediation steps with risk assessment and approval
    requirements.
    """

    def __init__(self):
        self.model = settings.model_name or "claude-sonnet-4-6"
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

    async def propose_remediation(
        self,
        rca: dict,
        incident: dict,
    ) -> RemediationPlan:
        """Generate a remediation plan based on root cause analysis.

        Args:
            rca: Root cause analysis dictionary containing:
                - category: Type of root cause
                - description: Detailed explanation
                - evidence: Supporting evidence list
            incident: Incident context dictionary containing:
                - incident_id: Unique identifier
                - severity: critical/high/medium/low
                - affected_services: List of impacted services

        Returns:
            RemediationPlan with ordered steps, risk assessment,
            and recovery estimates.
        """
        incident_id = incident.get("incident_id", "unknown")

        if not self.api_available:
            logger.warning(
                "ANTHROPIC_API_KEY not set; generating template-based "
                "remediation for %s",
                incident_id,
            )
            return self._template_based_remediation(rca, incident)

        logger.info(
            "Generating Claude-powered remediation for %s (category=%s)",
            incident_id,
            rca.get("category", "unknown"),
        )

        try:
            return await self._claude_remediation(rca, incident)
        except anthropic.APIError as exc:
            logger.error(
                "Claude API error generating remediation for %s: %s",
                incident_id,
                exc,
            )
            return self._template_based_remediation(rca, incident)
        except Exception as exc:
            logger.exception(
                "Unexpected error generating remediation for %s",
                incident_id,
            )
            return self._template_based_remediation(rca, incident)

    async def _claude_remediation(
        self,
        rca: dict,
        incident: dict,
    ) -> RemediationPlan:
        """Generate remediation using Claude API.

        Sends the RCA and incident context to Claude with a specialized
        system prompt, then parses the structured response into a
        RemediationPlan.

        Args:
            rca: Root cause analysis dictionary.
            incident: Incident context dictionary.

        Returns:
            RemediationPlan generated by Claude.
        """
        incident_id = incident.get("incident_id", "unknown")

        user_content = (
            f"Root Cause Analysis:\n{json.dumps(rca, indent=2)}\n\n"
            f"Incident Context:\n{json.dumps(incident, indent=2)}"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=REMEDIATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        # Parse Claude's response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        parsed = self._parse_remediation_json(text)

        # Build RemediationPlan from parsed response
        steps: list[RemediationStep] = []
        for step_data in parsed.get("remediation_steps", []):
            steps.append(RemediationStep(
                description=step_data.get("description", ""),
                command=step_data.get("command", ""),
                risk_level=step_data.get("risk_level", "medium"),
                requires_approval=step_data.get("requires_approval", True),
                estimated_impact=step_data.get("estimated_impact", ""),
                category=step_data.get("category", "root_cause_fix"),
                rollback_command=step_data.get("rollback_command", ""),
            ))

        return RemediationPlan(
            incident_id=incident_id,
            steps=steps,
            estimated_recovery_time=parsed.get("estimated_recovery_time", ""),
            rollback_plan=parsed.get("rollback_plan", ""),
            post_incident_actions=parsed.get("post_incident_actions", []),
        )

    def _parse_remediation_json(self, text: str) -> dict:
        """Parse JSON remediation response from Claude.

        Handles cases where JSON is embedded in markdown code blocks.

        Args:
            text: Raw text from Claude's response.

        Returns:
            Parsed dictionary with remediation data.
        """
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try markdown code block extraction
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

        # Try to find JSON object
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return {"remediation_steps": [], "raw_text": text[:2000]}

    def _template_based_remediation(
        self,
        rca: dict,
        incident: dict,
    ) -> RemediationPlan:
        """Generate remediation from templates when API is unavailable.

        Maps root cause categories to predefined remediation templates
        and fills in the placeholders with incident-specific data.

        Args:
            rca: Root cause analysis dictionary.
            incident: Incident context dictionary.

        Returns:
            Template-based RemediationPlan.
        """
        incident_id = incident.get("incident_id", "unknown")
        severity = incident.get("severity", "medium")
        affected_services = incident.get("affected_services", [])
        category = rca.get("category", "unknown")
        primary_service = affected_services[0] if affected_services else "app"
        namespace = "production"

        steps: list[RemediationStep] = []

        # Map root cause categories to remediation templates
        if category in ("dependency_failure", "cascading_failure"):
            steps.extend([
                RemediationStep(
                    description=f"Enable circuit breaker for {primary_service} upstream calls",
                    command=f"kubectl set env deployment/{primary_service} "
                    f"CIRCUIT_BREAKER_ENABLED=true CIRCUIT_BREAKER_THRESHOLD=5 "
                    f"-n {namespace}",
                    risk_level="low",
                    requires_approval=False,
                    estimated_impact="Prevent cascading failures to downstream services",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl set env deployment/{primary_service} "
                    f"CIRCUIT_BREAKER_ENABLED=false -n {namespace}",
                ),
                RemediationStep(
                    description=f"Scale {primary_service} to handle backlog after circuit breaker recovery",
                    command=f"kubectl scale deployment/{primary_service} --replicas=5 -n {namespace}",
                    risk_level="low",
                    requires_approval=False,
                    estimated_impact="Handle request backlog during recovery",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl scale deployment/{primary_service} --replicas=3 -n {namespace}",
                ),
            ])

        elif category in ("resource_exhaustion", "connection_pool_exhaustion"):
            steps.extend([
                RemediationStep(
                    description=f"Increase database connection pool size for {primary_service}",
                    command=f"kubectl set env deployment/{primary_service} "
                    f"DB_POOL_SIZE=100 -n {namespace}",
                    risk_level="low",
                    requires_approval=False,
                    estimated_impact="Restore database connection availability",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl set env deployment/{primary_service} "
                    f"DB_POOL_SIZE=50 -n {namespace}",
                ),
                RemediationStep(
                    description=f"Scale {primary_service} horizontally to distribute connection load",
                    command=f"kubectl scale deployment/{primary_service} --replicas=5 -n {namespace}",
                    risk_level="low",
                    requires_approval=False,
                    estimated_impact="Distribute connection load across more instances",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl scale deployment/{primary_service} --replicas=3 -n {namespace}",
                ),
                RemediationStep(
                    description="Scale RDS instance to support higher connection count",
                    command="terraform apply -target=aws_db_instance.main -var='instance_class=db.r6g.xlarge'",
                    risk_level="high",
                    requires_approval=True,
                    estimated_impact="Increase maximum supported connections at database level",
                    category="root_cause_fix",
                    rollback_command="terraform apply -target=aws_db_instance.main -var='instance_class=db.r6g.large'",
                ),
            ])

        elif category in ("deployment_failure", "bad_deployment"):
            steps.extend([
                RemediationStep(
                    description=f"Rollback {primary_service} to previous known-good revision",
                    command=f"kubectl rollout undo deployment/{primary_service} -n {namespace}",
                    risk_level="medium",
                    requires_approval=True,
                    estimated_impact="Restore service to last working version",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl rollout undo deployment/{primary_service} -n {namespace}",
                ),
            ])

        elif category in ("memory_leak", "oom"):
            steps.extend([
                RemediationStep(
                    description=f"Rolling restart {primary_service} to clear leaked memory",
                    command=f"kubectl rollout restart deployment/{primary_service} -n {namespace}",
                    risk_level="medium",
                    requires_approval=True,
                    estimated_impact="Temporarily resolve OOM by restarting pods with fresh memory",
                    category="immediate_mitigation",
                    rollback_command="",
                ),
                RemediationStep(
                    description=f"Increase memory limit for {primary_service}",
                    command=f"kubectl set resources deployment/{primary_service} "
                    f"--limits=memory=2Gi -n {namespace}",
                    risk_level="medium",
                    requires_approval=True,
                    estimated_impact="Prevent immediate OOM recurrence while leak is investigated",
                    category="root_cause_fix",
                    rollback_command=f"kubectl set resources deployment/{primary_service} "
                    f"--limits=memory=1Gi -n {namespace}",
                ),
            ])

        else:
            # Generic remediation steps
            steps.extend([
                RemediationStep(
                    description=f"Rolling restart {primary_service} to recover from bad state",
                    command=f"kubectl rollout restart deployment/{primary_service} -n {namespace}",
                    risk_level="medium",
                    requires_approval=True,
                    estimated_impact="Restore service to clean state",
                    category="immediate_mitigation",
                    rollback_command="",
                ),
                RemediationStep(
                    description=f"Scale {primary_service} horizontally",
                    command=f"kubectl scale deployment/{primary_service} --replicas=5 -n {namespace}",
                    risk_level="low",
                    requires_approval=False,
                    estimated_impact="Increase capacity to handle load",
                    category="immediate_mitigation",
                    rollback_command=f"kubectl scale deployment/{primary_service} --replicas=3 -n {namespace}",
                ),
            ])

        # Add prevention steps for all categories
        steps.append(RemediationStep(
            description="Create Jira ticket for post-incident follow-up and prevention measures",
            command="",
            risk_level="low",
            requires_approval=False,
            estimated_impact="Track long-term prevention work",
            category="prevention",
            rollback_command="",
        ))

        return RemediationPlan(
            incident_id=incident_id,
            steps=steps,
            estimated_recovery_time="15-30 minutes" if severity in ("critical", "high") else "30-60 minutes",
            rollback_plan=(
                f"Rollback {primary_service} deployment and restore previous "
                f"environment configuration if remediation steps cause regression."
            ),
            post_incident_actions=[
                "Conduct blameless post-incident review within 48 hours",
                "Update runbooks with findings from this incident",
                "Review and improve monitoring/alerting thresholds",
                f"Add integration tests for {category} failure scenario",
            ],
        )
