# MCP Tool Scoping

Aegis enforces a three-scope model on every tool it exposes to the AI agent.

## The three scopes

| Scope | Default | What it means |
|-------|---------|---------------|
| `read` | Loaded | Safe, read-only tools (log search, metric query, runbook lookup). |
| `write` | Opt-in | Side-effectful tools (Slack post, Jira ticket). Require `load_write=True` AND a human-approval gate downstream. |
| `blocked` | Never loaded | Destructive, irreversible, or infra-mutating tools. Defined in the codebase for auditability but never surfaced to the agent. |

## Why BLOCKED is compile-time absent

The 2025 Replit incident is the canonical lesson: an agent that *can* call a destructive tool will eventually be tricked into calling it. Prompt-injection attacks, hallucinated tool_use blocks, and adversarial log entries are all effective attack vectors when the tool schema is loaded into the model's context.

Runtime checks ("we'll refuse if the agent tries to call `terraform_apply`") are not sufficient. They depend on every caller remembering to check, on bug-free conditional logic, and on the tool schema itself not being leaked into prompts where it can be re-echoed back as a `tool_use`.

Aegis closes that class of bug by making BLOCKED tools *structurally unreachable*. The `ToolManifest.load_scope` method never returns them, the MCP `list_tools` response never contains them, and `get_tool(name)` always returns `None` for blocked names. The model literally cannot see that the tool exists.

## Belt and suspenders

Blocking is enforced on two independent axes:

1. `@scoped_tool("blocked")` — decorator-level scope tag.
2. `MCPScopeConfig.blocked_tool_names` — explicit deny-list by name.

Either one alone is sufficient. Together, adding a new destructive tool without remembering to block it is structurally very hard: forgetting both guards would require actively tagging the tool `read` or `write` AND omitting its name from the deny-list.

## Adding a new tool

- Read-only? Put it in `mcp/tools/read/` with `@scoped_tool("read")`.
- Writes to an external system? `mcp/tools/write/` with `@scoped_tool("write")`. Require human approval in the router.
- Mutates infrastructure? `mcp/tools/blocked/` with `@scoped_tool("blocked")` AND add its name to `DEFAULT_BLOCKED_TOOL_NAMES` in `scope_config.py`.
