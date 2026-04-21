"""Approval gates — pluggable backends that collect human sign-offs.

Every tier above ``SUGGEST`` can demand approvals. The number comes from
the policy (``require_approvals``); the *how* comes from one of the gates
below:

* :class:`NoneApprovalGate` — only valid for ``SUGGEST``. Always "approves"
  with zero approvers.
* :class:`LocalCLIApprovalGate` — the default for demos. Reads y/n from
  a callable (so tests can inject fake input). Records the operator as
  "cli:<user>".
* :class:`SlackApprovalGate` — posts a message and waits for reactions to
  reach the required count. The transport is abstracted behind a
  ``SlackTransport`` protocol so tests can stub it without a real Slack.
* :class:`GithubApprovalGate` — comments on a PR; counts ``/approve``
  replies from distinct users.

Gates return an :class:`ApprovalResult`. They MUST NOT mutate any state
beyond "ask the transport" — the engine is responsible for persisting
the decision and audit trail. Gates are free to time out or return
``approved=False``; the engine handles downgrade.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class ApprovalRequest:
    """Request passed to a gate."""

    action_name: str
    tier: str
    environment: str
    required: int
    groups: tuple[str, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalResult:
    """Outcome of an approval flow."""

    approved: bool
    approvers: tuple[str, ...]
    backend: str
    reason: str | None = None


class ApprovalGate(abc.ABC):
    """Abstract base class. Concrete gates implement :meth:`request`."""

    backend: str = "abstract"

    @abc.abstractmethod
    def request(self, req: ApprovalRequest) -> ApprovalResult:
        """Collect approvals and return the outcome."""


class NoneApprovalGate(ApprovalGate):
    """No-op gate — only valid for tier ``SUGGEST``.

    If a caller wires this up for anything else, it returns
    ``approved=False`` so the engine correctly downgrades.
    """

    backend = "none"

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        if req.required <= 0:
            return ApprovalResult(
                approved=True, approvers=(), backend=self.backend,
                reason="no approvals required"
            )
        return ApprovalResult(
            approved=False,
            approvers=(),
            backend=self.backend,
            reason=f"NoneApprovalGate cannot satisfy {req.required} approvals",
        )


class LocalCLIApprovalGate(ApprovalGate):
    """Default demo gate — reads y/n from a callable (injectable for tests).

    The ``prompt`` callable receives a formatted description and must return
    ``True`` to approve, ``False`` to reject. The ``user`` callable returns
    the approving operator's identifier. Both default to terminal ``input``.
    """

    backend = "cli"

    def __init__(
        self,
        prompt: Callable[[str], bool] | None = None,
        user: Callable[[], str] | None = None,
    ) -> None:
        self._prompt = prompt or _default_prompt
        self._user = user or _default_user

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        if req.required <= 0:
            return ApprovalResult(
                approved=True, approvers=(), backend=self.backend,
                reason="no approvals required"
            )
        approvers: list[str] = []
        for i in range(req.required):
            msg = (
                f"[{i + 1}/{req.required}] Approve action '{req.action_name}' "
                f"in {req.environment} at tier {req.tier}?"
            )
            if not self._prompt(msg):
                return ApprovalResult(
                    approved=False,
                    approvers=tuple(approvers),
                    backend=self.backend,
                    reason="operator declined",
                )
            approvers.append(f"cli:{self._user()}")
        return ApprovalResult(
            approved=True, approvers=tuple(approvers), backend=self.backend
        )


class SlackTransport(Protocol):
    """Minimal Slack-shaped transport."""

    def post_message(self, text: str, groups: tuple[str, ...]) -> str: ...
    def collect_reactions(self, message_id: str, required: int) -> list[str]: ...


class SlackApprovalGate(ApprovalGate):
    """Post message + react-to-approve approval flow."""

    backend = "slack"

    def __init__(self, transport: SlackTransport) -> None:
        self._transport = transport

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        if req.required <= 0:
            return ApprovalResult(
                approved=True, approvers=(), backend=self.backend,
                reason="no approvals required"
            )
        text = (
            f":rotating_light: Aegis requests approval for *{req.action_name}* "
            f"in `{req.environment}` at tier `{req.tier}` "
            f"(need {req.required} approvers from {', '.join(req.groups) or 'any'})."
        )
        msg_id = self._transport.post_message(text, req.groups)
        reactors = self._transport.collect_reactions(msg_id, req.required)
        if len(reactors) >= req.required:
            return ApprovalResult(
                approved=True,
                approvers=tuple(f"slack:{u}" for u in reactors[: req.required]),
                backend=self.backend,
            )
        return ApprovalResult(
            approved=False,
            approvers=tuple(f"slack:{u}" for u in reactors),
            backend=self.backend,
            reason=(
                f"got {len(reactors)} approvals, needed {req.required}"
            ),
        )


class GithubTransport(Protocol):
    """Minimal GitHub-shaped transport."""

    def comment(self, pr: str, body: str) -> str: ...
    def collect_approvals(self, pr: str, required: int) -> list[str]: ...


class GithubApprovalGate(ApprovalGate):
    """Comment-on-PR approval flow — counts distinct ``/approve`` replies."""

    backend = "github"

    def __init__(self, transport: GithubTransport, pr_ref_key: str = "pr") -> None:
        self._transport = transport
        self._pr_ref_key = pr_ref_key

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        if req.required <= 0:
            return ApprovalResult(
                approved=True, approvers=(), backend=self.backend,
                reason="no approvals required"
            )
        pr = req.context.get(self._pr_ref_key)
        if not pr:
            return ApprovalResult(
                approved=False,
                approvers=(),
                backend=self.backend,
                reason=f"missing '{self._pr_ref_key}' in request context",
            )
        body = (
            f"Aegis requests approval for `{req.action_name}` in "
            f"`{req.environment}` (tier={req.tier}). "
            f"Reply `/approve` to sign off (need {req.required})."
        )
        self._transport.comment(str(pr), body)
        approvers = self._transport.collect_approvals(str(pr), req.required)
        if len(approvers) >= req.required:
            return ApprovalResult(
                approved=True,
                approvers=tuple(f"gh:{u}" for u in approvers[: req.required]),
                backend=self.backend,
            )
        return ApprovalResult(
            approved=False,
            approvers=tuple(f"gh:{u}" for u in approvers),
            backend=self.backend,
            reason=(
                f"got {len(approvers)} /approve comments, needed {req.required}"
            ),
        )


# --------------------------------------------------------------------------
# Defaults for LocalCLIApprovalGate — separated so tests can inject cleanly.
# --------------------------------------------------------------------------

def _default_prompt(msg: str) -> bool:  # pragma: no cover - trivial I/O
    ans = input(f"{msg} [y/N] ").strip().lower()
    return ans in {"y", "yes"}


def _default_user() -> str:  # pragma: no cover - trivial I/O
    import getpass

    try:
        return getpass.getuser()
    except Exception:
        return "unknown"
