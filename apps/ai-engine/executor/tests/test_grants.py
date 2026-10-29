"""Grant store + Executor grant flow.

The grant is the only way an HTTP caller can get an action executed, so
these tests pin its three properties: bound to the action, short-lived,
single use. They also check that a grant can't be minted from a decision
that wouldn't clear the approval gate.
"""

from __future__ import annotations

import threading
from dataclasses import replace

import pytest

from executor.executor import Executor
from executor.grants import GrantError, GrantStore, action_digest
from executor.tests.conftest import FakeAction, make_decision


class FakeClock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def scale_action(replicas: int = 3) -> FakeAction:
    return FakeAction(
        name="scale-checkout",
        verb="scale",
        target="deployment/checkout",
        metadata={"replicas": replicas, "namespace": "shop"},
    )


# --------------------------------------------------------------------------- #
# Digest
# --------------------------------------------------------------------------- #


def test_digest_is_stable_across_metadata_key_order() -> None:
    a = FakeAction(metadata={"replicas": 3, "namespace": "shop"})
    b = FakeAction(metadata={"namespace": "shop", "replicas": 3})
    assert action_digest(a) == action_digest(b)


@pytest.mark.parametrize(
    "change",
    [
        {"verb": "rollout-restart"},
        {"target": "deployment/payments"},
        {"environment": "prod"},
        {"category": "terraform"},
        {"metadata": {"replicas": 0, "namespace": "shop"}},
        {"name": "something-else"},
    ],
)
def test_digest_changes_when_any_bound_field_changes(change: dict) -> None:
    base = scale_action()
    assert action_digest(base) != action_digest(replace(base, **change))


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #


def _issue(store: GrantStore, action: FakeAction):
    return store.issue(
        action, tier="EXECUTE", approvers=("june", "alice"),
        required_approvals=2, backend="test",
    )


def test_grant_is_single_use() -> None:
    store = GrantStore()
    action = scale_action()
    grant = _issue(store, action)
    store.consume(grant.grant_id, action)
    with pytest.raises(GrantError) as exc:
        store.consume(grant.grant_id, action)
    assert exc.value.reason == "grant_unknown_or_used"


def test_grant_expires() -> None:
    clock = FakeClock()
    store = GrantStore(ttl_seconds=900, clock=clock)
    action = scale_action()
    grant = _issue(store, action)
    clock.now += 900
    with pytest.raises(GrantError) as exc:
        store.consume(grant.grant_id, action)
    assert exc.value.reason == "grant_expired"
    assert len(store) == 0


def test_mismatch_is_refused_and_does_not_burn_the_grant() -> None:
    store = GrantStore()
    approved = scale_action(replicas=3)
    grant = _issue(store, approved)
    with pytest.raises(GrantError) as exc:
        store.consume(grant.grant_id, scale_action(replicas=0))
    assert exc.value.reason == "grant_action_mismatch"
    # The approved action still runs.
    assert store.consume(grant.grant_id, approved).grant_id == grant.grant_id


def test_peek_leaves_the_grant_usable() -> None:
    store = GrantStore()
    action = scale_action()
    grant = _issue(store, action)
    store.peek(grant.grant_id, action)
    store.consume(grant.grant_id, action)


def test_concurrent_consume_only_one_wins() -> None:
    store = GrantStore()
    action = scale_action()
    grant = _issue(store, action)
    wins: list[str] = []
    losses: list[str] = []
    barrier = threading.Barrier(16)

    def worker() -> None:
        barrier.wait()
        try:
            store.consume(grant.grant_id, action)
            wins.append("ok")
        except GrantError as exc:
            losses.append(exc.reason)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1
    assert losses == ["grant_unknown_or_used"] * 15


def test_expired_grants_are_swept_on_issue() -> None:
    clock = FakeClock()
    store = GrantStore(ttl_seconds=10, clock=clock)
    _issue(store, scale_action(1))
    _issue(store, scale_action(2))
    clock.now += 11
    _issue(store, scale_action(3))
    assert len(store) == 1


def test_ttl_must_be_positive() -> None:
    with pytest.raises(ValueError):
        GrantStore(ttl_seconds=0)


# --------------------------------------------------------------------------- #
# Executor.issue_grant / execute_with_grant
# --------------------------------------------------------------------------- #


def test_issue_grant_refuses_non_execute_tier(executor: Executor) -> None:
    with pytest.raises(GrantError) as exc:
        executor.issue_grant(scale_action(), make_decision(tier="PROPOSE"))
    assert exc.value.reason == "not_approved_for_execution"


