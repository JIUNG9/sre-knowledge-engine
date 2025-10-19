"""Workflow MCP tool schemas.

These tools allow Claude to interact with collaboration and workflow
systems during incident response — notifying teams, creating tickets,
opening pull requests, searching runbooks, and escalating via PagerDuty.
"""

WORKFLOW_TOOLS: list[dict] = [
    {
        "name": "slack_notify",
        "description": (
            "Send a notification to a Slack channel or thread. Used to communicate "
            "investigation findings, status updates, and remediation proposals to "
            "the incident response team."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel name or ID (e.g., '#incidents', '#sre-team')",
                },
                "message": {
                    "type": "string",
                    "description": "Message content (supports Slack markdown formatting)",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Thread timestamp to reply in an existing thread",
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "Message severity (affects formatting/emoji)",
                    "default": "info",
                },
                "blocks": {
                    "type": "array",
                    "description": "Slack Block Kit blocks for rich formatting",
                    "items": {"type": "object"},
                },
            },
            "required": ["channel", "message"],
        },
    },
    {
        "name": "jira_create",
        "description": (
            "Create a Jira ticket for tracking remediation work, follow-up tasks, "
            "or post-incident action items. Automatically links to the incident "
            "and populates relevant context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Jira project key (e.g., 'SRE', 'PLATFORM')",
                },
                "summary": {
                    "type": "string",
                    "description": "Ticket title/summary",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed ticket description (supports Jira markdown)",
                },
                "issue_type": {
                    "type": "string",
                    "enum": ["Bug", "Task", "Story", "Incident", "Sub-task"],
                    "description": "Jira issue type",
                    "default": "Task",
                },
                "priority": {
                    "type": "string",
                    "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                    "description": "Ticket priority",
                    "default": "High",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to apply to the ticket",
                },
                "assignee": {
                    "type": "string",
                    "description": "Jira username to assign the ticket to",
                },
                "incident_id": {
                    "type": "string",
                    "description": "Related incident ID for cross-referencing",
                },
            },
            "required": ["project", "summary", "description"],
        },
    },
    {
        "name": "github_pr",
        "description": (
            "Create a GitHub Pull Request for infrastructure or configuration changes "
            "identified during incident investigation. Supports creating PRs for "
            "Terraform changes, Kubernetes manifests, and application config updates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "GitHub repository (e.g., 'org/repo-name')",
                },
                "title": {
                    "type": "string",
                    "description": "Pull request title",
                },
                "body": {
                    "type": "string",
                    "description": "Pull request description (supports GitHub markdown)",
                },
                "base_branch": {
                    "type": "string",
                    "description": "Base branch to merge into",
                    "default": "main",
                },
                "head_branch": {
                    "type": "string",
                    "description": "Branch containing the changes",
                },
                "files": {
                    "type": "array",
                    "description": "Files to create/modify in the PR",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to apply to the PR",
                },
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "GitHub usernames to request review from",
                },
            },
            "required": ["repository", "title", "body"],
        },
    },
    {
        "name": "runbook_search",
        "description": (
            "Search the runbook knowledge base for relevant procedures and playbooks. "
            "Returns matching runbooks with step-by-step instructions for handling "
            "specific incident types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query describing the incident or procedure needed",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to filter runbooks by (e.g., 'database', 'networking', 'scaling')",
                },
                "service": {
                    "type": "string",
                    "description": "Service name to scope the search",
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Incident severity to match runbook urgency",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of runbooks to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "pagerduty_escalate",
        "description": (
            "Escalate an incident via PagerDuty. Triggers an escalation to the next "
            "level in the escalation policy or pages a specific on-call team. Used "
            "when the AI investigation determines human intervention is needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "PagerDuty incident ID to escalate (or Aegis incident ID to create new)",
                },
                "escalation_policy": {
                    "type": "string",
                    "description": "PagerDuty escalation policy ID or name",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["high", "low"],
                    "description": "Escalation urgency level",
                    "default": "high",
                },
                "message": {
                    "type": "string",
                    "description": "Escalation context message for the on-call engineer",
                },
                "details": {
                    "type": "object",
                    "description": "Additional context details (investigation summary, affected services, etc.)",
                },
            },
            "required": ["escalation_policy", "message"],
        },
    },
]
