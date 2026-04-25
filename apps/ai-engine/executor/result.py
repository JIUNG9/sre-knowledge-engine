"""Public result type for one executor invocation.

``ExecutionResult`` is what the orchestrator hands back to Layer 3 (the
Control Tower) — Investigation.execution_result will carry it. Three
outcomes are possible:

* ``executed``  — the wrapped command ran (or would have run, in dry-run).
* ``refused``   — a gate (tier / approvals / kill-switch / disabled config /
                  forbidden verb) said no. ``refused_reason`` explains.
* ``failed``    — the wrapper attempted execution and the underlying
                  process raised / non-zero-exited. ``stderr`` carries the
                  wrapper's captured error stream when available.

The result is JSON-serialisable Pydantic v2 so the FastAPI router can
return it directly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Outcome = Literal["executed", "refused", "failed"]


class ExecutionResult(BaseModel):
    """One row of executor output. Always present, never optional."""

    model_config = ConfigDict(extra="ignore")

    outcome: Outcome
    verb: str = ""
    target: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    refused_reason: str | None = None
    audit_id: str | None = None
    dry_run: bool = False
    investigation_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def refused(
        cls,
        *,
        reason: str,
        verb: str = "",
        target: str = "",
        investigation_id: str | None = None,
        audit_id: str | None = None,
    ) -> "ExecutionResult":
        """Convenience constructor for refusals — no command was run."""
        return cls(
            outcome="refused",
            verb=verb,
            target=target,
            refused_reason=reason,
            investigation_id=investigation_id,
            audit_id=audit_id,
        )

    @property
    def succeeded(self) -> bool:
        """True only when the underlying command ran cleanly."""
        return (
            self.outcome == "executed"
            and (self.exit_code is None or self.exit_code == 0)
        )
