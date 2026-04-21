"""Pluggable documentation sources.

Every source subclasses :class:`DocSource` and implements four methods:

- ``list()``            — enumerate every doc id the source can reach.
- ``fetch(id)``         — return a hydrated :class:`~reconciliation.models.Doc`.
- ``last_modified(id)`` — timestamp for freshness scoring.
- ``score_freshness(id)`` — 0.0 (stale) … 1.0 (fresh), computed from age.

Adding a new source (Notion, Google Docs, etc.) is a subclass-only
exercise — the reconciler, drift engine, and MCP tools never
discriminate between source types.

All sources are intentionally synchronous for simplicity: source I/O
is dominated by external HTTP latency, which the MCP tool wrapper can
``asyncio.to_thread`` around if the caller needs it.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import Doc, SourceName

logger = logging.getLogger("aegis.reconciliation.sources")


# --------------------------------------------------------------------------- #
# Freshness curve
# --------------------------------------------------------------------------- #
#
# The default freshness curve is a simple piecewise linear decay:
#
#   0 days  -> 1.0     (perfectly fresh)
#   180 d   -> 0.5     (half life)
#   365 d   -> 0.1     (a year old)
#   730 d+  -> 0.0     (two years or older — treat as stale floor)
#
# Individual sources can override `_freshness_curve` if they want a
# different policy — runbooks tolerate age better than incident dumps.


def _default_freshness(age_days: int | None) -> float:
    if age_days is None:
        return 0.0
    if age_days <= 0:
        return 1.0
    if age_days >= 730:
        return 0.0
    if age_days <= 180:
        # 1.0 -> 0.5 over 180 days
        return max(0.0, 1.0 - (age_days / 180.0) * 0.5)
    if age_days <= 365:
        # 0.5 -> 0.1 over next 185 days
        frac = (age_days - 180) / 185.0
        return max(0.0, 0.5 - frac * 0.4)
    # 0.1 -> 0.0 over final 365 days
    frac = (age_days - 365) / 365.0
    return max(0.0, 0.1 - frac * 0.1)


# --------------------------------------------------------------------------- #
# Abstract base
# --------------------------------------------------------------------------- #


class DocSource(ABC):
    """Abstract base class for any document source."""

    #: stable string identifier used in :class:`~reconciliation.models.Doc`
    name: SourceName = "obsidian"  # type: ignore[assignment]

    @abstractmethod
    def list(self) -> list[str]:
        """Return every doc id the source can reach."""

    @abstractmethod
    def fetch(self, doc_id: str) -> Doc | None:
        """Hydrate a doc by id, or return ``None`` if missing."""

    def last_modified(self, doc_id: str) -> datetime | None:
        """Default: pull ``last_modified`` from :meth:`fetch`. Override
        for sources that can answer the question without full fetch."""
        doc = self.fetch(doc_id)
        return doc.last_modified if doc else None

    def score_freshness(self, doc_id: str) -> float:
        """Return a freshness score between 0.0 (stale) and 1.0 (fresh)."""
        ts = self.last_modified(doc_id)
        return self._freshness_curve(_age_days(ts))

    @staticmethod
    def _freshness_curve(age_days: int | None) -> float:
        return _default_freshness(age_days)

    # ------------------------------------------------------------------ #
    # Convenience helpers shared by concrete sources
    # ------------------------------------------------------------------ #
    def search(self, topic: str) -> list[Doc]:
        """Return every doc whose title/body/tags mention ``topic``.

        Case-insensitive, no stemming. Sources with a smarter backend
        (e.g. Confluence CQL) should override this to avoid fetching
        every page locally.
        """
        needle = topic.lower().strip()
        hits: list[Doc] = []
        if not needle:
            return hits
        for doc_id in self.list():
            doc = self.fetch(doc_id)
            if doc is None:
                continue
            haystack = " ".join(
                [doc.title or "", doc.body or "", " ".join(doc.tags or [])]
            ).lower()
            if needle in haystack:
                hits.append(doc)
        return hits


def _age_days(ts: datetime | None) -> int | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    return max(delta.days, 0)


# --------------------------------------------------------------------------- #
# Obsidian (local markdown vault)
# --------------------------------------------------------------------------- #


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class ObsidianSource(DocSource):
    """Read ``.md`` files from an Obsidian vault on the local filesystem.

    Slugs are the file stems. ``_archive`` and ``_meta`` are skipped
    because those are Aegis-internal bookkeeping directories — we don't
    want archived pages re-surfacing in reconciliation results.
    """

    name: SourceName = "obsidian"

    def __init__(self, vault_root: Path | str) -> None:
        self.vault_root = Path(vault_root).expanduser()

    # ------------------------------------------------------------------ #
    def _iter_files(self) -> Iterable[Path]:
        if not self.vault_root.exists():
            return []
        for path in self.vault_root.rglob("*.md"):
            parts = set(path.parts)
            if "_archive" in parts or "_meta" in parts:
                continue
            yield path

    def list(self) -> list[str]:
        return [str(p.relative_to(self.vault_root)) for p in self._iter_files()]

    def fetch(self, doc_id: str) -> Doc | None:
        path = self.vault_root / doc_id
        if not path.exists() or not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        fm, body = _split_frontmatter(raw)
        title = fm.get("title") or path.stem
        tags_raw = fm.get("tags")
        tags = _normalise_tags(tags_raw)
        last_modified = _ts_from_frontmatter(fm) or _ts_from_stat(path)
        return Doc(
            id=doc_id,
            source=self.name,
            title=str(title),
            body=body,
            url=None,
            last_modified=last_modified,
            tags=tags,
            metadata={"path": str(path), "frontmatter": fm},
        )


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Cheap YAML-ish frontmatter split. Enough for freshness + tags —
    we intentionally avoid a PyYAML dep for test portability."""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    block = m.group(1)
    fm: dict[str, Any] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Handle simple list syntax: tags: [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            fm[key] = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
        elif value:
            fm[key] = value.strip("\"'")
    return fm, raw[m.end() :]


def _ts_from_frontmatter(fm: dict[str, Any]) -> datetime | None:
    for key in ("last_updated", "updated", "date", "modified"):
        if key in fm:
            try:
                value = fm[key]
                if isinstance(value, datetime):
                    return value
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _ts_from_stat(path: Path) -> datetime | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _normalise_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw if t]
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


