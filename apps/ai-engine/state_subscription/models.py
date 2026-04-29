"""Pydantic models for state-subscription events.

A :class:`StateChangeEvent` is the wire format every Layer 1.5 consumer
emits. Downstream the Layer 1.6 :class:`InvalidationEngine` looks events
up by ``artifact_id`` against the dependency reverse-index and marks
affected wiki pages ``pending_revalidation``.

Pattern note: this is Change Data Capture (CDC) from database-replication
literature, applied to operational knowledge. Each event is one
write-side mutation observed in an external infra subsystem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ArtifactKind = Literal["terraform", "k8s", "argocd", "cloud", "source_file"]


class StateChangeEvent(BaseModel):
    """A change observed in an external infra artifact.

    The ``artifact_id`` is the join key with
    :class:`wiki.synthesizer.ConfigDependency.artifact_id` — both ends
    use the same string so the reverse-index lookup is a dict get.

    ``old_value`` is ``None`` for the first observation of an artifact
    (consumer just started and has no baseline). ``new_value`` is
    ``None`` when the artifact was deleted.
    """

    artifact_kind: ArtifactKind
    artifact_id: str = Field(
        description="Stable identifier matching ConfigDependency.artifact_id."
    )
    old_value: str | None = Field(
        default=None,
        description="Previous value if known. None for first-observation events.",
    )
    new_value: str | None = Field(
        default=None,
        description="Current value. None means the artifact was deleted.",
    )
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = Field(
        description=(
            "Which consumer emitted this. Free-form but conventionally "
            "'<kind>://<scope>'. e.g. 'k8s://default/auth-service'."
        )
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_change(self) -> bool:
        """``False`` when ``old_value == new_value``.

        Consumers SHOULD filter on this before emitting so the
        downstream invalidation engine doesn't re-mark unchanged pages.
        """

        return self.old_value != self.new_value
