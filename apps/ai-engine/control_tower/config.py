"""Configuration for the Aegis Claude Control Tower (Layer 3).

The control tower exposes a single knob set at construction time that
governs how expensive an investigation can get. Values are expressed in
tokens (for context budgets) and counts (for LLM call ceilings). All
three modes — ``eco``, ``standard``, ``deep`` — carry independent
budgets so a single deployment can tune them without coupling.

The defaults are chosen to be safe for a small homelab / demo:

* ``eco`` ~ 4k context + 1 call → cheap triage, hundreds of alerts/day
* ``standard`` ~ 16k context + 2 calls → per-page investigation
* ``deep`` ~ 64k context + 3 calls → post-mortem quality

Deployments that want different ceilings pass a custom
:class:`ControlTowerConfig` to :class:`control_tower.ControlTower`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


InvestigationModeName = Literal["eco", "standard", "deep"]


class ControlTowerConfig(BaseModel):
    """Runtime configuration for the control tower.

    Attributes:
        default_mode: Mode used when callers do not specify one.
        eco_context_tokens: Context budget (in input tokens) for eco.
        standard_context_tokens: Context budget for standard mode.
        deep_context_tokens: Context budget for deep mode.
        max_llm_calls_per_mode: Hard ceiling per mode. The orchestrator
            refuses to issue more calls than this even if the prompt
            asks for it.
        enable_pattern_analyzer_in_deep: When ``True`` (default), deep
            mode feeds alert events through the Layer 2B pattern
            analyzer and injects the markdown summary into context.
        budget_usd_per_investigation: Soft cap for a single
            investigation. The tower does not abort mid-flight but
            records a warning on the Investigation when the cap is
            exceeded.
        include_traces_in_standard: When ``True``, standard mode
            augments the context with a handful of recent traces for
            the target service. Off by default to keep standard cheap.
    """

    default_mode: InvestigationModeName = "standard"

    eco_context_tokens: int = Field(default=4_000, ge=512)
    standard_context_tokens: int = Field(default=16_000, ge=1024)
    deep_context_tokens: int = Field(default=64_000, ge=2048)

    max_llm_calls_per_mode: dict[InvestigationModeName, int] = Field(
        default_factory=lambda: {"eco": 1, "standard": 2, "deep": 3}
    )

    enable_pattern_analyzer_in_deep: bool = True
    include_traces_in_standard: bool = False

    budget_usd_per_investigation: float = 1.00

    model_config = {"arbitrary_types_allowed": True}

    def context_budget_for(self, mode: InvestigationModeName) -> int:
        """Return the context-token budget for a given mode."""
        if mode == "eco":
            return self.eco_context_tokens
        if mode == "standard":
            return self.standard_context_tokens
        return self.deep_context_tokens

    def call_ceiling_for(self, mode: InvestigationModeName) -> int:
        """Return the max number of LLM calls permitted for a mode."""
        return int(self.max_llm_calls_per_mode.get(mode, 1))
