"""Abstract base for typed command wrappers.

The contract: every wrapper translates a :class:`ProposedAction` into a
fixed argv list (no shell, no string interpolation of user-controlled
values into anything but `--flag value` slots) and runs it via
``subprocess.run`` with stdin disabled and a strict timeout.

Wrappers MUST:

* Hard-code their list of supported verbs at class level.
* Reject any verb not in that list — even if the operator's
  :class:`ExecutorConfig.allowed_verbs` accidentally lists it.
* Sanitise every typed input (target, namespace, etc.) — only the
  small character set ``[a-zA-Z0-9_./:=-]`` is allowed.
* Honour ``dry_run=True`` by NOT shelling out and instead returning
  the planned argv as ``stdout``.

Wrappers MUST NOT:

* Accept `--exec`, `--shell`, `bash -c`, or any verb that lets the LLM
  inject arbitrary commands.
* Pipe / redirect / chain commands.
* Read or write files outside what the CLI itself does.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any

from ..result import ExecutionResult


class WrapperError(Exception):
    """Raised when wrapper-level validation refuses to build a command."""


# Conservative character class for any typed input that becomes part of
# argv. We deliberately exclude shell metacharacters (``$ ` ; & | > <``).
_SAFE_RE = re.compile(r"^[A-Za-z0-9_./:=\-@]+$")


def safe_token(value: str, *, field: str = "token") -> str:
    """Validate that ``value`` is a single shell-safe token.

    Empty strings and tokens with metacharacters are rejected loudly so
    the executor refuses early.
    """
    if not isinstance(value, str) or not value:
        raise WrapperError(f"{field} must be a non-empty string")
    if not _SAFE_RE.match(value):
        raise WrapperError(
            f"{field} contains disallowed characters (only "
            "[A-Za-z0-9_./:=@-] permitted)"
        )
    return value


class Wrapper(ABC):
    """Abstract base for typed CLI wrappers.

    Subclasses set :attr:`name` (used as a key into
    ``ExecutorConfig.allowed_verbs``) and :attr:`supported_verbs`. The
    base class handles the subprocess invocation and dry-run plumbing.
    """

    #: Wrapper key in :class:`ExecutorConfig.allowed_verbs`.
    name: str = ""

    #: Hard-coded verb whitelist enforced at the wrapper level.
    #: Even if config widens this, the wrapper still refuses.
    supported_verbs: frozenset[str] = frozenset()

    #: Forbidden verbs that must not even be loadable as a verb. The
    #: executor double-checks this list before dispatch.
    blocked_verbs: frozenset[str] = frozenset()

    #: Subprocess timeout in seconds. Wrappers may override per-CLI.
    timeout_seconds: float = 60.0

    def __init__(self, *, binary: str | None = None) -> None:
        self._binary_override = binary

    @property
    def binary(self) -> str:
        """Return the CLI binary path, defaulting to PATH lookup."""
        if self._binary_override:
            return self._binary_override
        return self.name  # e.g. "kubectl"

    def supports(self, verb: str) -> bool:
        """Return True when ``verb`` is in the hard-coded allow-list."""
        if verb in self.blocked_verbs:
            return False
        return verb in self.supported_verbs

    @abstractmethod
    def build_args(self, action: Any) -> list[str]:
        """Return the argv list for ``action`` (excluding the binary).

        Subclasses raise :class:`WrapperError` for any validation
        failure — the executor catches that and records a refusal.

        Subclasses should call :meth:`extract_verb` rather than reading
        ``action.verb`` directly so the ``"<wrapper> <verb>"`` prefix
        form is handled uniformly.
        """
        raise NotImplementedError

    def extract_verb(self, action: Any) -> str:
        """Return the wrapper-relative verb from ``action.verb``.

        Accepts both the prefixed form (``"kubectl rollout-restart"``)
        and the bare form (``"rollout-restart"``). Returns the bare verb.
        """
        raw = (getattr(action, "verb", "") or "").strip()
        if " " in raw:
            head, _, tail = raw.partition(" ")
            if head == self.name and tail:
                return tail.strip()
        return raw

    def execute(
        self,
        action: Any,
        *,
        dry_run: bool,
        investigation_id: str | None = None,
    ) -> ExecutionResult:
        """Build args, then either dry-run or shell out.

        Returns an :class:`ExecutionResult` regardless — the executor
        never raises on subprocess failure; instead it returns
        ``outcome="failed"`` with the error captured in ``stderr``.
        """
        # ``action.verb`` may carry a ``"<wrapper> <verb>"`` prefix
        # (e.g. ``"kubectl rollout-restart"``). ``extract_verb`` returns
        # the wrapper-relative verb that supports()/blocked_verbs check.
        verb = self.extract_verb(action)
        target = getattr(action, "target", "")

        # Wrapper-level verb gate. The executor also gates, but the
        # wrapper enforces its own floor so this class is safe to use
        # standalone in unit tests.
        if verb in self.blocked_verbs:
            return ExecutionResult.refused(
                reason=f"verb '{verb}' is permanently blocked by {self.name}",
                verb=verb,
                target=target,
                investigation_id=investigation_id,
            )
        if not self.supports(verb):
            return ExecutionResult.refused(
                reason=f"verb '{verb}' is not supported by {self.name}",
                verb=verb,
                target=target,
                investigation_id=investigation_id,
            )

        try:
            args = self.build_args(action)
        except WrapperError as exc:
            return ExecutionResult.refused(
                reason=f"invalid argument for {self.name} {verb}: {exc}",
                verb=verb,
                target=target,
                investigation_id=investigation_id,
            )

        argv = [self.binary, *args]

        if dry_run:
            return ExecutionResult(
                outcome="executed",
                verb=verb,
                target=target,
                exit_code=0,
                stdout=" ".join(argv),
                stderr="",
                duration_ms=0.0,
                dry_run=True,
                investigation_id=investigation_id,
                metadata={"mode": "dry-run", "binary": self.binary},
            )

        if shutil.which(self.binary) is None:
            return ExecutionResult(
                outcome="failed",
                verb=verb,
                target=target,
                exit_code=None,
                stdout="",
                stderr=f"{self.binary}: not found on PATH",
                duration_ms=0.0,
                dry_run=False,
                investigation_id=investigation_id,
            )

        started = time.monotonic()
        try:
            completed = subprocess.run(  # noqa: S603 — argv is fully typed
                argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            duration = (time.monotonic() - started) * 1000.0
            return ExecutionResult(
                outcome="failed",
                verb=verb,
                target=target,
                exit_code=None,
                stdout="",
                stderr=f"timeout after {self.timeout_seconds}s: {exc}",
                duration_ms=duration,
                dry_run=False,
                investigation_id=investigation_id,
            )
        except (OSError, ValueError) as exc:
            duration = (time.monotonic() - started) * 1000.0
            return ExecutionResult(
                outcome="failed",
                verb=verb,
                target=target,
                exit_code=None,
                stdout="",
                stderr=f"{type(exc).__name__}: {exc}",
                duration_ms=duration,
                dry_run=False,
                investigation_id=investigation_id,
            )

        duration = (time.monotonic() - started) * 1000.0
        outcome = "executed" if completed.returncode == 0 else "failed"
        return ExecutionResult(
            outcome=outcome,
            verb=verb,
            target=target,
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            duration_ms=duration,
            dry_run=False,
            investigation_id=investigation_id,
        )
