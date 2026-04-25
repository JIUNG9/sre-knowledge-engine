"""Environment-driven configuration for the Aegis executor (Layer 4 / Phase 2.5).

The executor is the keystone of Aegis self-healing — it actually runs the
real action that Layer 4 has authorised. To stay safe by default, every
knob is **off** unless the operator opts in:

* ``AEGIS_EXECUTOR_ENABLED`` — master switch. When False, the FastAPI
  router still mounts (so OpenAPI is complete) but every request returns
  503. Tests / CI / cold starts NEVER execute.
* ``AEGIS_EXECUTOR_DRY_RUN`` — when 1 (default), wrappers run in no-op
  mode and report what they *would* have done. Real side effects only
  happen when this is explicitly set to 0.
* ``AEGIS_EXECUTOR_TF_APPLY_ALLOWED`` — explicit consent for Terraform
  ``apply``. Required AND ``tier=EXECUTE`` AND >=2 approvals.
* ``AEGIS_EXECUTOR_AUDIT_LOG`` — JSONL audit path. Defaults to
  ``./aegis-executor-audit.jsonl`` in the working directory.

The dictionary of allowed verbs is the second-line defence — the wrappers
already block everything dangerous by hard-coding their verb list, but
:class:`ExecutorConfig` lets the operator further tighten (or, with care,
extend) the surface per deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return raw if raw not in (None, "") else default


# Conservative defaults. The wrappers themselves enforce a stricter floor —
# this dict can only *narrow* the verb surface, never widen it. Adding a new
# wrapper or verb requires a code change AND a release note.
DEFAULT_ALLOWED_VERBS: dict[str, list[str]] = {
    "kubectl": ["scale", "rollout-restart", "get", "describe", "logs"],
    "terraform": ["plan"],  # apply is gated on tf_apply_allowed
    "aws": [],  # all default-blocked; opt-in per deployment
}


@dataclass
class ExecutorConfig:
    """Top-level executor configuration.

    Attributes:
        enabled: Master on/off. Defaults to ``False`` so a fresh deploy
            cannot run anything until the operator says so.
        dry_run_default: When True (the default), wrappers run in no-op
            mode unless the request explicitly disables it. Production
            operators flip this to False once they've validated the
            surface.
        allowed_verbs: ``{wrapper_name: [verb, ...]}`` allow-list.
            Wrappers refuse any verb not in this map — even if the
            wrapper class would otherwise support it.
        terraform_apply_allowed: Hard gate on ``terraform apply``.
            Even with ``EXECUTE`` + 2 approvals, the executor refuses
            ``apply`` unless this is explicitly True.
        audit_log_path: JSONL audit path. Append-only.
        require_two_approvals_for_execute: Floor on ``EXECUTE``-tier
            actions. Defaults to True; the executor refuses execution
            with fewer than two approvals when ``True``.
    """

    enabled: bool = False
    dry_run_default: bool = True
    allowed_verbs: dict[str, list[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_ALLOWED_VERBS.items()}
    )
    terraform_apply_allowed: bool = False
    audit_log_path: str = "./aegis-executor-audit.jsonl"
    require_two_approvals_for_execute: bool = True

    @classmethod
    def from_env(cls) -> "ExecutorConfig":
        """Build an :class:`ExecutorConfig` from ``AEGIS_EXECUTOR_*`` env."""
        return cls(
            enabled=_env_bool("AEGIS_EXECUTOR_ENABLED", False),
            dry_run_default=_env_bool("AEGIS_EXECUTOR_DRY_RUN", True),
            terraform_apply_allowed=_env_bool(
                "AEGIS_EXECUTOR_TF_APPLY_ALLOWED", False
            ),
            audit_log_path=_env_str(
                "AEGIS_EXECUTOR_AUDIT_LOG", "./aegis-executor-audit.jsonl"
            ),
            require_two_approvals_for_execute=_env_bool(
                "AEGIS_EXECUTOR_REQUIRE_TWO_APPROVALS", True
            ),
        )

    def verb_allowed(self, wrapper: str, verb: str) -> bool:
        """Return ``True`` when ``verb`` is in the wrapper's allow-list."""
        return verb in self.allowed_verbs.get(wrapper, [])
