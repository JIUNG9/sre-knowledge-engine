"""ControlTower — the orchestrator that ties Layer 3 together.

Flow for :meth:`ControlTower.investigate`:

1. Kill switch consulted. If active, return a ``mode="halted"``
   Investigation carrying no action and a ``halted_reason``.
2. :class:`ContextBuilder` assembles a mode-appropriate Context bundle
   pulling L1 wiki + L2 telemetry + optional L2B pattern analysis.
3. An OTel root span (``aegis.investigation``) wraps everything that
   follows so all downstream LLM and tool spans are children of it.
4. The prompt for the chosen mode is routed through
   :class:`llm_router.LLMRouter.complete`. The router decides Ollama
   vs Claude based on content sensitivity.
5. Response is parsed into structured hypotheses + evidence +
   optional action suggestion.
6. If an action was suggested, it is converted to a
   :class:`ProposedAction` via :func:`control_tower.action.propose_action`
   which runs it through Layer 4 guardrails.
7. Investigation returned with OTel trace id + usage attached.

Every dependency is optional. Missing dependencies degrade
gracefully: no wiki means no wiki snippets, no guardrails means
actions default to SUGGEST, no router means the tower refuses to run.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from .action import propose_action
from .config import ControlTowerConfig, InvestigationModeName
from .context_builder import ContextBuilder
from .investigation import (
    Alert,
    Evidence,
    Hypothesis,
    Investigation,
    InvestigationUsage,
)
from .modes import ModeSpec, all_modes, get_mode_spec

logger = logging.getLogger("aegis.control_tower")


_SYSTEM_PROMPT = (
    "You are the Aegis Site Reliability Engineering assistant. You are "
    "analyzing a single alert or SRE question. Your answer MUST be a "
    "single JSON object matching this schema:\n"
    "{\n"
    '  "summary": "<one-paragraph plain-language summary>",\n'
    '  "hypotheses": [\n'
    '    {\n'
    '      "title": "<short title>",\n'
    '      "rationale": "<why this is plausible>",\n'
    '      "confidence": <float between 0 and 1>,\n'
    '      "evidence": [\n'
    '        {"kind": "log|metric|trace|wiki|pattern|other", '
    '"summary": "...", "source_ref": null, "confidence": 0.5}\n'
    '      ]\n'
    '    }\n'
    '  ],\n'
    '  "proposed_action": null OR {\n'
    '    "name": "...", "verb": "...", "target": "...", '
    '"environment": "dev|stage|prod", "category": "deployment|iam|...", '
    '"blast_radius": 1, "reversible": true, "requested_tier": '
    '"SUGGEST|DRAFT|PROPOSE|EXECUTE", "explanation": "..."}\n'
    "}\n"
    "Do not include any prose outside the JSON object. Do not include "
    "Markdown code fences. If you are unsure, set confidence low and "
    "leave proposed_action null."
)


class ControlTower:
    """Main orchestrator. Hand it an :class:`Alert`, get an :class:`Investigation`.

    Args:
        llm_router: A :class:`llm_router.LLMRouter`. Required — the
            tower cannot reason without it.
        wiki: Duck-typed WikiQueryable (typically a
            :class:`control_tower.context_builder.WikiAdapter`).
        log_fetcher, metric_fetcher, trace_fetcher, alert_fetcher:
            Layer 2 SigNoz connectors. Optional; missing connectors
            reduce Context fidelity but never crash.
        pattern_analyzer: Optional Layer 2B analyzer used only in
            deep mode.
        guardrails: Optional :class:`guardrails.engine.GuardrailsEngine`.
            When omitted, proposed actions default to SUGGEST tier.
        killswitch: Optional object exposing ``.is_active() -> bool``.
            When None, the tower assumes the switch is not tripped.
        config: :class:`ControlTowerConfig` with budget + mode
            defaults.
    """

    def __init__(
        self,
        *,
        llm_router: Any,
        wiki: Any | None = None,
        log_fetcher: Any | None = None,
        metric_fetcher: Any | None = None,
        trace_fetcher: Any | None = None,
        alert_fetcher: Any | None = None,
        pattern_analyzer: Any | None = None,
        guardrails: Any | None = None,
        killswitch: Any | None = None,
        config: ControlTowerConfig | None = None,
    ) -> None:
        if llm_router is None:
            raise ValueError("ControlTower requires an llm_router")
        self.router = llm_router
        self.config = config or ControlTowerConfig()
        self.guardrails = guardrails
        self.killswitch = killswitch
        self.context_builder = ContextBuilder(
            wiki=wiki,
            log_fetcher=log_fetcher,
            metric_fetcher=metric_fetcher,
            trace_fetcher=trace_fetcher,
            alert_fetcher=alert_fetcher,
            pattern_analyzer=pattern_analyzer
            if self.config.enable_pattern_analyzer_in_deep
            else None,
        )
        self._investigations: dict[str, Investigation] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def investigate(
        self,
        alert: Alert | dict[str, Any] | str,
        mode: InvestigationModeName | str | None = None,
    ) -> Investigation:
        """Run an end-to-end investigation for ``alert``.

        Args:
            alert: Either an :class:`Alert`, a dict that parses as one,
                or a plain string treated as a free-form SRE question.
            mode: Optional mode override. Defaults to
                ``config.default_mode``.
        """
        normalized = _normalize_alert(alert)
        mode_name = _normalize_mode(mode or self.config.default_mode)
        spec = get_mode_spec(mode_name)
        investigation_id = f"inv-{uuid.uuid4().hex[:12]}"
        started = time.monotonic()

        # --- 1. Kill-switch gate
        if self._killswitch_active():
            halted = Investigation(
                id=investigation_id,
                mode="halted",
                alert=normalized,
                summary="Investigation halted — kill switch is active.",
                halted_reason="killswitch_active",
                usage=InvestigationUsage(
                    llm_calls=0, duration_ms=(time.monotonic() - started) * 1000
                ),
            )
            self._investigations[investigation_id] = halted
            logger.warning(
                "control_tower: kill switch active; refused investigation %s",
                investigation_id,
            )
            return halted

        # --- 2. Wrap everything in an aegis.investigation OTel span
        return await self._run_traced(investigation_id, normalized, spec, started)

    def lookup(self, trace_or_id: str) -> Investigation | None:
        """Retrieve a previously-run investigation by id or trace_id."""
        if trace_or_id in self._investigations:
            return self._investigations[trace_or_id]
        for inv in self._investigations.values():
            if inv.trace_id and inv.trace_id == trace_or_id:
                return inv
        return None

    def modes(self) -> list[ModeSpec]:
        """Return every registered mode spec (for the ``/modes`` endpoint)."""
        return all_modes()

    # ------------------------------------------------------------------ #
    # Internal pipeline
    # ------------------------------------------------------------------ #

    async def _run_traced(
        self,
        investigation_id: str,
        alert: Alert,
        spec: ModeSpec,
        started: float,
    ) -> Investigation:
        span_cm = _start_root_span(investigation_id, alert, spec)
        with span_cm as span_handle:
            inv = await self._run(investigation_id, alert, spec, started)
            # Attach the OTel trace id if available.
            trace_id = _current_trace_id()
            if trace_id:
                inv.trace_id = trace_id
            if span_handle is not None:
                span_handle.set_attribute(
                    "aegis.investigation.mode", inv.mode
                )
                span_handle.set_attribute(
                    "aegis.investigation.hypotheses",
                    len(inv.hypotheses),
                )
                span_handle.set_attribute(
                    "aegis.investigation.halted", inv.halted
                )
        self._investigations[investigation_id] = inv
        return inv

    async def _run(
        self,
        investigation_id: str,
        alert: Alert,
        spec: ModeSpec,
        started: float,
    ) -> Investigation:
        budget = self.config.context_budget_for(spec.name)
        context = await self.context_builder.build(
            alert, spec.name, budget_tokens=budget
        )

        prompt = _compose_prompt(alert, context, spec)
        call_ceiling = min(spec.max_llm_calls, self.config.call_ceiling_for(spec.name))

        summary = ""
        hypotheses: list[Hypothesis] = []
        proposed = None
        usage = InvestigationUsage(llm_calls=0)
        backend_used: str | None = None
        warnings: list[str] = []

        calls_made = 0
        parsed_payload: dict[str, Any] | None = None
        while calls_made < call_ceiling:
            calls_made += 1
            try:
                response = await _call_router(
                    self.router, prompt, spec
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "LLM router call %d/%d failed: %s",
                    calls_made,
                    call_ceiling,
                    exc,
                )
                warnings.append(f"llm call failed: {exc}")
                break

            usage.llm_calls += 1
            backend_used = backend_used or getattr(response, "backend", None)
            text = getattr(response, "text", "") or ""

            parsed_payload = _safe_parse_json(text)
            if parsed_payload is not None:
                break
            # Retry with a stricter reminder if we still have budget.
            prompt = prompt + [
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON. Return a "
                        "single JSON object matching the schema with no "
                        "surrounding text."
                    ),
                }
            ]

        if parsed_payload is None:
            warnings.append("LLM did not return parseable JSON")
            parsed_payload = {"summary": "no parseable answer", "hypotheses": []}

        summary = str(parsed_payload.get("summary", "")).strip()
        hypotheses = _parse_hypotheses(parsed_payload.get("hypotheses", []))
        suggestion = parsed_payload.get("proposed_action")

        if suggestion:
            proposed = propose_action(
                suggestion,
                guardrails=self.guardrails,
                context={"alert": alert.model_dump()},
            )
            if proposed is not None and not proposed.approved:
                warnings.append(
                    f"guardrails held action at tier {proposed.tier}"
                )

        # Soft budget warning.
        cost = usage.cost_usd
        if cost > self.config.budget_usd_per_investigation:
            warnings.append(
                f"budget exceeded: ${cost:.4f} > "
                f"${self.config.budget_usd_per_investigation:.2f}"
            )

        usage.duration_ms = (time.monotonic() - started) * 1000

        return Investigation(
            id=investigation_id,
            mode=spec.name,
            alert=alert,
            summary=summary,
            hypotheses=hypotheses,
            proposed_action=proposed,
            context=context,
            usage=usage,
            routing_backend=backend_used,
            warnings=warnings,
            metadata={
                "mode_spec": spec.to_dict(),
            },
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _killswitch_active(self) -> bool:
        ks = self.killswitch
        if ks is None:
            return False
        try:
            fn = getattr(ks, "is_active", None)
            if callable(fn):
                return bool(fn())
        except Exception as exc:  # noqa: BLE001
            logger.warning("kill switch probe failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# Prompt composition
# --------------------------------------------------------------------------- #


def _compose_prompt(
    alert: Alert, context: Any, spec: ModeSpec
) -> list[dict[str, Any]]:
    """Build the chat-style message list for an investigation."""
    alert_block = _render_alert(alert)
    context_block = context.render() if context is not None else ""

    user_content = (
        f"## Alert\n{alert_block}\n\n"
        f"## Mode\n{spec.name} (budget ~{spec.max_tokens} output tokens)\n\n"
    )
    if context_block:
        user_content += f"## Context\n{context_block}\n\n"
    user_content += (
        "Respond with the JSON object described in the system prompt."
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _render_alert(alert: Alert) -> str:
    lines = [f"severity: {alert.severity}"]
    if alert.service:
        lines.append(f"service: {alert.service}")
    lines.append(f"environment: {alert.environment}")
    if alert.title:
        lines.append(f"title: {alert.title}")
    if alert.description:
        lines.append(f"description: {alert.description}")
    if alert.question:
        lines.append(f"question: {alert.question}")
    if alert.labels:
        lines.append(f"labels: {alert.labels}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# LLM call wrapper — threads OTel + router + usage
# --------------------------------------------------------------------------- #


async def _call_router(router: Any, prompt: list[dict[str, Any]], spec: ModeSpec) -> Any:
    """Invoke ``router.complete`` inside a GenAI OTel span."""
    try:
        from telemetry import trace_llm_call
    except Exception:  # pragma: no cover
        trace_llm_call = None  # type: ignore[assignment]

    if trace_llm_call is None:
        return await router.complete(prompt)

    with trace_llm_call(
        spec.preferred_model,
        "chat",
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
    ) as handle:
        response = await router.complete(prompt)
        usage = getattr(response, "usage", {}) or {}
        handle.set_response(
            model=getattr(response, "model", None),
            input_tokens=int(usage.get("input_tokens", 0) or 0) or None,
            output_tokens=int(usage.get("output_tokens", 0) or 0) or None,
            finish_reasons=[getattr(response, "finish_reason", "stop")],
        )
        return response


# --------------------------------------------------------------------------- #
# OTel helpers
# --------------------------------------------------------------------------- #


class _NullSpan:
    """Fallback span handle when OTel isn't installed."""

    def set_attribute(self, _key: str, _value: Any) -> None:
        return None


