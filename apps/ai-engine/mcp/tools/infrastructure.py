"""Infrastructure MCP tool schemas.

These tools allow Claude to interact with Kubernetes, AWS, and Terraform
during incident investigation. Destructive operations (kubectl_action,
terraform_apply) require human approval before execution.
"""

INFRASTRUCTURE_TOOLS: list[dict] = [
    {
        "name": "kubectl_read",
        "description": (
            "Read Kubernetes resource state using kubectl. Supports getting pods, "
            "deployments, services, events, logs, and other resources. Read-only "
            "operations that do not modify cluster state."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "kubectl read command to execute (e.g., 'get pods -n production', "
                        "'describe deployment/api-gateway', 'top pods -n production')"
                    ),
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace to target",
                    "default": "default",
                },
                "context": {
                    "type": "string",
                    "description": "Kubernetes context (cluster) to use",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "yaml", "wide", "name"],
                    "description": "Output format for kubectl",
                    "default": "json",
                },
            },
            "required": ["command"],
        },
        "requires_approval": False,
    },
    {
        "name": "kubectl_action",
        "description": (
            "Execute a mutating kubectl command (scale, restart, apply, delete). "
            "REQUIRES HUMAN APPROVAL before execution. Used for remediation actions "
            "during incident response."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "kubectl mutating command (e.g., 'scale deployment/api-gateway --replicas=5', "
                        "'rollout restart deployment/payment-service')"
                    ),
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace to target",
                },
                "context": {
                    "type": "string",
                    "description": "Kubernetes context (cluster) to use",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, perform a dry-run without applying changes",
                    "default": True,
                },
                "reason": {
                    "type": "string",
                    "description": "Explanation of why this action is needed (for audit trail)",
                },
            },
            "required": ["command", "namespace", "reason"],
        },
        "requires_approval": True,
    },
    {
        "name": "terraform_plan",
        "description": (
            "Run terraform plan to preview infrastructure changes. Read-only operation "
            "that shows what would change without applying. Useful for validating "
            "proposed remediation steps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": "Terraform workspace/directory to plan",
                },
                "target": {
                    "type": "string",
                    "description": "Specific resource to target (e.g., 'aws_rds_cluster.main')",
                },
                "var_overrides": {
                    "type": "object",
                    "description": "Variable overrides for the plan",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["workspace"],
        },
        "requires_approval": False,
    },
    {
        "name": "terraform_apply",
        "description": (
            "Apply Terraform changes to infrastructure. REQUIRES HUMAN APPROVAL. "
            "Only used for pre-approved remediation actions during incident response."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": "Terraform workspace/directory to apply",
                },
                "target": {
                    "type": "string",
                    "description": "Specific resource to target",
                },
                "plan_file": {
                    "type": "string",
                    "description": "Path to a previously generated plan file",
                },
                "reason": {
                    "type": "string",
                    "description": "Explanation of why this apply is needed (for audit trail)",
                },
            },
            "required": ["workspace", "reason"],
        },
        "requires_approval": True,
    },
    {
        "name": "aws_describe",
        "description": (
            "Describe AWS resources using the AWS CLI. Read-only operations to inspect "
            "resource state, configuration, and health. Supports EC2, RDS, ECS, EKS, "
            "Lambda, S3, CloudWatch, and other AWS services."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "AWS service name (e.g., 'ec2', 'rds', 'ecs', 'eks', 'lambda')",
                },
                "command": {
                    "type": "string",
                    "description": (
                        "AWS CLI describe command (e.g., 'describe-instances', "
                        "'describe-db-clusters', 'describe-services')"
                    ),
                },
                "region": {
                    "type": "string",
                    "description": "AWS region to query",
                    "default": "ap-northeast-2",
                },
                "filters": {
                    "type": "object",
                    "description": "AWS CLI filter parameters",
                    "additionalProperties": {"type": "string"},
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "table", "text"],
                    "description": "Output format",
                    "default": "json",
                },
            },
            "required": ["service", "command"],
        },
        "requires_approval": False,
    },
]
