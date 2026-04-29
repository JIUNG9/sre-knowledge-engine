"""Tests for :class:`state_subscription.models.StateChangeEvent`."""

from __future__ import annotations

from datetime import datetime, timezone

from state_subscription.models import StateChangeEvent


def test_is_change_true_when_values_differ() -> None:
    evt = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value="3",
        new_value="5",
        source="k8s://default/auth-service",
    )
    assert evt.is_change is True


def test_is_change_false_for_same_value() -> None:
    evt = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value="3",
        new_value="3",
        source="k8s://default/auth-service",
    )
    assert evt.is_change is False


def test_is_change_true_for_first_observation() -> None:
    """First observation: old=None, new=value — that *is* a change."""
    evt = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value=None,
        new_value="3",
        source="k8s://default/auth-service",
    )
    assert evt.is_change is True


def test_is_change_true_for_deletion() -> None:
    """Deletion: old=value, new=None — also a change."""
    evt = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:ConfigMap:default/app-config:data",
        old_value="something",
        new_value=None,
        source="k8s://default/app-config",
    )
    assert evt.is_change is True


def test_observed_at_defaults_to_utc_now() -> None:
    before = datetime.now(timezone.utc)
    evt = StateChangeEvent(
        artifact_kind="terraform",
        artifact_id="terraform:rds.tf:aurora_postgres_version",
        new_value="16",
        source="terraform://aegis-prod",
    )
    after = datetime.now(timezone.utc)
    assert evt.observed_at.tzinfo is not None
    assert before <= evt.observed_at <= after


def test_serialization_roundtrip() -> None:
    """JSON round-trip preserves every field exactly."""
    original = StateChangeEvent(
        artifact_kind="argocd",
        artifact_id="argocd:app:auth-service:targetRevision",
        old_value="abc123",
        new_value="def456",
        source="argocd://argo-cd/auth-service",
        metadata={"app_namespace": "argo-cd"},
    )
    payload = original.model_dump_json()
    rebuilt = StateChangeEvent.model_validate_json(payload)
    assert rebuilt == original


def test_metadata_defaults_to_empty_dict() -> None:
    evt = StateChangeEvent(
        artifact_kind="cloud",
        artifact_id="cloud:s3:my-bucket:lifecycle",
        new_value="enabled",
        source="cloud://aws/s3/my-bucket",
    )
    assert evt.metadata == {}