# --------------------------------------------------------------------------- #
# Confluence (wraps wiki.confluence_sync for the HTTP bits)
# --------------------------------------------------------------------------- #


class ConfluenceSource(DocSource):
    """Confluence wrapper.

    Accepts pre-fetched pages directly (the common case — ``ConfluenceSync``
    already hits the API and stores pages locally). Tests and offline
    usage can bypass the network by passing ``pages`` at construction.
    """

    name: SourceName = "confluence"

    def __init__(
        self,
        pages: list[dict[str, Any]] | None = None,
        *,
        sync: Any | None = None,
    ) -> None:
        self._sync = sync
        self._pages: dict[str, dict[str, Any]] = {}
        if pages:
            for page in pages:
                pid = str(page.get("id") or "")
                if pid:
                    self._pages[pid] = page

    # ------------------------------------------------------------------ #
    def load_from_sync(self, pages: list[dict[str, Any]]) -> None:
        """Populate the source from a ``ConfluenceSync.fetch_all_pages()`` result."""
        for page in pages:
            pid = str(page.get("id") or "")
            if pid:
                self._pages[pid] = page

    def list(self) -> list[str]:
        return list(self._pages.keys())

    def fetch(self, doc_id: str) -> Doc | None:
        page = self._pages.get(str(doc_id))
        if not page:
            return None
        body_wrap = (page.get("body") or {}).get("storage") or {}
        body = str(body_wrap.get("value") or page.get("body_markdown") or "")
        version = page.get("version") or {}
        last_modified = _parse_iso(
            version.get("createdAt") or page.get("updatedAt") or page.get("createdAt")
        )
        tags_raw = (page.get("metadata") or {}).get("labels") or []
        tags = [str(t.get("name") or t) if isinstance(t, dict) else str(t) for t in tags_raw]
        return Doc(
            id=str(page.get("id") or ""),
            source=self.name,
            title=str(page.get("title") or ""),
            body=body,
            url=page.get("_links", {}).get("webui") if isinstance(page.get("_links"), dict) else None,
            last_modified=last_modified,
            tags=tags,
            metadata={"space_key": page.get("spaceId"), "version": version},
        )


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# GitHub Wiki (local clone of a repo's .wiki.git)
# --------------------------------------------------------------------------- #


