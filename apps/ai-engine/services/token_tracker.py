"""Token usage tracking for Claude API calls.

Tracks per-investigation token usage (input, output, cached), calculates
cost based on model pricing, and stores usage history for auditing and
cost management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# Claude model pricing (per million tokens, USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cached_input": 0.30,
    },
    "claude-opus-4-6": {
        "input": 15.00,
        "output": 75.00,
        "cached_input": 1.50,
    },
    "claude-haiku-3-5": {
        "input": 0.80,
        "output": 4.00,
        "cached_input": 0.08,
    },
}


@dataclass
class TokenUsage:
    """Token usage for a single API call or investigation."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class InvestigationUsageRecord:
    """Complete usage record for an investigation."""

    investigation_id: str
    model: str
    api_calls: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "model": self.model,
            "api_calls": self.api_calls,
            "token_usage": self.usage.to_dict(),
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TokenTracker:
    """Tracks token usage across investigations.

    Maintains a rolling history of token usage per investigation and
    provides cost estimation based on current model pricing.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: list[InvestigationUsageRecord] = []
        self._active: dict[str, InvestigationUsageRecord] = {}

    def start_tracking(self, investigation_id: str, model: str) -> None:
        """Begin tracking tokens for an investigation.

        Args:
            investigation_id: Unique identifier for the investigation.
            model: Claude model name being used.
        """
        record = InvestigationUsageRecord(
            investigation_id=investigation_id,
            model=model,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._active[investigation_id] = record

    def record_api_call(
        self,
        investigation_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> None:
        """Record token usage from a single API call.

        Args:
            investigation_id: The investigation this call belongs to.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            cached_input_tokens: Number of input tokens served from cache.
        """
        record = self._active.get(investigation_id)
        if record is None:
            return

        record.api_calls += 1
        record.usage.input_tokens += input_tokens
        record.usage.output_tokens += output_tokens
        record.usage.cached_input_tokens += cached_input_tokens
        record.usage.total_tokens += input_tokens + output_tokens

    def finish_tracking(self, investigation_id: str) -> InvestigationUsageRecord | None:
        """Finish tracking and compute final cost.

        Args:
            investigation_id: The investigation to finalize.

        Returns:
            The completed usage record, or None if not found.
        """
        record = self._active.pop(investigation_id, None)
        if record is None:
            return None

        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.usage.estimated_cost_usd = self.estimate_cost(
            model=record.model,
            input_tokens=record.usage.input_tokens,
            output_tokens=record.usage.output_tokens,
            cached_input_tokens=record.usage.cached_input_tokens,
        )

        self._history.append(record)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

        return record

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> float:
        """Estimate cost in USD for a given token count.

        Args:
            model: Claude model name.
            input_tokens: Number of input tokens (non-cached).
            output_tokens: Number of output tokens.
            cached_input_tokens: Number of cached input tokens.

        Returns:
            Estimated cost in USD.
        """
        pricing = MODEL_PRICING.get(model)
        if pricing is None:
            # Fall back to sonnet pricing if model is unknown
            pricing = MODEL_PRICING["claude-sonnet-4-6"]

        # Non-cached input tokens = total input - cached
        non_cached_input = max(0, input_tokens - cached_input_tokens)

        cost = (
            (non_cached_input / 1_000_000) * pricing["input"]
            + (cached_input_tokens / 1_000_000) * pricing["cached_input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        return cost

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent usage history.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of usage record dictionaries, most recent first.
        """
        records = self._history[-limit:]
        records.reverse()
        return [r.to_dict() for r in records]

    def get_total_usage(self) -> dict[str, Any]:
        """Return aggregate usage statistics across all tracked investigations.

        Returns:
            Dictionary with total tokens, cost, and investigation count.
        """
        total_input = sum(r.usage.input_tokens for r in self._history)
        total_output = sum(r.usage.output_tokens for r in self._history)
        total_cached = sum(r.usage.cached_input_tokens for r in self._history)
        total_cost = sum(r.usage.estimated_cost_usd for r in self._history)
        total_calls = sum(r.api_calls for r in self._history)

        return {
            "total_investigations": len(self._history),
            "total_api_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cached_input_tokens": total_cached,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 4),
        }
