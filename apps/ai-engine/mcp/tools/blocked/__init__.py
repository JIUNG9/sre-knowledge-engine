"""Blocked-scope MCP tools.

Tools in this package are defined for auditability and code-review
visibility, but the ``ToolManifest`` guarantees they are NEVER surfaced
to the agent. Importing this package is safe — registration alone does
not make a tool callable.

See ``mcp/SCOPING.md`` for the full rationale.
"""

from mcp.tools.blocked import kubectl_delete, terraform_apply  # noqa: F401

__all__ = ["kubectl_delete", "terraform_apply"]
