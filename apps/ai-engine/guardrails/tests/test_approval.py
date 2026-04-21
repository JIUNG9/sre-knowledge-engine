"""Approval gate tests."""

from __future__ import annotations

from guardrails.approval import (
    ApprovalRequest,
    GithubApprovalGate,
    LocalCLIApprovalGate,
    NoneApprovalGate,
    SlackApprovalGate,
)


def _req(**overrides):
    base = dict(
        action_name="restart pod",
        tier="EXECUTE",
        environment="prod",
        required=2,
        groups=("oncall",),
        context={},
    )
    base.update(overrides)
    return ApprovalRequest(**base)


def test_none_gate_approves_only_when_zero_required():
    gate = NoneApprovalGate()
    yes = gate.request(_req(required=0))
    assert yes.approved is True
    no = gate.request(_req(required=1))
    assert no.approved is False


def test_cli_gate_collects_required_approvals():
    calls: list[str] = []

    def prompt(msg: str) -> bool:
        calls.append(msg)
        return True

    gate = LocalCLIApprovalGate(prompt=prompt, user=lambda: "june")
    res = gate.request(_req(required=2))
    assert res.approved is True
    assert len(res.approvers) == 2
    assert all(a.startswith("cli:june") for a in res.approvers)
    assert len(calls) == 2


def test_cli_gate_fails_on_first_reject():
    def prompt(msg: str) -> bool:
        return False

    gate = LocalCLIApprovalGate(prompt=prompt, user=lambda: "u")
    res = gate.request(_req(required=2))
    assert res.approved is False
    assert res.approvers == ()
    assert "declined" in (res.reason or "")


class _FakeSlack:
    def __init__(self, reactors: list[str]) -> None:
        self._reactors = reactors
        self.posted: list[str] = []

    def post_message(self, text: str, groups) -> str:
        self.posted.append(text)
        return "msg-1"

    def collect_reactions(self, message_id: str, required: int) -> list[str]:
        return self._reactors


def test_slack_gate_approves_with_enough_reactors():
    transport = _FakeSlack(["alice", "bob", "carol"])
    gate = SlackApprovalGate(transport)
    res = gate.request(_req(required=2))
    assert res.approved is True
    assert res.approvers == ("slack:alice", "slack:bob")
    assert transport.posted and "restart pod" in transport.posted[0]


def test_slack_gate_fails_when_underapproved():
    transport = _FakeSlack(["alice"])
    gate = SlackApprovalGate(transport)
    res = gate.request(_req(required=2))
    assert res.approved is False
    assert res.approvers == ("slack:alice",)
    assert "needed 2" in (res.reason or "")


class _FakeGithub:
    def __init__(self, approvers: list[str]) -> None:
        self._approvers = approvers
        self.comments: list[str] = []

    def comment(self, pr: str, body: str) -> str:
        self.comments.append(body)
        return "comment-1"

    def collect_approvals(self, pr: str, required: int) -> list[str]:
        return self._approvers


def test_github_gate_requires_pr_context():
    gate = GithubApprovalGate(_FakeGithub([]))
    res = gate.request(_req(required=1, context={}))
    assert res.approved is False
    assert "missing" in (res.reason or "")


def test_github_gate_counts_distinct_approvers():
    transport = _FakeGithub(["june", "alex"])
    gate = GithubApprovalGate(transport)
    res = gate.request(_req(required=2, context={"pr": "aegis-oss#42"}))
    assert res.approved is True
    assert res.approvers == ("gh:june", "gh:alex")
    assert transport.comments and "aegis-oss#42" not in transport.comments[0]
