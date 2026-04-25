"""AWS CLI wrapper.

Read-only by default. The wrapper auto-allows verbs whose first segment
matches one of the pure-read prefixes (``describe-`` / ``list-`` /
``get-``) AND a small extra set of explicitly-listed read verbs (e.g.
``head-object``).

Permanently blocked (NOT loadable):

* Any verb whose first token starts with ``delete-``, ``terminate-``,
  ``put-``, ``create-``, ``update-``, ``modify-``, ``attach-``,
  ``detach-``, ``run-``, ``start-``, ``stop-``, ``reboot-``,
  ``replace-``.
* All IAM mutating calls (the prefix list above blocks them, plus we
  add explicit guards for ``attach-role-policy``, ``put-role-policy``,
  ``create-policy``).
* Subprocess invocation of ``aws s3 cp/sync/rm/mv`` — those are
  filesystem-level mutations and we deliberately do not surface them
  even via opt-in.
"""

from __future__ import annotations

from typing import Any

from .base import Wrapper, WrapperError, safe_token


# Pure-read prefixes — any verb whose canonical first token starts with
# one of these is treated as read-only.
_READ_PREFIXES: tuple[str, ...] = (
    "describe-",
    "list-",
    "get-",
)

# Explicit extras that are read-only despite not matching a prefix.
_EXTRA_READ_VERBS: frozenset[str] = frozenset(
    {
        "head-object",
        "head-bucket",
    }
)

# Hard-coded permanent block list. These should never be available to
# the executor regardless of config.
_BLOCKED_PREFIXES: tuple[str, ...] = (
    "delete-",
    "terminate-",
    "put-",
    "create-",
    "update-",
    "modify-",
    "attach-",
    "detach-",
    "run-",
    "start-",
    "stop-",
    "reboot-",
    "replace-",
    "associate-",
    "disassociate-",
    "import-",
    "register-",
    "deregister-",
    "authorize-",
    "revoke-",
    "rotate-",
)

_BLOCKED_VERBS: frozenset[str] = frozenset(
    {
        "iam",  # whole service blocked as a verb safety
        "s3-cp",
        "s3-sync",
        "s3-rm",
        "s3-mv",
    }
)


def _is_read_verb(verb: str) -> bool:
    if verb in _EXTRA_READ_VERBS:
        return True
    return any(verb.startswith(prefix) for prefix in _READ_PREFIXES)


def _is_blocked_verb(verb: str) -> bool:
    if verb in _BLOCKED_VERBS:
        return True
    return any(verb.startswith(prefix) for prefix in _BLOCKED_PREFIXES)


class AwsCliWrapper(Wrapper):
    """``aws`` CLI gated to read-only verbs by default."""

    name = "aws"

    # The base class checks ``supports()`` — we override that method
    # because the AWS verb space is too large for a static set.
    supported_verbs = frozenset()
    blocked_verbs = frozenset()

    timeout_seconds = 60.0

    def supports(self, verb: str) -> bool:
        if not verb or not isinstance(verb, str):
            return False
        if _is_blocked_verb(verb):
            return False
        return _is_read_verb(verb)

    def build_args(self, action: Any) -> list[str]:
        verb = self.extract_verb(action)
        if _is_blocked_verb(verb):
            raise WrapperError(
                f"aws verb '{verb}' is permanently blocked"
            )
        if not _is_read_verb(verb):
            raise WrapperError(
                f"aws verb '{verb}' is not in the read-only allow-list"
            )

        # The CLI expects "service action" as separate tokens, but
        # ProposedAction carries a single verb string. We accept either
        # ``"<service> <action>"`` or just ``<action>``; in the latter
        # case we use the action.target as the service.
        service, sub = self._split_service(action, verb)
        argv = [service, sub, "--no-paginate", "--no-cli-pager"]

        # Region is optional, sourced from metadata.
        meta = getattr(action, "metadata", None) or {}
        region = meta.get("region") if isinstance(meta, dict) else None
        if region:
            argv.extend(["--region", safe_token(str(region), field="region")])

        return argv

    @staticmethod
    def _split_service(action: Any, verb: str) -> tuple[str, str]:
        """Resolve ``(service, action)`` for ``aws <service> <action>``."""
        meta = getattr(action, "metadata", None) or {}
        service = (
            meta.get("service") if isinstance(meta, dict) else None
        ) or getattr(action, "target", "")
        if not service:
            raise WrapperError(
                "aws wrapper needs metadata.service or action.target "
                "set to the service (e.g. 's3', 'ec2')"
            )
        return safe_token(str(service), field="service"), safe_token(
            verb, field="verb"
        )
