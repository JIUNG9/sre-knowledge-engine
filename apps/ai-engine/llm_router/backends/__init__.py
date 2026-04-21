"""Backend implementations for the LLM router.

Two backends are shipped:

* :mod:`llm_router.backends.claude`   — thin wrapper around Anthropic API.
* :mod:`llm_router.backends.ollama`   — thin wrapper around the Ollama
  HTTP API at ``http://localhost:11434``.

Both expose the same ``complete`` / ``stream`` interface and return the
same :class:`llm_router.router.RouterResponse` dataclass so callers
don't need to know which backend served the request.
"""

from __future__ import annotations

from .claude import ClaudeBackend
from .ollama import OllamaBackend, OllamaUnavailable

__all__ = ["ClaudeBackend", "OllamaBackend", "OllamaUnavailable"]
