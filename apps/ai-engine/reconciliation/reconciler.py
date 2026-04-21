"""Cross-source document reconciler.

The :class:`Reconciler` is the orchestration layer on top of the pluggable
sources. Its primary entry point — :meth:`Reconciler.compare` — does four
things for a topic:

1. Asks every registered source for docs matching the topic.
2. Builds a ranked :class:`DocRef` list (freshness-weighted).
3. Runs a cheap string-level diff between every pair of docs to find
   obvious disagreements.
4. Sends the top pair(s) to the LLM router for a semantic contradiction
   pass. Router failure (local LLM unavailable) is handled gracefully:
   the string-level findings are still returned, plus a note explaining
   the LLM step was skipped.

The reconciler is intentionally conservative about network and LLM
cost — a single ``compare`` call will never send more than ``llm_pair_limit``
pairs through the router.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .models import (
    Contradiction,
    Doc,
    DocRef,
    ReconciliationReport,
)
from .sources import DocSource

logger = logging.getLogger("aegis.reconciliation.reconciler")


# Matches either a semver-style number (1.2 / 1.2.3 / 1.2.3.4) OR a bare
# integer immediately preceded by a word like "version", "pg", "postgres",
# "v", "release", or "=" — so "postgres 16" registers but a timestamp
# or port number doesn't.
_VERSION_RE = re.compile(
    r"(?:\b(?:version|release|v|pg|postgres|postgresql|redis|python|kubernetes|k8s|kafka|node|java|go|terraform|helm|istio|mongo|mysql|pool(?:\s*size)?)\s*[:=]?\s*)(\d+(?:\.\d+){0,3})"
    r"|\b(\d+\.\d+(?:\.\d+){0,2})\b",
    re.IGNORECASE,
)
_BODY_TRIM = 8_000


_SYSTEM_PROMPT = """You are a meticulous SRE documentation auditor.

Two documents claim to describe the same topic. Identify factual or
procedural contradictions that would cause a reader following one to
take a different action than a reader following the other.

Categories:
- version_mismatch: numbers/versions disagree
- procedure_conflict: steps disagree
- coverage_gap: one covers a case the other omits and this matters
- factual_contradiction: other concrete facts disagree

Severity:
- critical: following the wrong doc causes an outage or data loss
- warning: causes wasted time or confusion
- info: stylistic or minor mismatch

Respond with ONLY a JSON array. Each element must have keys:
  claim_a (str), claim_b (str),
  severity ("critical" | "warning" | "info"),
  category ("version_mismatch" | "procedure_conflict" | "coverage_gap" | "factual_contradiction"),
  explanation (str).
Return [] when there are no real contradictions."""


_USER_TEMPLATE = """Topic: {topic}

--- DOCUMENT A ({label_a}) ---
{text_a}

--- DOCUMENT B ({label_b}) ---
{text_b}

