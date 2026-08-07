"""Consumer protocol + base class for Layer 1.5 state subscription.

We use :class:`abc.ABC` (not :class:`typing.Protocol`) to match the
existing reconciliation/connectors style in this codebase — those
modules already inherit from concrete bases like
:class:`reconciliation.sources.DocSource`. ABCs also give us a place
to hang shared behavior later (e.g. a default backoff retry helper)
without a structural-typing mismatch.

A consumer is a long-running async generator. Crash policy: if the
generator raises, that consumer's stream ends; the
:class:`InvalidationEngine` logs and continues with whatever consumers
remain. One bad ServiceAccount must not silently take down every
other watcher.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .models import StateChangeEvent


class ConsumerUnavailable(RuntimeError):
    """Raised when a consumer cannot reach its backing system at init.

    Callers (typically the AI engine bootstrap) catch this and either
    skip the consumer entirely or schedule a retry. The exception message
    should explain *what* is missing (no ``~/.kube/config``, package
    not installed, etc.) so an operator can fix it without digging
    into source.
    """


class Consumer(ABC):
    """A long-running observer of an external infra subsystem.

    Subclasses implement :meth:`stream` as an async generator yielding
    :class:`StateChangeEvent` values. They MAY override :meth:`healthcheck`
    with a real liveness probe; the default returns ``True``.

    Subclasses should set ``name`` as a class attribute so log lines and
    audit records can attribute events back to the emitter.
    """

    name: str = "consumer"

    @abstractmethod
    def stream(self) -> AsyncIterator[StateChangeEvent]:
        """Yield :class:`StateChangeEvent` values until cancelled.

        This must be an async generator (``async def`` + ``yield``) or
        an object with ``__aiter__``. The engine drains it via
        ``async for event in consumer.stream()``.
        """

    async def healthcheck(self) -> bool:
        """Return ``True`` when the underlying system is reachable.

        Default implementation always returns ``True`` — override when
        the subsystem exposes a cheap probe call (e.g. ``list_namespace
        limit=1`` on Kubernetes). Health is reported in
        ``/health`` style endpoints, not used for routing decisions.
        """

        return True
