"""Investigation modes for the Claude Control Tower.

Each mode is a declarative bundle of:

* the preferred Claude model
* the temperature + max_tokens to pass to the LLM
* the list of telemetry fetchers to call when building context
* whether the pattern analyzer runs
* the number of reasoning passes the orchestrator is allowed

Modes are *data*, not code. The orchestrator looks up the
:class:`ModeSpec` for the requested mode and executes the same pipeline
for all three — only the spec values change. This keeps the decision
tree small and testable.

Mode semantics:

* ``eco`` — Haiku-class model, tiny context, single LLM call. Best for
  first-pass triage of high-volume alerts. Skips pattern analysis and
  traces entirely.
* ``standard`` — Sonnet-class model, mid-sized context, up to two calls
  (hypothesize then summarize). Pulls L1 wiki + recent logs + metrics.
* ``deep`` — Opus-class model, large context, up to three calls
  (hypothesize, verify, summarize). Runs the pattern analyzer, pulls
  traces, and includes correlation findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import InvestigationModeName


@dataclass(frozen=True)
class ModeSpec:
    """Declarative bundle describing how one mode should run.

    Attributes:
        name: Mode identifier (``eco`` | ``standard`` | ``deep``).
        description: Human-readable blurb surfaced by the ``/modes`` API.
        preferred_model: Claude model hint. The LLM router ultimately
            decides which backend serves the call — this is a request,
            not a guarantee.
        max_tokens: Max tokens in the reply. Scales with the mode.
        temperature: Sampling temperature. Eco uses lower temp for
            consistency; deep uses slightly higher for exploration.
        include_wiki: When True, ContextBuilder calls WikiEngine.
        include_logs: When True, ContextBuilder calls LogFetcher.
        include_metrics: When True, ContextBuilder calls MetricFetcher.
        include_traces: When True, ContextBuilder calls TraceFetcher.
        include_alert_history: When True, ContextBuilder calls
            AlertFetcher.
        run_pattern_analyzer: When True, ContextBuilder invokes the
            Layer 2B PatternAnalyzer on collected events.
        max_llm_calls: Hard ceiling on reasoning passes for the mode.
    """

    name: InvestigationModeName
    description: str
    preferred_model: str
    max_tokens: int
    temperature: float
    include_wiki: bool
    include_logs: bool
    include_metrics: bool
    include_traces: bool
    include_alert_history: bool
    run_pattern_analyzer: bool
    max_llm_calls: int
    tools: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Serialisable view (used by the ``GET /api/v1/modes`` endpoint)."""
        return {
            "name": self.name,
            "description": self.description,
            "preferred_model": self.preferred_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "include_wiki": self.include_wiki,
            "include_logs": self.include_logs,
            "include_metrics": self.include_metrics,
            "include_traces": self.include_traces,
            "include_alert_history": self.include_alert_history,
            "run_pattern_analyzer": self.run_pattern_analyzer,
            "max_llm_calls": self.max_llm_calls,
            "tools": list(self.tools),
        }


# --------------------------------------------------------------------------- #
# Canonical specs
# --------------------------------------------------------------------------- #


ECO = ModeSpec(
    name="eco",
    description=(
        "Fast triage. Single LLM call, tight context. Best for first-pass "
        "sorting of high-volume alerts."
    ),
    preferred_model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    temperature=0.1,
    include_wiki=True,
    include_logs=False,
    include_metrics=False,
    include_traces=False,
    include_alert_history=False,
    run_pattern_analyzer=False,
    max_llm_calls=1,
    tools=("wiki.query",),
)


STANDARD = ModeSpec(
    name="standard",
    description=(
        "Balanced investigation. Pulls L1 wiki + recent logs + key metrics. "
        "Up to two LLM calls (hypothesize then summarize)."
    ),
    preferred_model="claude-sonnet-4-6",
    max_tokens=2048,
    temperature=0.2,
    include_wiki=True,
    include_logs=True,
    include_metrics=True,
    include_traces=False,
    include_alert_history=True,
    run_pattern_analyzer=False,
    max_llm_calls=2,
    tools=("wiki.query", "logs.search", "metrics.query", "alerts.history"),
)


DEEP = ModeSpec(
    name="deep",
    description=(
        "Post-mortem quality. Large context, pattern analyzer, traces, and "
        "correlation. Up to three LLM calls."
    ),
    preferred_model="claude-opus-4-7",
    max_tokens=4096,
    temperature=0.3,
    include_wiki=True,
    include_logs=True,
    include_metrics=True,
    include_traces=True,
    include_alert_history=True,
    run_pattern_analyzer=True,
    max_llm_calls=3,
    tools=(
        "wiki.query",
        "logs.search",
        "metrics.query",
        "traces.search",
        "alerts.history",
        "pattern_analyzer.analyze",
    ),
)


_MODES: dict[InvestigationModeName, ModeSpec] = {
    "eco": ECO,
    "standard": STANDARD,
    "deep": DEEP,
}


def get_mode_spec(name: InvestigationModeName | str) -> ModeSpec:
    """Return the :class:`ModeSpec` for ``name``.

    Raises:
        ValueError: When ``name`` is not a recognized mode.
    """
    key = str(name).lower().strip()
    if key not in _MODES:
        raise ValueError(
            f"unknown investigation mode '{name}'. "
            f"Valid modes: {', '.join(_MODES)}"
        )
    return _MODES[key]  # type: ignore[index]


def all_modes() -> list[ModeSpec]:
    """Return every registered mode spec, stable order."""
    return [_MODES["eco"], _MODES["standard"], _MODES["deep"]]