class _NullSpanCM:
    def __enter__(self) -> _NullSpan:
        return _NullSpan()

    def __exit__(self, *args: Any) -> None:
        return None


def _start_root_span(
    investigation_id: str, alert: Alert, spec: ModeSpec
) -> Any:
    """Start the root ``aegis.investigation`` span.

    Returns a context manager. If OTel is unavailable, returns a no-op
    that yields a :class:`_NullSpan` so the orchestrator code stays
    branch-free.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind
    except Exception:  # pragma: no cover
        return _NullSpanCM()

    tracer = trace.get_tracer("aegis.control_tower", "0.3.0")
    span_cm = tracer.start_as_current_span(
        "aegis.investigation", kind=SpanKind.INTERNAL
    )

    class _Wrapper:
        def __enter__(self) -> Any:
            span = span_cm.__enter__()
            span.set_attribute("aegis.investigation.id", investigation_id)
            span.set_attribute("aegis.investigation.mode_requested", spec.name)
            if alert.service:
                span.set_attribute("aegis.investigation.service", alert.service)
            span.set_attribute(
                "aegis.investigation.severity", alert.severity
            )
            span.set_attribute(
                "gen_ai.system", "anthropic"
            )
            return span

        def __exit__(self, *args: Any) -> None:
            span_cm.__exit__(*args)

    return _Wrapper()


def _current_trace_id() -> str | None:
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if getattr(ctx, "trace_id", 0):
            return f"{ctx.trace_id:032x}"
    except Exception:  # pragma: no cover
        return None
    return None


# --------------------------------------------------------------------------- #
# Input normalization
# --------------------------------------------------------------------------- #


def _normalize_alert(alert: Alert | dict[str, Any] | str) -> Alert:
    if isinstance(alert, Alert):
        return alert
    if isinstance(alert, dict):
        return Alert.model_validate(alert)
    if isinstance(alert, str):
        return Alert(question=alert, title=alert[:80])
    raise TypeError(f"cannot coerce {type(alert).__name__} to Alert")


def _normalize_mode(mode: InvestigationModeName | str) -> InvestigationModeName:
    key = str(mode).lower().strip()
    if key not in ("eco", "standard", "deep"):
        raise ValueError(f"unknown investigation mode '{mode}'")
    return key  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Response parsing
# --------------------------------------------------------------------------- #


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _safe_parse_json(text: str) -> dict[str, Any] | None:
    """Tolerant JSON parser.

    LLMs often emit valid JSON but occasionally wrap it in Markdown
    code fences or prose. We try a strict parse first, then fall back
    to a substring extractor.
    """
    if not text:
        return None
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(stripped)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _parse_hypotheses(raw: Any) -> list[Hypothesis]:
    if not isinstance(raw, list):
        return []
    out: list[Hypothesis] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        rationale = str(item.get("rationale", "")).strip()
        confidence = _coerce_confidence(item.get("confidence"))
        ev_raw = item.get("evidence") or []
        evidence: list[Evidence] = []
        if isinstance(ev_raw, list):
            for ev in ev_raw:
                if not isinstance(ev, dict):
                    continue
                kind_val = str(ev.get("kind", "other")).lower()
                if kind_val not in (
                    "wiki",
                    "metric",
                    "log",
                    "trace",
                    "pattern",
                    "other",
                ):
                    kind_val = "other"
                evidence.append(
                    Evidence(
                        kind=kind_val,  # type: ignore[arg-type]
                        summary=str(ev.get("summary", "")).strip(),
                        source_ref=ev.get("source_ref"),
                        confidence=_coerce_confidence(ev.get("confidence")),
                    )
                )
        out.append(
            Hypothesis(
                title=title,
                rationale=rationale,
                confidence=confidence,
                evidence=evidence,
            )
        )
    return out


def _coerce_confidence(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, v))