def test_issue_grant_refuses_short_approvals(executor: Executor) -> None:
    with pytest.raises(GrantError) as exc:
        executor.issue_grant(scale_action(), make_decision(approvers=("june",)))
    assert exc.value.reason == "insufficient_approvals"


def test_same_approver_twice_counts_once(executor: Executor) -> None:
    with pytest.raises(GrantError) as exc:
        executor.issue_grant(
            scale_action(), make_decision(approvers=("june", "june"))
        )
    assert exc.value.reason == "insufficient_approvals"


def test_execute_with_grant_runs_and_uses_it_up(make_executor, fake_binary) -> None:
    ex = make_executor(dry_run_default=False)
    action = scale_action()
    grant = ex.issue_grant(action, make_decision())

    first = ex.execute_with_grant(action, grant.grant_id)
    second = ex.execute_with_grant(action, grant.grant_id)

    assert first.outcome == "executed"
    assert first.dry_run is False
    assert len(fake_binary) == 1
    assert second.outcome == "refused"
    assert second.refused_reason == "grant_unknown_or_used"


def test_dry_run_with_grant_does_not_use_it_up(executor: Executor) -> None:
    action = scale_action()
    grant = executor.issue_grant(action, make_decision())
    preview = executor.execute_with_grant(action, grant.grant_id, dry_run=True)
    assert preview.dry_run is True
    assert len(executor.grants) == 1


def test_execute_with_grant_refuses_a_changed_action(
    executor: Executor, fake_binary
) -> None:
    grant = executor.issue_grant(scale_action(replicas=3), make_decision())
    result = executor.execute_with_grant(
        scale_action(replicas=0), grant.grant_id, dry_run=False
    )
    assert result.outcome == "refused"
    assert result.refused_reason == "grant_action_mismatch"
    assert fake_binary == []


def test_grant_refusal_is_audited(executor: Executor) -> None:
    executor.execute_with_grant(scale_action(), "not-a-grant", dry_run=False)
    rows = executor.audit.read_recent(limit=5)
    assert rows[0]["refused_reason"] == "grant_unknown_or_used"


def test_kill_switch_refusal_leaves_the_grant_usable(
    make_executor, killswitch_tripped, fake_binary
) -> None:
    ex = make_executor(dry_run_default=False, killswitch_check=killswitch_tripped)
    action = scale_action()
    grant = ex.issue_grant(action, make_decision())
    result = ex.execute_with_grant(action, grant.grant_id)
    assert result.refused_reason.startswith("killswitch_active")
    assert len(ex.grants) == 1
    assert fake_binary == []


def test_audit_row_names_the_grant(make_executor, fake_binary) -> None:
    ex = make_executor(dry_run_default=False)
    action = scale_action()
    grant = ex.issue_grant(action, make_decision())
    ex.execute_with_grant(action, grant.grant_id)
    row = ex.audit.read_recent(limit=1)[0]
    assert row["metadata"]["grant"] == grant.grant_id[:8]
    assert row["metadata"]["approval_backend"] == "test"


def test_non_json_metadata_is_refused_at_issue(executor: Executor) -> None:
    class Sneaky:
        def __str__(self) -> str:
            return "3"

    action = FakeAction(verb="scale", metadata={"replicas": Sneaky()})
    with pytest.raises(TypeError):
        executor.issue_grant(action, make_decision())


def test_ttl_has_an_upper_bound() -> None:
    with pytest.raises(ValueError):
        GrantStore(ttl_seconds=3601)


@pytest.mark.parametrize("raw", ["enabled", "y", "On", ""])
def test_typo_does_not_turn_dry_run_off(monkeypatch, raw: str) -> None:
    from executor.config import ExecutorConfig

    monkeypatch.setenv("AEGIS_EXECUTOR_DRY_RUN", raw)
    monkeypatch.setenv("AEGIS_EXECUTOR_REQUIRE_TWO_APPROVALS", raw)
    cfg = ExecutorConfig.from_env()
    assert cfg.dry_run_default is True
    assert cfg.require_two_approvals_for_execute is True


def test_explicit_false_turns_dry_run_off(monkeypatch) -> None:
    from executor.config import ExecutorConfig

    monkeypatch.setenv("AEGIS_EXECUTOR_DRY_RUN", "0")
    assert ExecutorConfig.from_env().dry_run_default is False
