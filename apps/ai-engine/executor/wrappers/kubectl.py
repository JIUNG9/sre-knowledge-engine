"""kubectl wrapper.

Default verbs (read-only + restart):

* ``get``               — kubectl get <target>
* ``describe``          — kubectl describe <target>
* ``logs``              — kubectl logs <target>
* ``rollout-restart``   — kubectl rollout restart <target>
* ``scale``             — kubectl scale <target> --replicas=<N>

Permanently blocked (NOT loadable):

* ``apply``  — would let the LLM mutate arbitrary cluster state
* ``delete`` — destructive
* ``patch``  — destructive
* ``exec``   — arbitrary shell into pod
* ``cp``     — file exfiltration
* ``edit``   — interactive, can rewrite specs

The target string is tightly validated. ``scale`` requires a metadata
``replicas`` field on the action — bare ``scale`` requests are refused.
"""

from __future__ import annotations

from typing import Any

from .base import Wrapper, WrapperError, safe_token


class KubectlWrapper(Wrapper):
    """kubectl with a minimal, audited verb surface."""

    name = "kubectl"

    supported_verbs = frozenset(
        {
            "get",
            "describe",
            "logs",
            "rollout-restart",
            "scale",
        }
    )

    blocked_verbs = frozenset(
        {
            "apply",
            "delete",
            "patch",
            "exec",
            "cp",
            "edit",
            "replace",
            "drain",
            "cordon",
            "uncordon",
            "label",
            "annotate",
            "taint",
        }
    )

    timeout_seconds = 30.0

    def build_args(self, action: Any) -> list[str]:
        verb = self.extract_verb(action)
        target = safe_token(getattr(action, "target", ""), field="target")
        namespace = self._extract_namespace(action)

        argv: list[str] = []

        if verb == "get":
            argv = ["get", target, "-o", "wide"]
        elif verb == "describe":
            argv = ["describe", target]
        elif verb == "logs":
            argv = ["logs", target, "--tail=200"]
        elif verb == "rollout-restart":
            argv = ["rollout", "restart", target]
        elif verb == "scale":
            replicas = self._extract_replicas(action)
            argv = ["scale", target, f"--replicas={replicas}"]
        else:
            # Defensive: supports() should have already filtered.
            raise WrapperError(f"unhandled kubectl verb '{verb}'")

        if namespace:
            argv.extend(["-n", namespace])
        return argv

    @staticmethod
    def _extract_namespace(action: Any) -> str | None:
        meta = getattr(action, "metadata", None) or {}
        ns = meta.get("namespace") if isinstance(meta, dict) else None
        env = getattr(action, "environment", "") or ""
        candidate = ns or (env if env not in ("prod", "production") else None)
        if not candidate:
            return None
        return safe_token(str(candidate), field="namespace")

    @staticmethod
    def _extract_replicas(action: Any) -> int:
        meta = getattr(action, "metadata", None) or {}
        if isinstance(meta, dict) and "replicas" in meta:
            try:
                replicas = int(meta["replicas"])
            except (TypeError, ValueError) as exc:
                raise WrapperError(
                    "scale requires integer metadata.replicas"
                ) from exc
        else:
            raise WrapperError(
                "scale requires metadata.replicas on the ProposedAction"
            )
        if replicas < 0 or replicas > 10_000:
            raise WrapperError("replicas must be in [0, 10000]")
        return replicas
