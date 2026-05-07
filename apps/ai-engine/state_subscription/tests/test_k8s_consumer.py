"""Tests for :class:`state_subscription.consumers.k8s.KubernetesConsumer`.

Strategy:
- Inject a :class:`FakeKubeClient` so the consumer never tries to call
  ``load_incluster_config`` or ``load_kube_config``.
- Replace ``kubernetes.watch.Watch`` with :class:`FakeWatch`, which
  yields pre-loaded batches and optionally raises on tail.
- Drain ``stream()`` with a small per-event timeout — these tests must
  finish in well under a second on CI.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import pytest

from state_subscription.consumers.k8s import KubernetesConsumer
from state_subscription.models import StateChangeEvent
from state_subscription.subscriber import ConsumerUnavailable

# Imported via conftest path tweak.
from state_subscription.tests.conftest import (  # type: ignore[import-not-found]
    FakeConfigMap,
    FakeDeployment,
    FakeKubeClient,
)


pytestmark = pytest.mark.asyncio


async def _drain(
    consumer: KubernetesConsumer,
    expected: int,
    *,
    per_event_timeout: float = 1.0,
) -> list[StateChangeEvent]:
    """Pull ``expected`` events from the stream and return them.

    Waits per-event so the test can give up promptly if the consumer
    never produces (rather than hanging the whole pytest run).
    """

    events: list[StateChangeEvent] = []
    agen = consumer.stream()
    try:
        for _ in range(expected):
            event = await asyncio.wait_for(agen.__anext__(), per_event_timeout)
            events.append(event)
    finally:
        await agen.aclose()
    return events


async def test_stream_yields_first_observation_event(fake_watch, fake_kube_client):
    """First observation: old=None, new=current — emitted as one event per field."""
    fake_watch.queue(
        [
            {
                "type": "ADDED",
                "object": FakeDeployment(
                    name="auth-service", replicas=3, image="acme-corp/auth:1.0"
                ),
            }
        ]
    )
    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        backoff_base=0.0,
    )

    events = await _drain(consumer, expected=2)

    by_path = {e.artifact_id.rsplit(":", 1)[1]: e for e in events}
    assert "spec.replicas" in by_path
    assert by_path["spec.replicas"].old_value is None
    assert by_path["spec.replicas"].new_value == "3"
    assert by_path["spec.replicas"].artifact_kind == "k8s"
    assert (
        by_path["spec.replicas"].artifact_id
        == "k8s:Deployment:default/auth-service:spec.replicas"
    )
    assert "spec.template.spec.containers[0].image" in by_path


async def test_stream_filters_unchanged_resource_versions(fake_watch, fake_kube_client):
    """A duplicate watch event must NOT produce a second emission.

    We prove the filter discriminates (rather than just running slowly)
    by queuing three batches: the first observation, an identical
    duplicate, and a real change. The consumer must yield exactly two
    first-observation events, skip the duplicate, then yield exactly one
    change event for the real update.
    """

    deploy_v1 = FakeDeployment(
        name="auth-service", replicas=3, image="acme-corp/auth:1.0"
    )
    deploy_v2 = FakeDeployment(
        name="auth-service", replicas=4, image="acme-corp/auth:1.0"
    )
    fake_watch.queue(
        [
            {"type": "ADDED", "object": deploy_v1},
            {"type": "MODIFIED", "object": deploy_v1},  # same values — no change
            {"type": "MODIFIED", "object": deploy_v2},  # real change: 3 -> 4
        ]
    )
    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        backoff_base=0.0,
    )

    events = await _drain(consumer, expected=3)
    first_obs = [e for e in events if e.old_value is None]
    changes = [e for e in events if e.old_value is not None]
    assert len(first_obs) == 2
    assert len(changes) == 1
    assert changes[0].artifact_id.endswith(":spec.replicas")
    assert changes[0].old_value == "3"
    assert changes[0].new_value == "4"


async def test_stream_emits_only_changes_on_value_update(
    fake_watch, fake_kube_client
):
    deploy_v1 = FakeDeployment(
        name="auth-service", replicas=3, image="acme-corp/auth:1.0"
    )
    deploy_v2 = FakeDeployment(
        name="auth-service", replicas=5, image="acme-corp/auth:1.0"
    )
    fake_watch.queue(
        [
            {"type": "ADDED", "object": deploy_v1},
            {"type": "MODIFIED", "object": deploy_v2},  # replicas 3 -> 5
        ]
    )
    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        backoff_base=0.0,
    )

    # First observation = 2 events (replicas + image),
    # second tick = 1 event (only replicas changed).
    events = await _drain(consumer, expected=3)
    change_events = [e for e in events if e.old_value is not None]
    assert len(change_events) == 1
    assert change_events[0].artifact_id.endswith(":spec.replicas")
    assert change_events[0].old_value == "3"
    assert change_events[0].new_value == "5"


async def test_watch_disconnect_triggers_backoff_retry(
    fake_watch, fake_kube_client
):
    """First batch raises ConnectionError; second batch succeeds."""

    deploy = FakeDeployment(
        name="auth-service", replicas=2, image="acme-corp/auth:1.0"
    )
    fake_watch.queue([], tail=ConnectionError("watch disconnected"))
    fake_watch.queue([{"type": "ADDED", "object": deploy}])

    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        max_retries=3,
        backoff_base=0.0,  # zero sleep so the test stays fast
    )

    events = await _drain(consumer, expected=2)
    assert {e.artifact_id.rsplit(":", 1)[1] for e in events} == {
        "spec.replicas",
        "spec.template.spec.containers[0].image",
    }


async def test_watch_disconnect_exhausts_retries_and_raises(
    fake_watch, fake_kube_client
):
    """N+1 disconnects -> consumer raises so the engine can react."""
    for _ in range(4):
        fake_watch.queue([], tail=ConnectionError("watch disconnected"))

    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        max_retries=2,
        backoff_base=0.0,
    )

    agen = consumer.stream()
    with pytest.raises(RuntimeError, match="exhausted retries"):
        await asyncio.wait_for(agen.__anext__(), timeout=2.0)
    await agen.aclose()


async def test_consumer_unavailable_when_kubernetes_pkg_missing(monkeypatch):
    """If ``import kubernetes`` fails, ``ConsumerUnavailable`` is raised
    when no client was injected."""

    # Hide any cached kubernetes modules.
    for name in list(sys.modules):
        if name == "kubernetes" or name.startswith("kubernetes."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    # And block re-imports.
    real_find = sys.meta_path

    class _BlockKubernetes:
        def find_module(self, fullname: str, path: Any = None) -> Any:
            if fullname == "kubernetes" or fullname.startswith("kubernetes."):
                raise ImportError(f"blocked: {fullname}")
            return None

        def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
            if fullname == "kubernetes" or fullname.startswith("kubernetes."):
                raise ImportError(f"blocked: {fullname}")
            return None

    monkeypatch.setattr(sys, "meta_path", [_BlockKubernetes(), *real_find])

    with pytest.raises(ConsumerUnavailable, match="kubernetes"):
        KubernetesConsumer(
            namespaces=("default",),
            tracked_kinds=("Deployment",),
            client=None,
        )


async def test_configmap_data_change_emits_event(fake_watch, fake_kube_client):
    cm_v1 = FakeConfigMap(name="app-config", data={"FOO": "1"})
    cm_v2 = FakeConfigMap(name="app-config", data={"FOO": "2"})
    fake_watch.queue(
        [
            {"type": "ADDED", "object": cm_v1},
            {"type": "MODIFIED", "object": cm_v2},
        ]
    )
    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("ConfigMap",),
        client=fake_kube_client,
        backoff_base=0.0,
    )

    events = await _drain(consumer, expected=2)
    first, second = events
    assert first.old_value is None
    assert second.old_value == first.new_value
    assert second.new_value != first.new_value
    assert second.artifact_id == "k8s:ConfigMap:default/app-config:data"


async def test_healthcheck_calls_list_namespace(fake_watch, fake_kube_client):
    consumer = KubernetesConsumer(
        namespaces=("default",),
        tracked_kinds=("Deployment",),
        client=fake_kube_client,
        backoff_base=0.0,
    )
    ok = await consumer.healthcheck()
    assert ok is True
    assert fake_kube_client.CoreV1Api().list_namespace.calls  # type: ignore[attr-defined]


async def test_assert_read_only_passes_with_readonly_service_account(
    fake_kube_client: FakeKubeClient,
) -> None:
    """Default FakeKubeClient denies every verb. The self-check should
    issue one review per forbidden verb and return without raising."""
    consumer = KubernetesConsumer(
        namespaces=("default",),
        client=fake_kube_client,
        backoff_base=0.0,
    )
    consumer.assert_read_only()  # must not raise

    auth = fake_kube_client.AuthorizationV1Api()
    expected = len(KubernetesConsumer._FORBIDDEN_VERBS)
    assert len(auth.calls) == expected


async def test_assert_read_only_raises_when_service_account_has_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A service account that's been granted `create deployments` must
    cause the consumer to refuse to start. Simulates the design doc's
    'well-meaning operator who fixed something' (§7)."""
    from state_subscription.tests.conftest import FakeKubeClient

    bad_client = FakeKubeClient(
        allowed_verbs={("create", "deployments")}
    )
    consumer = KubernetesConsumer(
        namespaces=("default",),
        client=bad_client,
        backoff_base=0.0,
    )
    with pytest.raises(PermissionError, match="create deployments"):
        consumer.assert_read_only()


async def test_assert_read_only_skips_when_authorization_api_unavailable(
    fake_kube_client: FakeKubeClient,
) -> None:
    """Some dev clusters / tools strip the AuthorizationV1Api surface.
    We log and proceed in that case rather than blocking startup."""
    # Strip the API to mimic an environment without authorization.k8s.io.
    del fake_kube_client.__class__.AuthorizationV1Api

    consumer = KubernetesConsumer(
        namespaces=("default",),
        client=fake_kube_client,
        backoff_base=0.0,
    )
    consumer.assert_read_only()  # warns and returns; must not raise

    # Restore for downstream tests in the same session.
    def _restore(self):  # noqa: ANN001
        return self._auth
    fake_kube_client.__class__.AuthorizationV1Api = _restore  # type: ignore[assignment]
