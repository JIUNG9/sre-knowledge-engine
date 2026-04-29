"""Concrete :class:`Consumer` implementations.

Each submodule is optional — importing a consumer that depends on a
package not installed in the current environment must not crash this
package's import. The ``KubernetesConsumer`` raises
:class:`ConsumerUnavailable` lazily at instantiation time; here we just
guard the import so the surface is clean either way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["KubernetesConsumer"]

if TYPE_CHECKING:
    from .k8s import KubernetesConsumer  # noqa: F401

try:
    from .k8s import KubernetesConsumer  # type: ignore[assignment]
except Exception:  # pragma: no cover - kubernetes pkg may be missing
    KubernetesConsumer = None  # type: ignore[assignment]