class GitHubWikiSource(DocSource):
    """Read a GitHub wiki backed by a local clone of ``repo.wiki.git``.

    The GitHub wiki storage format is a flat directory of markdown files
    (``Home.md``, ``Runbook-Database.md``, …). We treat it just like
    Obsidian but rooted at the clone path.
    """

    name: SourceName = "github_wiki"

    def __init__(self, wiki_root: Path | str, *, repo_url: str | None = None) -> None:
        self.wiki_root = Path(wiki_root).expanduser()
        self.repo_url = repo_url

    def _iter_files(self) -> Iterable[Path]:
        if not self.wiki_root.exists():
            return []
        for path in self.wiki_root.glob("*.md"):
            yield path

    def list(self) -> list[str]:
        return [p.name for p in self._iter_files()]

    def fetch(self, doc_id: str) -> Doc | None:
        path = self.wiki_root / doc_id
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        fm, body = _split_frontmatter(raw)
        title = fm.get("title") or path.stem.replace("-", " ")
        url = None
        if self.repo_url:
            url = f"{self.repo_url.rstrip('/')}/wiki/{path.stem}"
        return Doc(
            id=doc_id,
            source=self.name,
            title=str(title),
            body=body,
            url=url,
            last_modified=_ts_from_stat(path),
            tags=_normalise_tags(fm.get("tags")),
            metadata={"path": str(path)},
        )


# --------------------------------------------------------------------------- #
# Slack-pinned messages (stub — access is out-of-scope for v1)
# --------------------------------------------------------------------------- #


class SlackPinSource(DocSource):
    """Stub source for Slack-pinned messages.

    The real integration would hit ``conversations.pins.list`` + a
    lookup cache, but token scoping + workspace-admin approval are
    non-trivial so v1 ships a stub you can seed with test fixtures.
    Any supplied ``pins`` act as the authoritative doc set so the
    contradiction engine can still be exercised in tests.
    """

    name: SourceName = "slack_pin"

    def __init__(self, pins: list[dict[str, Any]] | None = None) -> None:
        self._pins: dict[str, dict[str, Any]] = {}
        if pins:
            for pin in pins:
                pid = str(pin.get("id") or pin.get("ts") or "")
                if pid:
                    self._pins[pid] = pin

    def list(self) -> list[str]:
        return list(self._pins.keys())

    def fetch(self, doc_id: str) -> Doc | None:
        pin = self._pins.get(str(doc_id))
        if not pin:
            return None
        body = str(pin.get("text") or pin.get("body") or "")
        return Doc(
            id=doc_id,
            source=self.name,
            title=str(pin.get("title") or body.splitlines()[0][:80] if body else doc_id),
            body=body,
            url=pin.get("permalink"),
            last_modified=_parse_iso(pin.get("pinned_at") or pin.get("ts_iso")),
            tags=list(pin.get("tags") or []),
            metadata={"channel": pin.get("channel"), "user": pin.get("user")},
        )


# --------------------------------------------------------------------------- #
# Link extraction (used by docs_link_check)
# --------------------------------------------------------------------------- #


def extract_links(body: str) -> tuple[list[str], list[str]]:
    """Return ``(internal_links, external_links)`` from a markdown body."""
    internal: list[str] = []
    external: list[str] = []
    for match in _WIKILINK_RE.finditer(body or ""):
        internal.append(match.group(1).strip())
    for match in _MD_LINK_RE.finditer(body or ""):
        url = match.group(1).strip()
        if url.startswith("http://") or url.startswith("https://"):
            external.append(url)
        else:
            internal.append(url)
    # Dedupe, preserve order
    internal = list(dict.fromkeys(internal))
    external = list(dict.fromkeys(external))
    return internal, external


__all__ = [
    "DocSource",
    "ObsidianSource",
    "ConfluenceSource",
    "GitHubWikiSource",
    "SlackPinSource",
    "extract_links",
]
