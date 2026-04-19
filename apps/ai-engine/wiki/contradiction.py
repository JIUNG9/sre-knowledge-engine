"""Detect contradictions between wiki pages and new incoming sources.

The ContradictionDetector uses Claude Sonnet (reasoning-grade) to compare
pairs of pages or a new source against an existing page, and emits a
structured report of factual or procedural disagreements.

Results persist to ``~/Documents/obsidian-sre/_meta/contradictions.json``
so the Obsidian side can render a dashboard without re-running Claude.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, TYPE_CHECKING

import anyio
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

    from .synthesizer import WikiPage


log = logging.getLogger("aegis.wiki")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTRADICTIONS_PATH = Path.home() / "Documents" / "obsidian-sre" / "_meta" / "contradictions.json"

# Rough token pricing for claude-sonnet-4-6 (USD per million tokens).
# Used for a best-effort cost estimate; not billed — the Anthropic usage
# object is authoritative where available.
_SONNET_INPUT_PER_MTOK = 3.0
_SONNET_OUTPUT_PER_MTOK = 15.0

SeverityT = Literal["critical", "warning", "info"]
CategoryT = Literal[
    "version_mismatch",
    "procedure_conflict",
    "coverage_gap",
    "factual_contradiction",
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Contradiction(BaseModel):
    """A single conflicting pair of claims between two pages/sources."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    page_a_slug: str
    page_b_slug: str | None = None  # None-or-source-id for incoming-vs-existing
    claim_a: str
    claim_b: str
    severity: SeverityT
    category: CategoryT
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_note: str | None = None


class ContradictionReport(BaseModel):
    """Output of a vault-wide contradiction scan."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_pages_scanned: int
    contradictions: list[Contradiction] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Claude JSON schema (documented in module docstring for downstream agents)
# ---------------------------------------------------------------------------
#
# The detector asks Claude to return a JSON array of objects matching:
#
#   {
#     "claim_a": str,           # exact/near-exact sentence from page A
#     "claim_b": str,           # exact/near-exact sentence from page B / new source
#     "severity": "critical" | "warning" | "info",
#     "category": "version_mismatch" | "procedure_conflict"
#                | "coverage_gap"    | "factual_contradiction",
#     "explanation": str        # one-sentence rationale (not persisted, used for logging)
#   }
#
# Empty array means "no contradictions found."
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """You are a meticulous SRE documentation auditor.

Given two documents that overlap on some topic, identify factual or procedural
contradictions between them. A contradiction is only worth reporting if a reader
following one document would take a different action than one following the other.

Categories:
- version_mismatch: numbers/versions disagree (e.g. "terraform 1.8" vs "terraform 1.5")
- procedure_conflict: steps disagree (e.g. "restart pods" vs "scale to 0")
- coverage_gap: one document covers a case the other omits and this matters
  (e.g. post-mortem mentions DNS failures but the runbook has no DNS step)
- factual_contradiction: other concrete facts disagree (IDs, owners, names,
  e.g. "account is 123" vs "account is 456")

Severity:
- critical: following the wrong document causes an incident, outage, or data loss
- warning:  causes wasted time, confusion, or skipped safeguards
- info:     stylistic or minor mismatch; reader can figure it out

Respond with ONLY a JSON array. No prose, no markdown fence. Use the exact
schema documented in the user message. Return [] if there are no real
contradictions — do not manufacture them."""


_USER_TEMPLATE = """Topic: {topic}

--- DOCUMENT A ({label_a}) ---
{text_a}

--- DOCUMENT B ({label_b}) ---
{text_b}

Return a JSON array. Each element must have keys:
  claim_a (str), claim_b (str), severity (critical|warning|info),
  category (version_mismatch|procedure_conflict|coverage_gap|factual_contradiction),
  explanation (str).
