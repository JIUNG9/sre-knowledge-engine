"""Synthesize new source content into existing wiki pages using Claude Haiku.

Two LLM calls per ingest, at most:

1. `decide_action` — cheap routing: given the Source + a slim index of
   existing pages, does this belong on an existing page or does it warrant
   a new one?
2. `synthesize_new_page` OR `merge_into_page` — the actual write.

We deliberately keep the router (1) and writer (2) as separate calls
instead of one-shotting because the router needs the full page index
but not full bodies, and the writer needs the single target body but
not the index. Splitting halves the token cost vs. a combined prompt.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import frontmatter
from pydantic import BaseModel, Field

from .ingester import Source

logger = logging.getLogger("aegis.wiki")

# Anthropic Claude pricing per the spec (USD per 1M tokens).
# Synthesis uses Haiku by default; Sonnet-class pricing is listed for
# callers that opt into a larger model for merges.
_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
}


PageType = Literal["entity", "concept", "incident", "runbook"]
Freshness = Literal["current", "stale", "archived", "needs_review"]


class WikiPage(BaseModel):
    """A materialized Obsidian markdown page.

    `frontmatter` is the canonical source for structured fields (tags,
    sources, type, freshness). `last_updated` and `sources` are also
    mirrored as top-level fields so pydantic validators and downstream
    quality engines can reason about them without re-parsing YAML.
    """

    title: str
    type: PageType
    slug: str
    path: Path
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    body: str = ""
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    sources: list[str] = Field(default_factory=list)
    freshness: Freshness = "current"

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_file(cls, path: Path) -> WikiPage:
        """Parse a page from disk.

        Missing/ill-formed frontmatter is tolerated — we fall back to
        filename-derived slug and default type 'concept', because
        authoring-time pages may be incomplete and we still want them
        indexed (a page that can't be loaded is invisible to synthesis).
        """

        path = Path(path)
        raw = path.read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        meta: dict[str, Any] = dict(post.metadata or {})

        slug = str(meta.get("slug") or path.stem)
        title = str(meta.get("title") or _title_from_body(post.content) or path.stem)
        page_type_raw = str(meta.get("type") or _infer_type_from_path(path))
        if page_type_raw not in ("entity", "concept", "incident", "runbook"):
            page_type_raw = "concept"
        page_type: PageType = page_type_raw  # type: ignore[assignment]

        last_updated_raw = meta.get("last_updated") or meta.get("updated")
        last_updated = _parse_datetime(last_updated_raw) or datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        )

        sources_raw = meta.get("sources") or []
        if isinstance(sources_raw, str):
            sources_raw = [sources_raw]
        sources = [str(s) for s in sources_raw]

        freshness_raw = str(meta.get("freshness") or "current")
        if freshness_raw not in ("current", "stale", "archived", "needs_review"):
            freshness_raw = "current"
        freshness: Freshness = freshness_raw  # type: ignore[assignment]

        return cls(
            title=title,
            type=page_type,
            slug=slug,
            path=path,
            frontmatter=meta,
            body=post.content,
            last_updated=last_updated,
            sources=sources,
            freshness=freshness,
        )

    def to_markdown(self) -> str:
        """Serialize to obsidian markdown with YAML frontmatter.

        We always rewrite frontmatter from the pydantic fields so
        `last_updated`, `sources`, and `freshness` stay in sync with the
        model — easy to forget when editing `self.frontmatter` directly.
        """

        meta: dict[str, Any] = dict(self.frontmatter)
        meta["title"] = self.title
        meta["type"] = self.type
        meta["slug"] = self.slug
        meta["last_updated"] = self.last_updated.isoformat()
        meta["sources"] = list(dict.fromkeys(self.sources))  # de-dup, preserve order
        meta["freshness"] = self.freshness

        post = frontmatter.Post(self.body, **meta)
        return frontmatter.dumps(post)

    def save(self, vault_root: Path) -> Path:
        """Write the page to disk under `<vault_root>/<type>s/<slug>.md`.

        The plural-dir convention (entities/, concepts/, incidents/,
        runbooks/) matches the vault layout the other agent is setting
        up. We create parent dirs on demand so a brand-new vault can
        be populated incrementally.
        """

        vault_root = Path(vault_root).expanduser()
        target_dir = vault_root / f"{self.type}s"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{self.slug}.md"
        target_path.write_text(self.to_markdown(), encoding="utf-8")
        self.path = target_path
        return target_path


class SynthesisDecision(BaseModel):
    """Router output — whether a Source creates/updates/skips a page."""

    action: Literal["create_new", "update_existing", "skip"]
    target_page_slug: str | None = None
    target_type: str | None = None
    reasoning: str = ""


class _TokenUsage(BaseModel):
    """Internal telemetry record for a single Haiku/Sonnet call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class Synthesizer:
    """Wraps Claude calls for wiki synthesis.

    Exposes three async methods: `decide_action`, `synthesize_new_page`,
    `merge_into_page`. Every call returns token usage + cost via the
    `last_usage` attribute (and `all_usage` for cumulative tracking) —
    this is the wiring the FinOps panel reads to show $/month.
    """

    _SYSTEM_PROMPT = (
        "You are the Aegis Wiki synthesizer — an SRE knowledge curator for an "
        "Obsidian vault. You write concise, accurate, cross-linked pages in "
        "standard Obsidian markdown.\n\n"
        "Format rules:\n"
        "- Use YAML frontmatter with fields: title, type, slug, tags, sources, "
        "freshness, last_updated.\n"
        "- `type` is one of: entity, concept, incident, runbook.\n"
        "- Use [[WikiLink]] syntax for references to other pages in the vault. "
        "Prefer [[slug]] or [[slug|display text]].\n"
        "- Keep bodies under 400 lines. Use headings (##, ###), tables, and "
        "code fences. No emojis.\n"
        "- Never invent facts. If the source is ambiguous, say so explicitly "
        "in a '## Open questions' section.\n"
        "- Preserve existing [[WikiLinks]] and headings when merging.\n"
    )

    def __init__(
        self,
        anthropic_client: Any,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        """Store the async Anthropic client + chosen synthesis model.

        `anthropic_client` is expected to be an `AsyncAnthropic` instance,
        but we type it as `Any` so tests can pass mocks without pulling
        the SDK into the test deps.
        """

        self.client = anthropic_client
        self.model = model
        self.last_usage: _TokenUsage | None = None
        self.all_usage: list[_TokenUsage] = []

    # -- Public API -----------------------------------------------------

    async def decide_action(
        self, source: Source, existing_pages: list[WikiPage]
    ) -> SynthesisDecision:
        """Ask Claude whether to create, update, or skip.

        We pass only (slug, title, type, 1-line summary) for each page —
        full bodies would blow the context window on a large vault and
        aren't needed for routing.
        """

        index_entries: list[dict[str, str]] = []
        for p in existing_pages:
            summary = _first_sentence(p.body)[:200]
            index_entries.append(
                {
                    "slug": p.slug,
                    "title": p.title,
                    "type": p.type,
                    "summary": summary,
                }
            )

        user_prompt = (
            "Decide whether the new source below should create a new wiki page, "
            "merge into an existing page, or be skipped.\n\n"
            "Respond with a JSON object only (no markdown fences), with keys:\n"
            "  action: one of 'create_new', 'update_existing', 'skip'\n"
            "  target_page_slug: slug if updating, else null\n"
            "  target_type: one of 'entity', 'concept', 'incident', 'runbook' "
            "if creating, else null\n"
            "  reasoning: 1-3 sentences explaining the choice\n\n"
            f"EXISTING PAGES (index):\n{json.dumps(index_entries, indent=2)}\n\n"
            f"NEW SOURCE:\n"
            f"- type: {source.type.value}\n"
            f"- path: {source.path_or_url}\n"
            f"- metadata: {json.dumps(source.metadata, default=str)[:1000]}\n\n"
            f"CONTENT (truncated to 6000 chars):\n{source.content[:6000]}\n"
        )

        text = await self._call(
            system=self._SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=512,
        )
        data = _extract_json(text)
        try:
            return SynthesisDecision(**data)
        except Exception as exc:  # noqa: BLE001 - pydantic raises ValidationError
            logger.warning("decide_action: invalid JSON from model: %s", exc)
            return SynthesisDecision(
                action="skip",
                reasoning=f"router returned unparseable response: {text[:200]}",
            )

    async def synthesize_new_page(
        self, source: Source, page_type: str
    ) -> WikiPage:
        """Write a brand-new page from a single Source."""

        slug = _slugify(
            source.metadata.get("title")
            or _title_from_body(source.content)
            or Path(source.path_or_url).stem
            or source.id
        )
        user_prompt = (
            f"Write a new Obsidian wiki page of type '{page_type}' from the "
            "source below. Output the full markdown file (frontmatter + body). "
            "Include this frontmatter at minimum:\n"
            f"  title, type: {page_type}, slug: {slug}, tags: [...], "
            f"sources: ['{source.path_or_url}'], freshness: current\n\n"
            "Body must start with a one-paragraph summary, then detailed "
            "sections. Use [[WikiLink]]s for any services, concepts, or "
            "incidents you reference.\n\n"
            f"SOURCE type: {source.type.value}\n"
            f"SOURCE path: {source.path_or_url}\n"
            f"SOURCE metadata: {json.dumps(source.metadata, default=str)[:1000]}\n\n"
            f"SOURCE CONTENT:\n{source.content[:12000]}\n"
        )

        text = await self._call(
            system=self._SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4096,
        )
        post = frontmatter.loads(_strip_markdown_fence(text))
        meta: dict[str, Any] = dict(post.metadata or {})
        title = str(meta.get("title") or _title_from_body(post.content) or slug)
        meta.setdefault("type", page_type)
        meta.setdefault("slug", slug)
        meta.setdefault("sources", [source.path_or_url])
        meta.setdefault("freshness", "current")

        page_type_val = str(meta.get("type") or page_type)
        if page_type_val not in ("entity", "concept", "incident", "runbook"):
            page_type_val = "concept"

        return WikiPage(
            title=title,
            type=page_type_val,  # type: ignore[arg-type]
            slug=str(meta.get("slug") or slug),
            path=Path(f"{meta.get('slug') or slug}.md"),
            frontmatter=meta,
            body=post.content,
            last_updated=datetime.now(timezone.utc),
            sources=[str(s) for s in meta.get("sources", [source.path_or_url])],
            freshness="current",
        )

    async def merge_into_page(
        self, source: Source, existing_page: WikiPage
    ) -> WikiPage:
        """Merge new source content into an existing page body.

        The prompt explicitly forbids dropping existing [[WikiLinks]] or
        headings — LLMs will otherwise happily rewrite the whole page,
        which breaks Obsidian's backlink graph.
        """

        user_prompt = (
            "Merge the new source into the existing wiki page. Return the "
            "COMPLETE updated markdown file (frontmatter + body).\n\n"
            "Rules:\n"
            "- Preserve ALL existing [[WikiLinks]] unless they are factually "
            "wrong — if you remove one, justify it in an HTML comment.\n"
            "- Preserve all top-level (## ) headings that already exist.\n"
            "- Append new facts under the most relevant heading or create a "
            "new subsection.\n"
            "- Update frontmatter: add the new source URL to `sources`, set "
            "`last_updated` to now, keep `freshness: current`.\n"
            "- Do not duplicate information already present.\n\n"
            f"EXISTING PAGE ({existing_page.slug}):\n"
            f"{existing_page.to_markdown()}\n\n"
            f"NEW SOURCE:\n"
            f"- type: {source.type.value}\n"
            f"- path: {source.path_or_url}\n"
            f"- metadata: {json.dumps(source.metadata, default=str)[:800]}\n\n"
            f"CONTENT:\n{source.content[:10000]}\n"
        )

        text = await self._call(
            system=self._SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=6144,
        )
        post = frontmatter.loads(_strip_markdown_fence(text))
        meta: dict[str, Any] = dict(post.metadata or {})

        # Merge sources: keep existing + new, de-duplicated.
        merged_sources = list(
            dict.fromkeys(
                list(existing_page.sources)
                + [str(s) for s in meta.get("sources", [])]
                + [source.path_or_url]
            )
        )
        meta["sources"] = merged_sources
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        meta.setdefault("type", existing_page.type)
        meta.setdefault("slug", existing_page.slug)
        meta.setdefault("freshness", "current")

        page_type_val = str(meta.get("type") or existing_page.type)
        if page_type_val not in ("entity", "concept", "incident", "runbook"):
            page_type_val = existing_page.type

        return WikiPage(
            title=str(meta.get("title") or existing_page.title),
            type=page_type_val,  # type: ignore[arg-type]
            slug=str(meta.get("slug") or existing_page.slug),
            path=existing_page.path,
            frontmatter=meta,
            body=post.content,
            last_updated=datetime.now(timezone.utc),
            sources=merged_sources,
            freshness="current",
        )

    # -- Internals ------------------------------------------------------

    async def _call(self, system: str, user: str, max_tokens: int) -> str:
        """Run one Anthropic messages call and record cost.

        Uses the AsyncAnthropic v1 `messages.create` shape. We read
        `usage.input_tokens` / `usage.output_tokens` if present and fall
        back to zeros so mocks without usage info still work.
        """

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        # Extract text content across possible SDK shapes (block or string).
        text = ""
        content = getattr(response, "content", None) or []
        for block in content:
            block_text = getattr(block, "text", None)
            if block_text is not None:
                text += block_text
            elif isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        pricing = _PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        cost = (
            input_tokens * pricing["input"] / 1_000_000
            + output_tokens * pricing["output"] / 1_000_000
        )

        record = _TokenUsage(
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
        )
        self.last_usage = record
        self.all_usage.append(record)
        logger.debug(
            "claude call: model=%s in=%d out=%d cost=$%.6f",
            self.model,
            input_tokens,
            output_tokens,
            cost,
        )
        return text


# -- Module-private helpers ---------------------------------------------


_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FENCE_RE = re.compile(r"^```(?:\w+)?\s*\n(.+?)\n```\s*$", re.DOTALL)


def _title_from_body(body: str) -> str | None:
    """Return the first H1 heading in a markdown body, if any."""

    match = _HEADING_RE.search(body or "")
    if match:
        return match.group(1).strip()
    return None


def _first_sentence(body: str) -> str:
    """Crude first-sentence extractor for the page-index summary."""

    stripped = (body or "").strip()
    if not stripped:
        return ""
    # Skip leading headings — they're metadata, not content.
    for line in stripped.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Return up to the first period or newline.
        match = re.match(r"(.+?[.!?])\s", line + " ")
        if match:
            return match.group(1)
        return line
    return ""


def _slugify(text: str) -> str:
    """Obsidian-friendly slug: lowercase kebab, ascii only."""

    slug = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return slug or "untitled"


def _infer_type_from_path(path: Path) -> str:
    """Infer page type from its parent directory in the vault."""

    for part in reversed(path.parts):
        normalized = part.lower().rstrip("s")
        if normalized in ("entity", "concept", "incident", "runbook"):
            return normalized
    return "concept"


def _parse_datetime(value: Any) -> datetime | None:
    """Best-effort datetime parser for frontmatter values.

    python-frontmatter returns native datetime for YAML timestamps; str
    values come in from hand-edited files. We tolerate both and bail
    to None if the format is unrecognized (the caller falls back to
    file mtime).
    """

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM response.

    Tolerates leading prose and code fences — Haiku sometimes wraps
    the JSON in ```json ... ``` despite being told not to.
    """

    candidate = text.strip()
    fence = _FENCE_RE.match(candidate)
    if fence:
        candidate = fence.group(1).strip()

    # Find the first '{' and the last '}' to slice out the JSON object.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _strip_markdown_fence(text: str) -> str:
    """Remove a wrapping ```markdown ... ``` fence if the model added one."""

    stripped = text.strip()
    fence = _FENCE_RE.match(stripped)
    if fence:
        return fence.group(1)
    return stripped
