"""Terraform wrapper.

Default verb:

* ``plan``  — always allowed; runs in-place, mutates nothing.

Opt-in verb (requires ``ExecutorConfig.terraform_apply_allowed=True``):

* ``apply`` — only with ``tier=EXECUTE`` AND >=2 approvals AND explicit
              config opt-in. The wrapper itself ALSO checks the config
              flag at runtime — defence in depth.

Permanently blocked (NOT loadable):

* ``destroy`` — never. There's no scenario where the AI agent should be
                allowed to terraform-destroy a real environment.
* ``import``  — can mutate state.
* ``state``   — can mutate state.
* ``taint`` / ``untaint`` — destructive next-apply.
* ``force-unlock`` — circumvents safety locks.
"""

from __future__ import annotations

from typing import Any

from .base import Wrapper, WrapperError, safe_token


class TerraformWrapper(Wrapper):
    """Terraform with a tight, audited verb surface."""

    name = "terraform"

    supported_verbs = frozenset({"plan", "apply"})

    # ``destroy`` is the most important entry here — the executor's
    # tier-cap also enforces this, but pinning at the wrapper means a
    # stray import / refactor cannot accidentally surface it.
    blocked_verbs = frozenset(
        {
            "destroy",
            "import",
            "state",
            "taint",
            "untaint",
            "force-unlock",
            "console",
            "workspace",
        }
    )

    timeout_seconds = 600.0  # plan/apply can take a few minutes

    def __init__(
        self,
        *,
        binary: str | None = None,
        apply_allowed: bool = False,
    ) -> None:
        super().__init__(binary=binary)
        self._apply_allowed = bool(apply_allowed)

    @property
    def apply_allowed(self) -> bool:
        return self._apply_allowed

    def build_args(self, action: Any) -> list[str]:
        verb = self.extract_verb(action)
        target = getattr(action, "target", "") or ""
        chdir = self._extract_chdir(action)

        if verb == "plan":
            argv = [f"-chdir={chdir}", "plan", "-input=false", "-no-color"]
        elif verb == "apply":
            if not self._apply_allowed:
                raise WrapperError(
                    "terraform apply refused: ExecutorConfig."
                    "terraform_apply_allowed is False"
                )
            argv = [
                f"-chdir={chdir}",
                "apply",
                "-input=false",
                "-no-color",
                "-auto-approve",
            ]
        else:
            raise WrapperError(f"unhandled terraform verb '{verb}'")

        if target:
            target_token = safe_token(target, field="target")
            argv.append(f"-target={target_token}")

        return argv

    @staticmethod
    def _extract_chdir(action: Any) -> str:
        """Resolve the working directory for terraform.

        Pulled from ``metadata.chdir`` first, then falls back to the
        action ``target`` (validated as a path-like token). The CWD
        token is always validated as a safe path-style identifier so
        we never inject shell metacharacters.
        """
        meta = getattr(action, "metadata", None) or {}
        chdir = (
            meta.get("chdir")
            if isinstance(meta, dict)
            else None
        )
        if not chdir:
            chdir = "."
        return safe_token(str(chdir), field="chdir")