If nothing conflicts, return []."""


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class ContradictionDetector:
    """Claude-powered contradiction detector."""

    def __init__(
        self,
        anthropic_client: "AsyncAnthropic",
        model: str = "claude-sonnet-4-6",
        persist_path: Path | None = None,
    ) -> None:
        self.client = anthropic_client
        self.model = model
        self.persist_path = persist_path or CONTRADICTIONS_PATH

    # --- public API --------------------------------------------------------

    async def detect_in_pair(
        self,
        page_a: "WikiPage",
        page_b: "WikiPage",
    ) -> list[Contradiction]:
        """Compare two existing wiki pages."""
        topic = _infer_topic(page_a, page_b)
        items, _cost = await self._ask_claude(
            topic=topic,
            label_a=page_a.slug,
            text_a=page_a.body,
            label_b=page_b.slug,
            text_b=page_b.body,
        )
        return [
            _build_contradiction(item, page_a_slug=page_a.slug, page_b_slug=page_b.slug)
            for item in items
        ]

    async def detect_new_vs_existing(
        self,
        new_content: str,
        existing_page: "WikiPage",
        source_id: str = "incoming",
    ) -> list[Contradiction]:
        """Compare an incoming source chunk against a page before merging."""
        topic = existing_page.title or existing_page.slug
        items, _cost = await self._ask_claude(
            topic=topic,
            label_a=existing_page.slug,
            text_a=existing_page.body,
            label_b=source_id,
            text_b=new_content,
        )
        return [
            _build_contradiction(item, page_a_slug=existing_page.slug, page_b_slug=source_id)
            for item in items
        ]

    async def scan_vault(self, pages: list["WikiPage"]) -> ContradictionReport:
        """Pairwise scan. Clusters pages by shared tags/wikilinks first to
        avoid O(n^2) Claude calls on unrelated pages."""
        clusters = _cluster_pages_by_topic(pages)
        log.info(
            "contradiction.scan_vault: %d pages -> %d clusters",
            len(pages),
            len(clusters),
        )

        all_contradictions: list[Contradiction] = []
        total_cost = 0.0

        for cluster_key, cluster_pages in clusters.items():
            if len(cluster_pages) < 2:
                continue
            for a, b in _unique_pairs(cluster_pages):
                try:
                    items, cost = await self._ask_claude(
                        topic=cluster_key,
                        label_a=a.slug,
                        text_a=a.body,
                        label_b=b.slug,
                        text_b=b.body,
                    )
                    total_cost += cost
                    for item in items:
                        all_contradictions.append(
                            _build_contradiction(item, page_a_slug=a.slug, page_b_slug=b.slug)
                        )
                except Exception:
                    log.exception(
                        "contradiction.scan_vault: failed pair %s <-> %s", a.slug, b.slug
                    )

        summary = _summarize(all_contradictions)
        report = ContradictionReport(
            total_pages_scanned=len(pages),
            contradictions=all_contradictions,
            summary=summary,
            estimated_cost_usd=round(total_cost, 4),
        )
        await self._persist(report)
        return report

    # --- internals ---------------------------------------------------------

    async def _ask_claude(
        self,
        *,
        topic: str,
        label_a: str,
        text_a: str,
        label_b: str,
        text_b: str,
    ) -> tuple[list[dict[str, Any]], float]:
        """Returns (parsed-items, estimated-usd-cost-for-this-call)."""
        prompt = _USER_TEMPLATE.format(
            topic=topic,
            label_a=label_a,
            label_b=label_b,
            text_a=_trim(text_a),
            text_b=_trim(text_b),
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = _extract_text(response)
        items = _parse_json_array(text)
        cost = _estimate_cost(response)
        return items, cost

    async def _persist(self, report: ContradictionReport) -> None:
        """Write report JSON to the Obsidian _meta folder."""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = report.model_dump(mode="json")
            async with await anyio.open_file(self.persist_path, "w") as f:
                await f.write(json.dumps(payload, indent=2, default=str))
            log.info(
                "contradiction: persisted %d findings to %s",
                len(report.contradictions),
                self.persist_path,
            )
        except Exception:
            log.exception("contradiction: failed to persist report")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_MAX_BODY_CHARS = 12_000  # keep prompts reasonable


def _trim(text: str) -> str:
    if len(text) <= _MAX_BODY_CHARS:
        return text
    return text[:_MAX_BODY_CHARS] + "\n\n[... truncated ...]"


def _extract_text(response: Any) -> str:
    """Pull the first text block out of an Anthropic Messages response."""
    try:
        blocks = response.content or []
        for block in blocks:
            btype = getattr(block, "type", None)
            if btype == "text":
                return getattr(block, "text", "") or ""
    except Exception:
        log.exception("contradiction: could not extract response text")
    return ""


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    """Best-effort parse of a JSON array from Claude's response."""
    if not text:
        return []
    stripped = text.strip()
    # Strip common markdown fences if Claude ignores instructions.
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    # If Claude prepended prose, extract the first [...] block.
    if not stripped.startswith("["):
        m = re.search(r"\[.*\]", stripped, re.DOTALL)
        if not m:
            log.warning("contradiction: no JSON array in response: %r", text[:200])
            return []
        stripped = m.group(0)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        log.warning("contradiction: invalid JSON from Claude: %r", stripped[:200])
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def _build_contradiction(
    item: dict[str, Any],
    *,
    page_a_slug: str,
    page_b_slug: str | None,
) -> Contradiction:
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
        page_a_slug=page_a_slug,
        page_b_slug=page_b_slug,
        claim_a=str(item.get("claim_a", "")).strip(),
        claim_b=str(item.get("claim_b", "")).strip(),
        severity=severity,
        category=category,
    )


