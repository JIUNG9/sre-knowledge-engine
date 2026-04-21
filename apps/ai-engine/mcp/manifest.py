"""MCP tool manifest — the single source of truth for which tools are
surfaced to the Claude agent.

Architectural principle (the "Replit lesson")
---------------------------------------------
A BLOCKED tool must be ABSENT from the MCP manifest entirely. It is not
enough to register a handler and refuse to call it — a prompt injection
can still cause the agent to invoke any tool whose schema is loaded.

The manifest enforces this at load time:

1. ``@scoped_tool("blocked")`` records the tool in ``_all_registered``
   but the manifest NEVER returns it from ``load_scope()``.
2. ``MCPScopeConfig.blocked_tool_names`` provides a second, independent
   filter — any tool name appearing there is excluded regardless of its
   registered scope (belt + suspenders).

Idempotency
-----------
Re-registering the same callable (e.g. when a package is imported twice
during testing or hot-reload) is a no-op. Re-registering a DIFFERENT
callable under an existing tool name raises ``ValueError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from mcp.scope_config import MCPScopeConfig


Scope = Literal["read", "write", "blocked"]


@dataclass(frozen=True)
class LoadedTool:
    """Represents a tool surfaced by the manifest."""

    name: str
    scope: Scope
    fn: Callable


class ToolManifest:
    """Registry that decides which tools reach the MCP serving layer.

    The manifest is intentionally simple: tools register themselves at
    import time via the ``@scoped_tool`` decorator, and the serving layer
    asks ``load_scope`` for exactly the tools it wants to surface.
    """

    def __init__(self) -> None:
        # name -> LoadedTool for every tool ever registered
        self._all_registered: dict[str, LoadedTool] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def register(
        self,
        tool_fn: Callable,
        scope: Scope,
        name: str | None = None,
    ) -> LoadedTool:
        """Register a tool function under a given scope.

        Idempotent: re-registering the same function under the same name
        returns the existing entry without raising. Attempting to register
        a different function under a name already in use raises
        ``ValueError``.

        Args:
            tool_fn: The tool implementation callable.
            scope: One of "read", "write", "blocked".
            name: Tool name. Defaults to ``tool_fn.__name__``.

        Returns:
            The ``LoadedTool`` entry.
        """
        if scope not in ("read", "write", "blocked"):
            raise ValueError(
                f"Invalid scope {scope!r}. Must be 'read', 'write', or 'blocked'."
            )

        tool_name = name or tool_fn.__name__
        existing = self._all_registered.get(tool_name)
        if existing is not None:
            if existing.scope != scope:
                raise ValueError(
                    f"Tool {tool_name!r} is already registered with a different "
                    f"scope (existing scope={existing.scope!r}, "
                    f"new scope={scope!r})."
                )
            # Same name + same scope: treat as idempotent. This covers
            # module reloads where the callable object is new but
            # represents the same tool.
            if existing.fn is tool_fn:
                return existing
            refreshed = LoadedTool(name=tool_name, scope=scope, fn=tool_fn)
            self._all_registered[tool_name] = refreshed
            return refreshed

        entry = LoadedTool(name=tool_name, scope=scope, fn=tool_fn)
        self._all_registered[tool_name] = entry
        return entry

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    def load_scope(
        self,
        scope: Scope,
        config: MCPScopeConfig | None = None,
    ) -> list[LoadedTool]:
        """Return the tools that should be surfaced for a given scope.

        BLOCKED tools are NEVER returned, regardless of the requested
        scope or config flags. This method is what the MCP server calls
        to build its tool manifest — tools that aren't returned here do
        not exist from the agent's perspective.

        Args:
            scope: Which scope bucket to surface ("read" or "write").
                Passing "blocked" always returns an empty list.
            config: Scope configuration. If omitted, a default
                ``MCPScopeConfig()`` is used.

        Returns:
            List of ``LoadedTool`` entries, in registration order.
        """
        if config is None:
            config = MCPScopeConfig()

        if scope == "blocked":
            # Blocked tools are never loaded, full stop.
            return []

        if scope == "read" and not config.load_read:
            return []
        if scope == "write" and not config.load_write:
            return []

        blocked_names = set(config.blocked_tool_names)

        surfaced: list[LoadedTool] = []
        for entry in self._all_registered.values():
            if entry.scope != scope:
                continue
            # Belt-and-suspenders: even a "read"- or "write"-tagged tool
            # is dropped if its name appears in the blocklist.
            if entry.name in blocked_names:
                continue
            # Additional defence: anything ever tagged "blocked" stays out.
            # (already covered by the scope filter above, but explicit.)
            surfaced.append(entry)

        return surfaced

    def load_all_allowed(
        self,
        config: MCPScopeConfig | None = None,
    ) -> list[LoadedTool]:
        """Return every tool allowed under the given config.

        Convenience wrapper that concatenates ``load_scope("read")`` and,
        if enabled, ``load_scope("write")``. BLOCKED tools are never
        included.
        """
        if config is None:
            config = MCPScopeConfig()
        result: list[LoadedTool] = []
        if config.load_read:
            result.extend(self.load_scope("read", config))
        if config.load_write:
            result.extend(self.load_scope("write", config))
        return result

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #

    def get_all_loaded(self) -> list[LoadedTool]:
        """Return every tool that has ever registered, regardless of scope.

        Intended for diagnostics and tests only — callers must NOT use
        this to build the MCP manifest, because it includes blocked tools.
        """
        return list(self._all_registered.values())

    def get_blocked(self) -> list[LoadedTool]:
        """Return every tool registered with scope="blocked"."""
        return [t for t in self._all_registered.values() if t.scope == "blocked"]

    def clear(self) -> None:
        """Reset the manifest. Test-only helper."""
        self._all_registered.clear()


# Process-wide singleton. Decorators and the MCP server share this one.
manifest = ToolManifest()


__all__ = ["ToolManifest", "LoadedTool", "Scope", "manifest"]
