"""Kubernetes state-change consumer.

Watches ``Deployment`` / ``StatefulSet`` / ``ConfigMap`` / ``Secret``
metadata across configured namespaces and emits
:class:`StateChangeEvent` whenever a tracked field changes value.

Why a thread bridge?
    The official ``kubernetes`` Python client exposes
    ``watch.Watch().stream(...)`` as a *blocking* iterator. Wrapping
    one call in :func:`asyncio.to_thread` would only return the next
    event then exit; we need a continuous stream. The robust pattern
    is one daemon :class:`threading.Thread` per ``(kind, namespace)``
    running the blocking loop and pushing onto an
    :class:`asyncio.Queue` via :meth:`asyncio.AbstractEventLoop.call_soon_threadsafe`.
    The async generator just awaits ``queue.get()``.

Why an injectable client?
    The :class:`kubernetes` package may not be installed (it is an
    optional dep). Passing an explicit ``client`` to ``__init__``
    keeps the test seam clean and skips the real ``load_kube_config``
    branch entirely. Production callers leave ``client=None`` and let
    :meth:`_init_client` resolve it.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import AsyncIterator, Iterable
from typing import Any

from ..models import StateChangeEvent
from ..subscriber import Consumer, ConsumerUnavailable

logger = logging.getLogger("aegis.state_subscription.k8s")


# Default kinds we watch. All four are common sources of "the running
# system disagrees with the documented system" — the exact category
# the wiki vault cares about.
DEFAULT_TRACKED_KINDS: tuple[str, ...] = (
    "Deployment",
    "StatefulSet",
    "ConfigMap",
    "Secret",
)

# Sentinel pushed by watcher threads to signal "I'm done / I crashed".
# The drain loop checks the type and either exits cleanly or raises.
_STREAM_END = object()
_STREAM_ERROR = object()


class KubernetesConsumer(Consumer):
    """Long-running watcher over Kubernetes core/apps API objects.

    artifact_id format: ``k8s:<Kind>:<namespace>/<name>:<jsonpath>``.
    Examples:
        - ``k8s:Deployment:default/auth-service:spec.replicas``
        - ``k8s:Deployment:default/auth-service:spec.template.spec.containers[0].image``
        - ``k8s:ConfigMap:default/app-config:data``
        - ``k8s:Secret:default/db-creds:metadata.resourceVersion``

    Note: Secret *values* are deliberately never read — we only emit on
    ``metadata.resourceVersion`` changes so the wiki engine learns that
    "something changed" without us logging plaintext credentials.
    """

    name = "kubernetes"

    def __init__(
        self,
        namespaces: Iterable[str] = ("default",),
        tracked_kinds: Iterable[str] = DEFAULT_TRACKED_KINDS,
        *,
        client: Any | None = None,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        queue_maxsize: int = 1000,
    ) -> None:
        """Wire up namespaces, kinds, and the (optional) injected client.

        Args:
            namespaces: Namespaces to watch. Each (kind, namespace) pair
                gets its own watcher thread.
            tracked_kinds: Subset of :data:`DEFAULT_TRACKED_KINDS`.
            client: Pre-built ``kubernetes.client`` module. When ``None``
                we attempt in-cluster config first, then ``~/.kube/config``,
                and raise :class:`ConsumerUnavailable` if neither works.
            max_retries: Retries before a watcher thread gives up after
                disconnect.
            backoff_base: Multiplier for the exponential-backoff sleep
                between retries. Tests pass ``0.0`` to keep them fast.
            queue_maxsize: Bound on the in-memory event queue. A slow
                downstream invalidation engine will eventually block
                the watcher threads — better than unbounded growth.
        """

        self.namespaces = list(namespaces)
        self.tracked_kinds = list(tracked_kinds)
        self._client = client if client is not None else self._init_client()
        self._max_retries = max(0, int(max_retries))
        self._backoff_base = max(0.0, float(backoff_base))
        self._queue_maxsize = queue_maxsize

        # artifact_id -> last observed string value. Mutated only inside
        # watcher threads, but each artifact_id is owned by exactly one
        # thread (kind+namespace combo) so no lock is required.
        self._last_values: dict[str, str | None] = {}
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    # -- Internals: kubernetes client wiring --------------------------

    def _init_client(self) -> Any:
        """Resolve a kubernetes client module or raise :class:`ConsumerUnavailable`.

        Order: in-cluster config (works on Pods with a ServiceAccount)
        → kubeconfig (works on developer laptops). If both fail we raise
        so the caller can choose whether to skip the consumer.
        """

        try:
            from kubernetes import client, config as kube_config  # type: ignore
        except ImportError as exc:
            raise ConsumerUnavailable(
                "kubernetes Python client not installed. "
                "Run `pip install kubernetes` to enable the k8s consumer."
            ) from exc

        try:
            kube_config.load_incluster_config()
            logger.info("k8s consumer: loaded in-cluster config")
            return client
        except Exception as in_cluster_exc:  # noqa: BLE001
            logger.debug(
                "k8s consumer: in-cluster config unavailable: %s",
                in_cluster_exc,
            )

        try:
            kube_config.load_kube_config()
            logger.info("k8s consumer: loaded kubeconfig from disk")
            return client
        except Exception as kc_exc:  # noqa: BLE001
            raise ConsumerUnavailable(
                f"No Kubernetes credentials found "
                f"(neither in-cluster nor ~/.kube/config): {kc_exc}"
            ) from kc_exc

    # -- Public API: stream + healthcheck -----------------------------

    async def stream(self) -> AsyncIterator[StateChangeEvent]:
        """Spawn watcher threads and yield events from the shared queue.

        The generator owns the threads' lifecycle: when the consumer
        is cancelled (the caller breaks the ``async for`` loop or its
        task is cancelled) we set ``_stop_event`` and let the threads
        exit on their next watch tick.
        """

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_maxsize)

        for kind in self.tracked_kinds:
            for namespace in self.namespaces:
                thread = threading.Thread(
                    target=self._watch_loop,
                    args=(loop, queue, kind, namespace),
                    name=f"k8s-watch-{kind}-{namespace}",
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)

        try:
            while True:
                event = await queue.get()
                if event is _STREAM_END:
                    # One thread finished; keep draining as long as
                    # any other thread is still alive.
                    if not any(t.is_alive() for t in self._threads):
                        return
                    continue
                if event is _STREAM_ERROR:
                    # Bubble up — the engine will log and unsubscribe us.
                    raise RuntimeError("k8s watcher thread exhausted retries")
                if isinstance(event, StateChangeEvent):
                    yield event
        finally:
            self._stop_event.set()

    async def healthcheck(self) -> bool:
        """Cheap probe: list one namespace.

        Returns ``False`` on any exception so the orchestrator can
        surface "consumer unhealthy" without losing the actual stream.
        """

        try:
            v1 = self._client.CoreV1Api()
            await asyncio.to_thread(v1.list_namespace, limit=1)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("k8s consumer: healthcheck failed: %s", exc)
            return False

    # -- Internals: per-thread watch loop -----------------------------

    def _watch_loop(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Any],
        kind: str,
        namespace: str,
    ) -> None:
        """Run inside a daemon thread; bridge the sync watch to asyncio.

        Pulls from ``watch.Watch().stream(api.list_*, namespace=ns)``,
        dispatches every event to :meth:`_emit_changes_for_object`, and
        retries with exponential backoff on disconnects. After
        ``max_retries`` consecutive failures we push ``_STREAM_ERROR``
        and exit so the async caller can re-raise.
        """

        retries = 0
        while not self._stop_event.is_set():
            try:
                self._run_watch_once(loop, queue, kind, namespace)
                retries = 0
            except Exception as exc:  # noqa: BLE001 - watch raises broad types
                if self._stop_event.is_set():
                    break
                retries += 1
                if retries > self._max_retries:
                    logger.error(
                        "k8s consumer: watcher %s/%s exhausted retries (%d): %s",
                        kind,
                        namespace,
                        retries,
                        exc,
                    )
                    self._enqueue(loop, queue, _STREAM_ERROR)
                    return
                sleep_for = self._backoff_base * (2 ** (retries - 1))
                logger.warning(
                    "k8s consumer: watcher %s/%s disconnected (%s); "
                    "retry %d/%d in %.2fs",
                    kind,
                    namespace,
                    exc,
                    retries,
                    self._max_retries,
                    sleep_for,
                )
                if sleep_for > 0:
                    if self._stop_event.wait(sleep_for):
                        break

        self._enqueue(loop, queue, _STREAM_END)

    def _run_watch_once(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Any],
        kind: str,
        namespace: str,
    ) -> None:
        """One full ``watch.stream()`` pass; raises when the stream ends."""

        from kubernetes import watch as kube_watch  # type: ignore

        list_fn = self._list_fn_for(kind, namespace)
        if list_fn is None:
            logger.warning(
                "k8s consumer: no list function for kind %s; thread exiting",
                kind,
            )
            return

        watcher = kube_watch.Watch()
        for evt in watcher.stream(list_fn, namespace=namespace):
            if self._stop_event.is_set():
                watcher.stop()
                return
            obj = evt.get("object")
            if obj is None:
                continue
            self._emit_changes_for_object(loop, queue, kind, namespace, obj)

    def _list_fn_for(self, kind: str, namespace: str) -> Any | None:
        """Map a Kind to the right ``list_namespaced_*`` API function.

        We resolve lazily so the consumer can be constructed without
        the ``apps_v1`` API being touched (handy in tests).
        """

        if kind in ("ConfigMap", "Secret"):
            api = self._client.CoreV1Api()
        elif kind in ("Deployment", "StatefulSet"):
            api = self._client.AppsV1Api()
        else:
            return None

        method_map = {
            "Deployment": "list_namespaced_deployment",
            "StatefulSet": "list_namespaced_stateful_set",
            "ConfigMap": "list_namespaced_config_map",
            "Secret": "list_namespaced_secret",
        }
        return getattr(api, method_map[kind], None)

    # -- Internals: object → event translation -------------------------

    def _emit_changes_for_object(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Any],
        kind: str,
        namespace: str,
        obj: Any,
    ) -> None:
        """Translate one watch event into zero or more :class:`StateChangeEvent`.

        Each tracked field becomes an artifact_id; we compare the new
        value to ``_last_values`` and only emit on actual change. First
        observation emits with ``old_value=None``.
        """

        meta = _attr(obj, "metadata")
        if meta is None:
            return
        name = _attr(meta, "name") or "unknown"
        source = f"k8s://{namespace}/{name}"

        for jsonpath, value in _extract_tracked_fields(kind, obj):
            artifact_id = f"k8s:{kind}:{namespace}/{name}:{jsonpath}"
            previous = self._last_values.get(artifact_id, _UNSET)
            if previous is _UNSET:
                # First observation — record but emit with old_value=None.
                self._last_values[artifact_id] = value
                event = StateChangeEvent(
                    artifact_kind="k8s",
                    artifact_id=artifact_id,
                    old_value=None,
                    new_value=value,
                    source=source,
                    metadata={"kind": kind, "name": name, "namespace": namespace},
                )
                self._enqueue(loop, queue, event)
                continue
            if previous == value:
                continue
            event = StateChangeEvent(
                artifact_kind="k8s",
                artifact_id=artifact_id,
                old_value=previous,
                new_value=value,
                source=source,
                metadata={"kind": kind, "name": name, "namespace": namespace},
            )
            self._last_values[artifact_id] = value
            self._enqueue(loop, queue, event)

    def _enqueue(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Any],
        item: Any,
    ) -> None:
        """Push ``item`` onto the asyncio queue from a worker thread.

        Uses :meth:`asyncio.AbstractEventLoop.call_soon_threadsafe` —
        ``queue.put_nowait`` is the only :class:`asyncio.Queue` method
        safe to call cross-thread when scheduled this way. If the queue
        is bounded and full, ``put_nowait`` raises and we drop the event
        with a warning rather than blocking the watcher thread.
        """

        def _put() -> None:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                logger.warning(
                    "k8s consumer: event queue full; dropping event (raise queue_maxsize)"
                )

        try:
            loop.call_soon_threadsafe(_put)
        except RuntimeError:
            # Loop already closed — caller cancelled. Nothing to do.
            pass


# -- Module helpers ---------------------------------------------------


_UNSET = object()


def _attr(obj: Any, name: str) -> Any:
    """Read an attribute or dict key.

    The kubernetes client returns CamelCase attribute objects, but tests
    pass plain dicts. Supporting both makes the test seam minimal.
    """

    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _extract_tracked_fields(kind: str, obj: Any) -> list[tuple[str, str | None]]:
    """Return ``[(jsonpath, value)]`` pairs the consumer tracks for ``kind``.

    We deliberately stringify everything so the diff logic in
    :class:`KubernetesConsumer` can rely on plain string equality —
    a ``replicas`` int and a ConfigMap dict end up comparable.
    """

    out: list[tuple[str, str | None]] = []
    if kind == "Deployment" or kind == "StatefulSet":
        spec = _attr(obj, "spec")
        replicas = _attr(spec, "replicas") if spec is not None else None
        out.append(("spec.replicas", _stringify(replicas)))

        template = _attr(spec, "template") if spec is not None else None
        tpl_spec = _attr(template, "spec") if template is not None else None
        containers = _attr(tpl_spec, "containers") if tpl_spec is not None else None
        for idx, container in enumerate(containers or []):
            image = _attr(container, "image")
            out.append(
                (f"spec.template.spec.containers[{idx}].image", _stringify(image))
            )
    elif kind == "ConfigMap":
        data = _attr(obj, "data")
        # Stable string of the data dict — sorted keys so re-orderings
        # don't false-positive a change.
        if data is None:
            out.append(("data", None))
        else:
            try:
                items = sorted(dict(data).items())
            except TypeError:
                items = list(dict(data).items())
            out.append(("data", repr(items)))
    elif kind == "Secret":
        # Never read Secret.data — only the resource version proves
        # *something* changed.
        meta = _attr(obj, "metadata")
        rv = _attr(meta, "resource_version") if meta is not None else None
        if rv is None and meta is not None:
            rv = _attr(meta, "resourceVersion")
        out.append(("metadata.resourceVersion", _stringify(rv)))
    return out


def _stringify(value: Any) -> str | None:
    """Coerce a watched field to ``str | None`` for value-equality checks."""

    if value is None:
        return None
    return str(value)
