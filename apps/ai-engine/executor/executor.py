"""Layer 4 executor — the keystone of Aegis self-healing.

This is the dispatcher that turns Aegis from "advisory AI SRE that
proposes" into "operator AI SRE that runs". The executor is the LAST
mile — every gate (risk, policy, approval, kill switch) has already had
its say before this code runs. Even so, the executor re-checks the
critical gates because the cost of a bad call here is real-world
infrastructure damage.

The chain of gates, in strict order:

1. Config gate — ``ExecutorConfig.enabled``. If False, refuse.
2. Tier gate  — ``decision.tier == EXECUTE``. PROPOSE/DRAFT/SUGGEST
                land back at the operator UI; the executor refuses.
3. Approval gate — ``decision.approval.approved`` is True AND the
                approver count >= ``policy.required_approvals``.
                For ``EXECUTE``, also >= 2 unless explicitly disabled.
4. Verb gate  — wrapper.supports(verb) AND verb in
                ``ExecutorConfig.allowed_verbs[wrapper]``.
5. Kill-switch gate — checked LAST, immediately before dispatch.
                This is the operator's emergency stop after every
                automated gate has already said "yes".
6. Audit write — refused on failure (never run an unaudited command).
7. Wrapper.execute — typed argv, captured stdout/stderr, exit code.

Every gate emits one OTel span attribute on the parent span so a
single trace shows the full decision path.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from .audit import AuditLogger, ExecutorAuditRecord
from .config import ExecutorConfig
from .result import ExecutionResult
from .wrappers import AwsCliWrapper, KubectlWrapper, TerraformWrapper, Wrapper

if TYPE_CHECKING:
    pass

logger = logging.getLogger("aegis.executor")


SPAN_NAME = "aegis.executor.dispatch"

ATTR_OUTCOME = "aegis.executor.outcome"
ATTR_VERB = "aegis.executor.verb"
ATTR_TARGET = "aegis.executor.target"
ATTR_TIER = "aegis.executor.tier"
ATTR_APPROVALS = "aegis.executor.approvals"
ATTR_DRY_RUN = "aegis.executor.dry_run"
ATTR_REASON = "aegis.executor.refused_reason"
ATTR_AUDIT_ID = "aegis.executor.audit_id"
ATTR_INV_ID = "aegis.executor.investigation_id"
ATTR_GATE = "aegis.executor.gate"


class Executor:
    """Dispatches a :class:`ProposedAction` after final gate checks.

    The executor is constructed once per process. It carries the
    config, the audit logger, and the dictionary of wrappers. Tests
    typically inject a ``killswitch_check`` callable; production wires
    :class:`killswitch.KillSwitch` directly.
    """

    def __init__(
        self,
        *,
        config: ExecutorConfig,
        audit: AuditLogger | None = None,
        wrappers: dict[str, Wrapper] | None = None,
        killswitch_check: Any | None = None,
    ) -> None:
        self.config = config
        self.audit = audit or AuditLogger(config.audit_log_path)
        self.wrappers: dict[str, Wrapper] = wrappers or self._default_wrappers(config)
        self._killswitch_check = killswitch_check or _default_killswitch_check

    @staticmethod
    def _default_wrappers(config: ExecutorConfig) -> dict[str, Wrapper]:
        return {
            "kubectl": KubectlWrapper(),
            "terraform": TerraformWrapper(
                apply_allowed=config.terraform_apply_allowed
            ),
            "aws": AwsCliWrapper(),
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def execute(
        self,
        action: Any,
        decision: Any,
        *,
        investigation_id: str | None = None,
        dry_run: bool | None = None,
    ) -> ExecutionResult:
        """Run ``action`` if every gate clears, else return a refusal.

        Args:
            action: A :class:`ProposedAction` (or anything with the same
                attribute shape: ``name``, ``verb``, ``target``,
                ``environment``, ``tier``, ``approver_groups``).
            decision: A guardrails ``GuardrailDecision`` (or anything
                with ``tier``, ``approved``, ``approval``, ``policy``).
            investigation_id: Optional Layer 3 correlation key.
            dry_run: Override the per-config dry-run default. ``None``
                = use ``config.dry_run_default``.

        Returns:
            An :class:`ExecutionResult` — never raises for gate refusals.
        """
        with _span(SPAN_NAME) as span:
            self._set_attr(span, ATTR_INV_ID, investigation_id or "")
            self._set_attr(span, ATTR_VERB, getattr(action, "verb", ""))
            self._set_attr(span, ATTR_TARGET, getattr(action, "target", ""))

            effective_dry_run = (
                self.config.dry_run_default if dry_run is None else bool(dry_run)
            )
            self._set_attr(span, ATTR_DRY_RUN, effective_dry_run)

            # ---- Gate 1: config ----
            if not self.config.enabled:
                self._set_attr(span, ATTR_GATE, "disabled")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="executor_disabled",
                    span=span,
                    dry_run=effective_dry_run,
                )

            # ---- Gate 2: tier ----
            tier_name = self._tier_name(decision)
            self._set_attr(span, ATTR_TIER, tier_name)
            if tier_name != "EXECUTE":
                self._set_attr(span, ATTR_GATE, "tier")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="not_approved_for_execution",
                    span=span,
                    dry_run=effective_dry_run,
                )

            # ---- Gate 3: approvals ----
            approvers = self._approvers(decision)
            self._set_attr(span, ATTR_APPROVALS, len(approvers))
            required = self._required_approvals(decision)
            if not self._is_approved(decision):
                self._set_attr(span, ATTR_GATE, "approval")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="approval_gate_not_satisfied",
                    span=span,
                    dry_run=effective_dry_run,
                )
            if len(approvers) < required:
                self._set_attr(span, ATTR_GATE, "approval")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="insufficient_approvals",
                    span=span,
                    dry_run=effective_dry_run,
                )
            if (
                self.config.require_two_approvals_for_execute
                and len(approvers) < 2
            ):
                self._set_attr(span, ATTR_GATE, "approval")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="execute_requires_two_approvals",
                    span=span,
                    dry_run=effective_dry_run,
                )

            # ---- Gate 4: verb / wrapper ----
            wrapper, wrapper_name = self._resolve_wrapper(action)
            if wrapper is None:
                self._set_attr(span, ATTR_GATE, "wrapper")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason="no_wrapper_for_verb",
                    span=span,
                    dry_run=effective_dry_run,
                )
            verb = self._wrapper_verb(action)
            if verb in wrapper.blocked_verbs:
                self._set_attr(span, ATTR_GATE, "blocked_verb")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason=f"verb_permanently_blocked:{verb}",
                    span=span,
                    dry_run=effective_dry_run,
                )
            if not wrapper.supports(verb):
                self._set_attr(span, ATTR_GATE, "wrapper_verb")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason=f"verb_not_supported:{verb}",
                    span=span,
                    dry_run=effective_dry_run,
                )
            if not self.config.verb_allowed(wrapper_name, verb):
                self._set_attr(span, ATTR_GATE, "config_verb")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason=f"verb_not_in_allow_list:{wrapper_name}:{verb}",
                    span=span,
                    dry_run=effective_dry_run,
                )

            # ---- Gate 5: kill switch (LAST DEFENSE) ----
            active, ks_reason = self._safe_killswitch_check()
            if active:
                self._set_attr(span, ATTR_GATE, "killswitch")
                return self._refuse(
                    action=action,
                    decision=decision,
                    investigation_id=investigation_id,
                    reason=f"killswitch_active:{ks_reason or 'no_reason'}",
                    span=span,
                    dry_run=effective_dry_run,
                )

            # ---- Dispatch ----
            self._set_attr(span, ATTR_GATE, "dispatch")
            return self._dispatch(
                wrapper=wrapper,
                action=action,
                decision=decision,
                investigation_id=investigation_id,
                approvers=approvers,
                tier_name=tier_name,
                dry_run=effective_dry_run,
                span=span,
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _dispatch(
        self,
        *,
        wrapper: Wrapper,
        action: Any,
        decision: Any,
        investigation_id: str | None,
        approvers: tuple[str, ...],
        tier_name: str,
        dry_run: bool,
        span: Any,
    ) -> ExecutionResult:
        verb = self._wrapper_verb(action)
        target = getattr(action, "target", "")
        environment = getattr(action, "environment", "prod") or "prod"
        action_name = getattr(action, "name", verb or "anonymous")

        started = time.monotonic()
        try:
            result = wrapper.execute(
                action,
                dry_run=dry_run,
                investigation_id=investigation_id,
            )
        except Exception as exc:  # noqa: BLE001 — wrapper bugs must not crash executor
            logger.exception("executor: wrapper raised")
            duration = (time.monotonic() - started) * 1000.0
            result = ExecutionResult(
                outcome="failed",
                verb=verb,
                target=target,
                exit_code=None,
                stdout="",
                stderr=f"wrapper exception: {type(exc).__name__}: {exc}",
                duration_ms=duration,
                dry_run=dry_run,
                investigation_id=investigation_id,
            )

        # ---- Audit (mandatory) ----
        try:
            record = self.audit.record(
                investigation_id=investigation_id,
                action=action_name,
                verb=verb,
                target=target,
                environment=environment,
                tier=tier_name,
                approvals=approvers,
                outcome=result.outcome,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=result.duration_ms,
                dry_run=dry_run,
                refused_reason=result.refused_reason,
                metadata={
                    "wrapper": wrapper.name,
                    "category": getattr(action, "category", ""),
                    "blast_radius": getattr(action, "blast_radius", 0),
                    "reversible": bool(getattr(action, "reversible", True)),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("executor: audit write failed: %s", exc)
            self._set_attr(span, ATTR_OUTCOME, "refused")
            self._set_attr(span, ATTR_REASON, "audit_write_failed")
            return ExecutionResult.refused(
                reason="audit_write_failed",
                verb=verb,
                target=target,
                investigation_id=investigation_id,
            )

        result.audit_id = record.audit_id
        result.investigation_id = investigation_id
        self._set_attr(span, ATTR_OUTCOME, result.outcome)
        self._set_attr(span, ATTR_AUDIT_ID, record.audit_id)
        return result

    def _refuse(
        self,
        *,
        action: Any,
        decision: Any,
        investigation_id: str | None,
        reason: str,
        span: Any,
        dry_run: bool,
    ) -> ExecutionResult:
        verb = getattr(action, "verb", "")
        target = getattr(action, "target", "")
        env = getattr(action, "environment", "prod") or "prod"
        tier_name = self._tier_name(decision)
        approvers = self._approvers(decision)
        action_name = getattr(action, "name", verb or "anonymous")

        try:
            record: ExecutorAuditRecord | None = self.audit.record(
                investigation_id=investigation_id,
                action=action_name,
                verb=verb,
                target=target,
                environment=env,
                tier=tier_name,
                approvals=approvers,
                outcome="refused",
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=0.0,
                dry_run=dry_run,
                refused_reason=reason,
                metadata={"category": getattr(action, "category", "")},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("executor: audit write on refusal failed: %s", exc)
            record = None

        self._set_attr(span, ATTR_OUTCOME, "refused")
        self._set_attr(span, ATTR_REASON, reason)
        if record is not None:
            self._set_attr(span, ATTR_AUDIT_ID, record.audit_id)

        return ExecutionResult.refused(
            reason=reason,
            verb=verb,
            target=target,
            investigation_id=investigation_id,
            audit_id=record.audit_id if record is not None else None,
        )

    def _resolve_wrapper(self, action: Any) -> tuple[Wrapper | None, str]:
        """Pick a wrapper based on the verb prefix or category.

        ProposedAction.verb may be either ``"kubectl rollout-restart"`` or
        just ``"rollout-restart"``. We accept both forms by:

        1. Checking if the first whitespace-separated token is a wrapper
           name (kubectl/terraform/aws). If so, that's the wrapper and
           the remainder is the actual verb.
        2. Otherwise, falling back to the action's ``category`` field.
        3. Otherwise, scanning every wrapper to see which one supports
           the bare verb.
        """
        raw = (getattr(action, "verb", "") or "").strip()
        if " " in raw:
            head, _, _ = raw.partition(" ")
            if head in self.wrappers:
                return self.wrappers[head], head

        category = (getattr(action, "category", "") or "").lower()
        if category in self.wrappers:
            return self.wrappers[category], category

        verb = self._wrapper_verb(action)
        for name, wrapper in self.wrappers.items():
            if verb in wrapper.blocked_verbs:
                return wrapper, name
            if wrapper.supports(verb):
                return wrapper, name
        return None, ""

    @staticmethod
    def _wrapper_verb(action: Any) -> str:
        """Extract the wrapper-relative verb from action.verb.

        Handles ``"kubectl rollout-restart"`` -> ``"rollout-restart"``.
        """
        raw = (getattr(action, "verb", "") or "").strip()
        if " " in raw:
            head, _, tail = raw.partition(" ")
            if head in ("kubectl", "terraform", "aws"):
                return tail.strip()
        return raw

    @staticmethod
    def _tier_name(decision: Any) -> str:
        if decision is None:
            return "SUGGEST"
        tier = getattr(decision, "tier", None)
        if tier is None:
            return "SUGGEST"
        name = getattr(tier, "name", None)
        return name if isinstance(name, str) else str(tier)

    @staticmethod
    def _approvers(decision: Any) -> tuple[str, ...]:
        if decision is None:
            return ()
        approval = getattr(decision, "approval", None)
        approvers = getattr(approval, "approvers", None) if approval else None
        if approvers is None:
            return ()
        return tuple(approvers)

    @staticmethod
    def _required_approvals(decision: Any) -> int:
        if decision is None:
            return 0
        policy = getattr(decision, "policy", None)
        return int(getattr(policy, "required_approvals", 0) or 0)

    @staticmethod
    def _is_approved(decision: Any) -> bool:
        if decision is None:
            return False
        approval = getattr(decision, "approval", None)
        if approval is None:
            # Some decisions skip the approval object when no approvals
            # were required. Honour decision.approved in that case.
            return bool(getattr(decision, "approved", False))
        return bool(getattr(approval, "approved", False))

    def _safe_killswitch_check(self) -> tuple[bool, str | None]:
        try:
            active, reason = self._killswitch_check()
            return bool(active), reason
        except Exception as exc:  # noqa: BLE001
            logger.warning("executor: kill-switch probe raised %r", exc)
            # Fail-closed for the executor: if we can't read the switch,
            # we DO NOT execute. The advisory paths fail-open; the
            # operator path fails-closed.
            return True, f"killswitch_probe_failed:{exc}"

    @staticmethod
    def _set_attr(span: Any, key: str, value: Any) -> None:
        if span is None:
            return
        setter = getattr(span, "set_attribute", None)
        if not callable(setter):
            return
        try:
            setter(key, value if isinstance(value, (str, int, float, bool)) else str(value))
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------- #
# Internal helpers
# ---------------------------------------------------------------------- #


def _default_killswitch_check() -> tuple[bool, str | None]:
    """Probe Layer 0.3 KillSwitch lazily; fail-closed on import errors.

    Unlike the guardrails engine (which fails *open* so missing infra
    doesn't block demos), the executor fails *closed* — if we cannot
    confirm the kill switch is clear, we refuse execution.
    """
    try:
        from killswitch import KillSwitch  # type: ignore[import-not-found]

        status = KillSwitch().status()
        return bool(status.active), getattr(status, "reason", None)
    except Exception as exc:  # noqa: BLE001
        return True, f"killswitch_unavailable:{exc}"


class _NoOpSpan:
    """Span fallback when OTel isn't installed. Used by ``_span``."""

    def set_attribute(self, key: str, value: Any) -> None:
        return None


class _NoOpSpanContext:
    def __enter__(self) -> _NoOpSpan:
        return _NoOpSpan()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


def _span(name: str) -> Any:
    """Open an OTel span if available, else a no-op."""
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - OTel always installed in this repo
        return _NoOpSpanContext()
    tracer = trace.get_tracer("aegis.executor", "0.5.0")
    return tracer.start_as_current_span(name)