Return a JSON array following the schema in the system prompt."""


class Reconciler:
    """Cross-source reconciler."""

    def __init__(
        self,
        sources: list[DocSource],
        *,
        llm_router: Any | None = None,
        llm_pair_limit: int = 3,
        sensitivity_override: bool | None = True,
    ) -> None:
        """Args:

        sources: List of already-constructed :class:`DocSource` instances.
            Iteration order determines tiebreaker ordering in the
            ranked result list.
        llm_router: Optional Layer 0.4 :class:`LLMRouter` (or anything
            with an async ``.complete(messages, sensitivity_override=...)``
            method). When absent, the reconciler skips the LLM step.
        llm_pair_limit: Maximum pairs to send through the router per
            :meth:`compare` call. Protects token budget on a topic that
            matches hundreds of docs.
        sensitivity_override: Forwarded to the router. Default ``True``
            (route to Ollama / local) because doc bodies may contain
            internal hostnames, account ids, etc. Set ``None`` to let
            the router classify the prompt itself.
        """
        self.sources = list(sources)
        self.llm_router = llm_router
        self.llm_pair_limit = max(1, llm_pair_limit)
        self.sensitivity_override = sensitivity_override

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def find(self, topic: str, sources: list[str] | None = None) -> list[DocRef]:
        """Return a ranked list of :class:`DocRef` for ``topic``.

        Args:
            topic: Substring to match (case-insensitive).
            sources: Optional list of source names to restrict the
                search (``["obsidian", "confluence"]``). ``None`` = all.
        """
        matches = self._collect_matches(topic, sources)
        refs: list[DocRef] = []
        for src, doc in matches:
            freshness = src.score_freshness(doc.id)
            refs.append(
                DocRef(
                    id=doc.id,
                    source=doc.source,
                    title=doc.title,
                    url=doc.url,
                    last_modified=doc.last_modified,
                    freshness_score=round(freshness, 3),
                    snippet=_snippet(doc.body),
                )
            )
        refs.sort(key=lambda r: (-r.freshness_score, r.title.lower()))
        return refs

    async def compare(self, topic: str) -> ReconciliationReport:
        """Query every source, build a ranked DocRef list, and run the
        full contradiction pass (string diff + LLM)."""

        matches = self._collect_matches(topic, None)
        report = ReconciliationReport(
            topic=topic,
            sources_queried=[s.name for s in self.sources],
        )

        # Build DocRefs up front so the report is useful even if the
        # LLM pass fails below.
        for src, doc in matches:
            freshness = src.score_freshness(doc.id)
            report.docs.append(
                DocRef(
                    id=doc.id,
                    source=doc.source,
                    title=doc.title,
                    url=doc.url,
                    last_modified=doc.last_modified,
                    freshness_score=round(freshness, 3),
                    snippet=_snippet(doc.body),
                )
            )
        report.docs.sort(key=lambda r: (-r.freshness_score, r.title.lower()))

        # String-level diff pass — always runs, never calls network.
        pairs = _unique_pairs([doc for _, doc in matches])
        string_findings = self._string_diff(topic, pairs)
        report.contradictions.extend(string_findings)

        # LLM-assisted semantic pass.
        if self.llm_router is None:
            report.llm_available = False
            report.notes.append("llm_router not configured; skipping semantic pass")
            return report

        pairs_to_score = pairs[: self.llm_pair_limit]
        semantic_findings: list[Contradiction] = []
        for a, b in pairs_to_score:
            try:
                items, backend = await self._ask_router(topic, a, b)
                report.llm_backend = backend
                for item in items:
                    semantic_findings.append(_build_contradiction(item, a, b))
            except _RouterUnavailable as exc:
                report.llm_available = False
                report.notes.append(f"llm_router unavailable: {exc}")
                logger.warning("reconciler: LLM unavailable — %s", exc)
                break
            except Exception as exc:  # noqa: BLE001 — don't crash the report
                report.notes.append(f"llm_router error: {exc!r}")
                logger.exception("reconciler: LLM call failed")
                break
        report.contradictions.extend(semantic_findings)
        return report

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _collect_matches(
        self,
        topic: str,
        source_filter: list[str] | None,
    ) -> list[tuple[DocSource, Doc]]:
        matches: list[tuple[DocSource, Doc]] = []
        allowed = {s.lower() for s in source_filter} if source_filter else None
        for src in self.sources:
            if allowed is not None and src.name not in allowed:
                continue
            try:
                hits = src.search(topic)
            except Exception:
                logger.exception("reconciler: source %s.search failed", src.name)
                continue
            for doc in hits:
                matches.append((src, doc))
        return matches

    def _string_diff(
        self,
        topic: str,
        pairs: list[tuple[Doc, Doc]],
    ) -> list[Contradiction]:
        findings: list[Contradiction] = []
        for a, b in pairs:
            # Version mismatch detection: look for keyword-qualified numbers
            # (e.g. "postgres 16") or semver-style numbers (e.g. "1.2.3").
            versions_a = _find_versions(a.body or "")
            versions_b = _find_versions(b.body or "")
            if versions_a and versions_b and versions_a != versions_b:
                only_a = versions_a - versions_b
                only_b = versions_b - versions_a
                if only_a and only_b:
                    findings.append(
                        Contradiction(
                            doc_a=a.global_id,
                            doc_b=b.global_id,
                            claim_a=f"versions cited: {sorted(only_a)}",
                            claim_b=f"versions cited: {sorted(only_b)}",
                            severity="warning",
                            category="version_mismatch",
                            explanation=(
                                "string-diff: doc bodies cite disjoint version numbers"
                            ),
                        )
                    )
        return findings

    async def _ask_router(
        self,
        topic: str,
        a: Doc,
        b: Doc,
    ) -> tuple[list[dict[str, Any]], str]:
        prompt = _USER_TEMPLATE.format(
            topic=topic,
            label_a=a.global_id,
            label_b=b.global_id,
            text_a=_trim(a.body),
            text_b=_trim(b.body),
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = await self.llm_router.complete(
                messages,
                sensitivity_override=self.sensitivity_override,
            )
        except Exception as exc:  # Translate any router failure to our sentinel
            # Detect the specific local-unavailable case by duck-typing
            # on the exception name or message so we don't hard-import
            # OllamaUnavailable.
            name = type(exc).__name__
            msg = str(exc).lower()
            if (
                "Unavailable" in name
                or "Connection" in name
                or "unavailable" in msg
                or "connection refused" in msg
                or "timeout" in msg
            ):
                raise _RouterUnavailable(str(exc)) from exc
            raise

        text = getattr(resp, "text", "") or ""
        backend = getattr(resp, "backend", "unknown")
        return _parse_json_array(text), backend


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class _RouterUnavailable(RuntimeError):
    """Internal sentinel for 'local LLM not reachable' conditions."""


def _find_versions(text: str) -> set[str]:
    """Extract version-like tokens from a body.

    Returns the string form of each version found. The regex has two
    alternatives (keyword-qualified / semver-style); ``finditer`` lets
    us collect either group without tuple-unpack branching.
    """
    hits: set[str] = set()
    for match in _VERSION_RE.finditer(text):
        token = match.group(1) or match.group(2)
        if token:
            hits.add(token)
    return hits


def _snippet(body: str, max_chars: int = 220) -> str:
    if not body:
        return ""
    text = " ".join(body.split())
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


def _trim(text: str) -> str:
    if not text:
        return ""
    if len(text) <= _BODY_TRIM:
        return text
    return text[:_BODY_TRIM] + "\n\n[... truncated ...]"


def _unique_pairs(docs: list[Doc]) -> list[tuple[Doc, Doc]]:
    pairs: list[tuple[Doc, Doc]] = []
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            if a.global_id == b.global_id:
                continue
            key = tuple(sorted((a.global_id, b.global_id)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((a, b))
    return pairs


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    if not stripped.startswith("["):
        match = re.search(r"\[.*\]", stripped, re.DOTALL)
        if not match:
            return []
        stripped = match.group(0)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def _build_contradiction(item: dict[str, Any], a: Doc, b: Doc) -> Contradiction:
    severity = item.get("severity", "warning")
    if severity not in ("critical", "warning", "info"):
        severity = "warning"
    category = item.get("category", "factual_contradiction")
    if category not in (
        "version_mismatch",
        "procedure_conflict",
        "coverage_gap",
        "factual_contradiction",
    ):
        category = "factual_contradiction"
    return Contradiction(
        doc_a=a.global_id,
        doc_b=b.global_id,
        claim_a=str(item.get("claim_a") or "").strip(),
        claim_b=str(item.get("claim_b") or "").strip(),
        severity=severity,
        category=category,
        explanation=str(item.get("explanation") or "").strip(),
    )


__all__ = ["Reconciler"]
