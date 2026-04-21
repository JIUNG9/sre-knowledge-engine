"""MCP tool scope configuration.

Defines which tool scopes are loaded into the MCP server. This is the
compile-time gate that enforces the Replit-lesson rule: BLOCKED tools
never participate in MCP serving, regardless of runtime flags.

Scopes
------
- read:    Safe, read-only tools. Loaded by default.
- write:   Side-effect tools (Slack, Jira, PRs). Opt-in via ``load_write``.
- blocked: Never loaded. Never surfaced in the MCP manifest. Absolute.

BLOCKED semantics
-----------------
``blocked_tool_names`` is authoritative. Any registered tool whose name
appears in this list is excluded from every ``load_scope`` result, even
``load_scope("write")``. The default list reflects the highest-risk
mutating tools the Aegis agent must never be able to invoke.
"""

from dataclasses import dataclass, field


DEFAULT_BLOCKED_TOOL_NAMES: list[str] = [
    "terraform_apply",
    "kubectl_delete",
    "aws_iam_delete",
    "kubectl_apply_destructive",
    "helm_install",
]


@dataclass(frozen=True)
class MCPScopeConfig:
    """Configuration for the MCP tool manifest.

    Attributes:
        load_read: Whether to surface tools registered with scope="read".
        load_write: Whether to surface tools registered with scope="write".
            Write tools are side-effectful (Slack post, Jira create, etc.)
            and are opt-in. Even when True, blocked tools are still
            excluded by name.
        blocked_tool_names: List of tool names that must NEVER appear in
            the MCP manifest, regardless of scope annotation. This is
            the belt-and-suspenders defence on top of the
            ``@scoped_tool("blocked")`` decorator.
    """

    load_read: bool = True
    load_write: bool = False
    blocked_tool_names: list[str] = field(
        default_factory=lambda: list(DEFAULT_BLOCKED_TOOL_NAMES)
    )


__all__ = ["MCPScopeConfig", "DEFAULT_BLOCKED_TOOL_NAMES"]
