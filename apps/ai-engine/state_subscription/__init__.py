"""State subscription — Layer 1.5.

Long-running consumers observe external infra subsystems (Kubernetes,
Terraform state, ArgoCD, cloud APIs, source files) and emit
:class:`StateChangeEvent` values whenever a tracked artifact changes.
The Layer 1.6 :class:`InvalidationEngine` consumes these events and
marks dependent wiki pages ``pending_revalidation``.

Optimistic imports: the :class:`KubernetesConsumer` requires the
``kubernetes`` Python package, which is not in the core requirements.
A missing dep leaves ``KubernetesConsumer = None`` and the rest of the
package still imports — matching the wiki/contradiction pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "Consumer",
    "ConsumerUnavailable",
    "StateChangeEvent",
    "ArtifactKind",
    "KubernetesConsumer",
]

if TYPE_CHECKING:
    from .consumers.k8s import KubernetesConsumer  # noqa: F401
    from .models import ArtifactKind, StateChangeEvent  # noqa: F401
    from .subscriber import Consumer, ConsumerUnavailable  # noqa: F401


try:
    from .models import ArtifactKind, StateChangeEvent  # type: ignore[assignment]
except Exception:  # pragma: no cover
    StateChangeEvent = None  # type: ignore[assignment]
    ArtifactKind = None  # type: ignore[assignment]

try:
    from .subscriber import Consumer, ConsumerUnavailable  # type: ignore[assignment]
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore[assignment]
    ConsumerUnavailable = None  # type: ignore[assignment]

try:
    from .consumers.k8s import KubernetesConsumer  # type: ignore[assignment]
except Exception:  # pragma: no cover
    KubernetesConsumer = None  # type: ignore[assignment]
