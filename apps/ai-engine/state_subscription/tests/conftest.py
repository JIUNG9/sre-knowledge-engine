"""Shared pytest fixtures for the state_subscription test suite.

We never touch a real cluster: tests inject a :class:`FakeKubeClient`
into :class:`KubernetesConsumer` via the ``client=`` constructor arg,
and patch :mod:`kubernetes.watch` (or its absence) per-test. Keeping
the path-tweak local matches the scheduler/reconciliation conftests.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

# Resolve `from state_subscription.x import ...` to apps/ai-engine.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))


# -- Fake kubernetes objects ------------------------------------------ #


class _FakeMeta:
    def __init__(self, name: str, resource_version: str = "1") -> None:
        self.name = name
        self.resource_version = resource_version


class _FakeContainer:
    def __init__(self, image: str) -> None:
        self.image = image


class _FakeTemplateSpec:
    def __init__(self, containers: list[_FakeContainer]) -> None:
        self.containers = containers


class _FakeTemplate:
    def __init__(self, spec: _FakeTemplateSpec) -> None:
        self.spec = spec


class _FakeDeploymentSpec:
    def __init__(self, replicas: int, containers: list[_FakeContainer]) -> None:
        self.replicas = replicas
        self.template = _FakeTemplate(_FakeTemplateSpec(containers))


class FakeDeployment:
    """Minimal stand-in for ``V1Deployment``."""

    def __init__(
        self,
        name: str,
        replicas: int,
        image: str,
        resource_version: str = "1",
    ) -> None:
        self.metadata = _FakeMeta(name, resource_version)
        self.spec = _FakeDeploymentSpec(replicas, [_FakeContainer(image)])


class FakeConfigMap:
    """Minimal stand-in for ``V1ConfigMap``."""

    def __init__(
        self, name: str, data: dict[str, str], resource_version: str = "1"
    ) -> None:
        self.metadata = _FakeMeta(name, resource_version)
        self.data = data


class FakeSecret:
    """Minimal stand-in for ``V1Secret`` (we only read metadata)."""

    def __init__(self, name: str, resource_version: str = "1") -> None:
        self.metadata = _FakeMeta(name, resource_version)


# -- Fake kubernetes client module ------------------------------------ #


class _FakeNamespacedList:
    """Stub for ``list_namespaced_*`` calls."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append({"args": args, "kwargs": kwargs})
        return None


class _FakeAppsV1Api:
    def __init__(self) -> None:
        self.list_namespaced_deployment = _FakeNamespacedList(
            "list_namespaced_deployment"
        )
        self.list_namespaced_stateful_set = _FakeNamespacedList(
            "list_namespaced_stateful_set"
        )


class _FakeCoreV1Api:
    def __init__(self) -> None:
        self.list_namespaced_config_map = _FakeNamespacedList(
            "list_namespaced_config_map"
        )
        self.list_namespaced_secret = _FakeNamespacedList("list_namespaced_secret")
        self.list_namespace = _FakeNamespacedList("list_namespace")


class FakeKubeClient:
    """In-memory stand-in for the ``kubernetes.client`` module."""

    def __init__(self) -> None:
        self._apps = _FakeAppsV1Api()
        self._core = _FakeCoreV1Api()

    def AppsV1Api(self) -> _FakeAppsV1Api:  # noqa: N802 - mirror real API
        return self._apps

    def CoreV1Api(self) -> _FakeCoreV1Api:  # noqa: N802 - mirror real API
        return self._core


# -- Fake watch ------------------------------------------------------- #


class FakeWatch:
    """Replacement for ``kubernetes.watch.Watch``.

    Tests pre-load a queue of *batches* — each batch is a list of
    ``{type, object}`` dicts that one ``stream(...)`` call will yield
    before raising the configured tail exception (or :class:`StopIteration`
    if none). Subsequent ``stream`` calls pop the next batch, simulating
    reconnect-after-disconnect behavior.
    """

    # Class-level batches so the consumer's own ``Watch()`` call hits us.
    batches: list[tuple[list[dict[str, Any]], Exception | None]] = []
    instances: list["FakeWatch"] = []

    @classmethod
    def reset(cls) -> None:
        cls.batches = []
        cls.instances = []

    @classmethod
    def queue(
        cls,
        events: Iterable[dict[str, Any]],
        tail: Exception | None = None,
    ) -> None:
        cls.batches.append((list(events), tail))

    def __init__(self) -> None:
        self.stopped = False
        FakeWatch.instances.append(self)

    def stream(self, *_args: Any, **_kwargs: Any) -> Iterable[dict[str, Any]]:
        if not FakeWatch.batches:
            return iter(())
        events, tail = FakeWatch.batches.pop(0)

        def _gen() -> Iterable[dict[str, Any]]:
            for evt in events:
                if self.stopped:
                    return
                yield evt
            if tail is not None:
                raise tail
            # No tail — natural end mimics watch returning normally.

        return _gen()

    def stop(self) -> None:
        self.stopped = True


# -- Fixtures --------------------------------------------------------- #


@pytest.fixture
def fake_kube_client() -> FakeKubeClient:
    return FakeKubeClient()


@pytest.fixture
def fake_watch(monkeypatch: pytest.MonkeyPatch) -> type[FakeWatch]:
    """Patch ``kubernetes.watch.Watch`` to :class:`FakeWatch` for the test."""
    FakeWatch.reset()

    # Build a fake ``kubernetes`` package tree if the real one is absent.
    fake_pkg = sys.modules.setdefault("kubernetes", _make_fake_kubernetes_pkg())
    fake_watch_module = getattr(fake_pkg, "watch", None) or _make_fake_watch_module()
    fake_watch_module.Watch = FakeWatch  # type: ignore[attr-defined]
    sys.modules["kubernetes.watch"] = fake_watch_module
    monkeypatch.setattr(fake_pkg, "watch", fake_watch_module, raising=False)
    yield FakeWatch
    FakeWatch.reset()


def _make_fake_kubernetes_pkg() -> Any:
    """Construct a minimal ``kubernetes`` module so ``import kubernetes`` works."""
    import types

    pkg = types.ModuleType("kubernetes")
    pkg.__path__ = []  # type: ignore[attr-defined] - mark as a package
    pkg.client = types.ModuleType("kubernetes.client")  # type: ignore[attr-defined]
    pkg.config = types.ModuleType("kubernetes.config")  # type: ignore[attr-defined]
    pkg.watch = _make_fake_watch_module()  # type: ignore[attr-defined]

    def _no_in_cluster() -> None:
        raise RuntimeError("no in-cluster config")

    def _no_kube_config() -> None:
        raise RuntimeError("no kubeconfig on disk")

    pkg.config.load_incluster_config = _no_in_cluster  # type: ignore[attr-defined]
    pkg.config.load_kube_config = _no_kube_config  # type: ignore[attr-defined]
    sys.modules["kubernetes.client"] = pkg.client  # type: ignore[attr-defined]
    sys.modules["kubernetes.config"] = pkg.config  # type: ignore[attr-defined]
    return pkg


def _make_fake_watch_module() -> Any:
    import types

    mod = types.ModuleType("kubernetes.watch")
    mod.Watch = FakeWatch  # type: ignore[attr-defined]
    return mod