def _estimate_cost(response: Any) -> float:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0.0
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    return (
        (in_tok / 1_000_000) * _SONNET_INPUT_PER_MTOK
        + (out_tok / 1_000_000) * _SONNET_OUTPUT_PER_MTOK
    )


def _summarize(contradictions: list[Contradiction]) -> dict[str, int]:
    summary: dict[str, int] = defaultdict(int)
    summary["total"] = len(contradictions)
    for c in contradictions:
        summary[f"severity.{c.severity}"] += 1
        summary[f"category.{c.category}"] += 1
    return dict(summary)


def _infer_topic(a: "WikiPage", b: "WikiPage") -> str:
    """Pick a human-readable topic string for the prompt."""
    if a.title and b.title and a.title == b.title:
        return a.title
    return f"{a.title or a.slug} / {b.title or b.slug}"


def _extract_wikilinks(body: str) -> set[str]:
    return {m.group(1).strip().lower() for m in _WIKILINK_RE.finditer(body or "")}


def _page_tags(page: "WikiPage") -> set[str]:
    """Collect tag-ish keys for clustering. Uses frontmatter.tags and wikilinks."""
    tags: set[str] = set()
    fm = getattr(page, "frontmatter", None) or {}
    raw = fm.get("tags") if isinstance(fm, dict) else None
    if isinstance(raw, (list, tuple, set)):
        tags.update(str(t).lower() for t in raw if t)
    elif isinstance(raw, str):
        tags.update(t.strip().lower() for t in raw.split(",") if t.strip())
    # Use wikilinks too — pages linking the same target probably overlap.
    tags.update(_extract_wikilinks(getattr(page, "body", "") or ""))
    # And the page's own type as a coarse bucket.
    ptype = getattr(page, "type", None)
    if ptype:
        tags.add(f"type:{str(ptype).lower()}")
    return tags


def _cluster_pages_by_topic(pages: list["WikiPage"]) -> dict[str, list["WikiPage"]]:
    """Cheap clustering: any shared tag or wikilink puts pages in the same bucket.
    One page can be in multiple buckets — pair dedup happens in _unique_pairs.
    """
    clusters: dict[str, list["WikiPage"]] = defaultdict(list)
    for p in pages:
        keys = _page_tags(p)
        if not keys:
            # Fallback: bucket by slug prefix so it isn't skipped entirely.
            keys = {f"slug:{p.slug.split('-')[0]}"}
        for k in keys:
            clusters[k].append(p)
    return clusters


def _unique_pairs(pages: Iterable["WikiPage"]) -> Iterable[tuple["WikiPage", "WikiPage"]]:
    """Yield each unordered pair exactly once across the whole scan."""
    seen: set[tuple[str, str]] = set()
    lst = list(pages)
    for i, a in enumerate(lst):
        for b in lst[i + 1 :]:
            key = tuple(sorted((a.slug, b.slug)))
            if key in seen or key[0] == key[1]:
                continue
            seen.add(key)
            yield a, b
