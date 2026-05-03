"""Pydantic models for the Layer 1.6 invalidation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


InvalidationReason = Literal[
    "value_change",
    "first_observation",
    "consumer_init",
]


class InvalidationRecord(BaseModel):
    """Audit record for one invalidation decision.

    The engine writes one of these per :class:`StateChangeEvent`
    handled — even when no pages were affected — so the JSONL log is a
    complete history of "what did the consumer see, and what did the
    engine do about it?". That's the replay surface for incident review.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    artifact_id: str = Field(description="The changed artifact_id.")
    affected_slugs: list[str] = Field(
        default_factory=list,
        description="Wiki page slugs marked pending_revalidation.",
    )
    reason: InvalidationReason = Field(
        description=(
            "Why this invalidation fired. 'value_change' for normal "
            "transitions, 'first_observation' when the consumer just "
            "started, 'consumer_init' for a manual rebuild."
        )
    )
    old_value: str | None = None
    new_value: str | None = None
    shadow_mode: bool = Field(
        default=False,
        description=(
            "When True, the engine logged this record without mutating "
            "any wiki pages. Useful for canary rollouts."
        ),
    )
