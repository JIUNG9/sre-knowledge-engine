"""Ingest sources into raw knowledge units for the LLM Wiki Engine.

Ingestion is intentionally format-agnostic: every input (markdown, PDF,
SigNoz incident payload, Confluence page) is normalized into a `Source`
with a stable content-addressable id and a metadata bag. Downstream,
the Synthesizer decides whether the Source spawns a new wiki page or
merges into an existing one — so this layer must stay lossless and
lightweight (no LLM calls, no network I/O beyond what the caller
already did).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import anyio
import frontmatter
from pydantic import BaseModel, Field
from pypdf import PdfReader

logger = logging.getLogger("aegis.wiki")


class SourceType(str, Enum):
    """Enumerates every input flavor the wiki engine can ingest.

    Kept as str-enum so it round-trips cleanly through JSON and
    pydantic without a custom serializer.
    """

    MARKDOWN = "markdown"
    PDF = "pdf"
    TEXT = "text"
    SIGNOZ_INCIDENT = "signoz_incident"
    CONFLUENCE_PAGE = "confluence_page"
    GITHUB_MD = "github_md"


class Source(BaseModel):
    """A normalized knowledge unit ready for synthesis.

    `id` is SHA256(content)[:16] by default — content-addressable so the
    same file re-ingested produces an identical id, which lets the
    synthesizer de-duplicate without consulting a database.
    """

    id: str
    type: SourceType
    path_or_url: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def _content_id(content: str) -> str:
    """Return the first 16 hex chars of SHA256(content).

    Kept as a module-level helper so tests and callers that construct
    Sources manually (e.g. from SigNoz payloads) can reuse the same
    hashing scheme the file ingest path uses.
    """

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return digest[:16]


class Ingester:
    """Dispatches raw inputs to format-specific parsers.

    The class is stateless; an instance exists mainly so callers can
    share a single object and so subclasses can override individual
    `_ingest_*` methods (for example, to add OCR for scanned PDFs).
    """

    _EXTENSION_DISPATCH: dict[str, str] = {
        ".md": "_ingest_markdown",
        ".markdown": "_ingest_markdown",
        ".txt": "_ingest_text",
        ".pdf": "_ingest_pdf",
    }

    async def ingest_file(self, path: Path) -> Source:
        """Ingest a file from disk, picking the parser by extension.

        Raises ValueError for unsupported extensions rather than
        falling back to a text read — silent fallback tends to produce
        garbled content for binary formats the caller didn't expect
        to be ingested.
        """

        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"source file not found: {path}")

        handler_name = self._EXTENSION_DISPATCH.get(path.suffix.lower())
        if handler_name is None:
            raise ValueError(
                f"unsupported source extension: {path.suffix!r} ({path.name})"
            )

        handler = getattr(self, handler_name)
        source: Source = await handler(path)
        logger.info(
            "ingested %s (%s, %d chars, id=%s)",
            path.name,
            source.type.value,
            len(source.content),
            source.id,
        )
        return source

    async def _ingest_markdown(self, path: Path) -> Source:
        """Parse a markdown file, splitting YAML frontmatter from body.

        Uses python-frontmatter so we get proper YAML handling and the
        body back with frontmatter stripped — important because the
        id hash must be computed on body only (otherwise trivial
        frontmatter tweaks would invalidate content dedup).
        """

        raw = await anyio.Path(path).read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        body = post.content
        metadata: dict[str, Any] = dict(post.metadata or {})
        metadata.setdefault("filename", path.name)
        return Source(
            id=_content_id(body),
            type=SourceType.MARKDOWN,
            path_or_url=str(path),
            content=body,
            metadata=metadata,
        )

    async def _ingest_text(self, path: Path) -> Source:
        """Read a plain text file as UTF-8.

        Plain-text files lack structured metadata, so we stash the
        filename only — downstream synthesis will have to classify the
        document based on content alone.
        """

        content = await anyio.Path(path).read_text(encoding="utf-8")
        return Source(
            id=_content_id(content),
            type=SourceType.TEXT,
            path_or_url=str(path),
            content=content,
            metadata={"filename": path.name},
        )

    async def _ingest_pdf(self, path: Path) -> Source:
        """Extract text from a PDF with pypdf.

        pypdf is synchronous, so we run it in a worker thread to
        avoid blocking the event loop on multi-page documents.
        Layout information is discarded — we only need the text for
        LLM synthesis, and preserving layout adds cost without value
        for the current use cases (runbooks, postmortems, design docs).
        """

        def _extract() -> tuple[str, int]:
            reader = PdfReader(str(path))
            parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
            return "\n\n".join(parts), len(reader.pages)

        content, page_count = await anyio.to_thread.run_sync(_extract)
        return Source(
            id=_content_id(content),
            type=SourceType.PDF,
            path_or_url=str(path),
            content=content,
            metadata={"filename": path.name, "page_count": page_count},
        )

    async def ingest_signoz_incident(
        self, incident_dict: dict[str, Any]
    ) -> Source:
        """Normalize a SigNoz incident payload into a Source.

        We flatten the common fields into a human-readable markdown
        block so the synthesizer's prompt stays uniform across input
        types. The raw payload is preserved in metadata for callers
        that need structured access later.
        """

        incident_id = str(
            incident_dict.get("id")
            or incident_dict.get("incident_id")
            or incident_dict.get("alertId")
            or "unknown"
        )
        title = incident_dict.get("name") or incident_dict.get("title") or ""
        severity = incident_dict.get("severity") or incident_dict.get("priority")
        service = incident_dict.get("service") or incident_dict.get("labels", {}).get(
            "service"
        )
        started_at = incident_dict.get("startsAt") or incident_dict.get("created_at")
        description = (
            incident_dict.get("description")
            or incident_dict.get("annotations", {}).get("description")
            or ""
        )

        content_lines = [
            f"# Incident: {title}".rstrip(),
            "",
            f"- id: {incident_id}",
            f"- severity: {severity}" if severity else "",
            f"- service: {service}" if service else "",
            f"- started: {started_at}" if started_at else "",
            "",
            "## Description",
            "",
            description,
        ]
        content = "\n".join(line for line in content_lines if line is not None)

        return Source(
            id=f"signoz-{incident_id}",
            type=SourceType.SIGNOZ_INCIDENT,
            path_or_url=f"signoz://incident/{incident_id}",
            content=content,
            metadata={
                "incident_id": incident_id,
                "severity": severity,
                "service": service,
                "started_at": started_at,
                "raw": incident_dict,
            },
        )

    async def ingest_confluence_page(
        self, page_dict: dict[str, Any]
    ) -> Source:
        """Normalize a Confluence REST API page response into a Source.

        Confluence returns body in HTML-ish storage format; we extract
        the plain-text body if present and otherwise fall back to the
        full body blob. Structured metadata (space, version, url) is
        preserved for future diffing / link-back.
        """

        page_id = str(page_dict.get("id") or "unknown")
        title = page_dict.get("title") or ""
        body = page_dict.get("body") or {}

        # Confluence API v2 nests under body.storage.value or body.atlas_doc_format
        content = ""
        if isinstance(body, dict):
            for key in ("storage", "atlas_doc_format", "view", "plain"):
                section = body.get(key)
                if isinstance(section, dict) and section.get("value"):
                    content = str(section["value"])
                    break
        if not content:
            content = str(page_dict.get("content") or "")

        space_key = (page_dict.get("space") or {}).get("key") if isinstance(
            page_dict.get("space"), dict
        ) else page_dict.get("spaceId")
        version = (page_dict.get("version") or {}).get("number") if isinstance(
            page_dict.get("version"), dict
        ) else page_dict.get("version")
        url = (
            (page_dict.get("_links") or {}).get("webui")
            if isinstance(page_dict.get("_links"), dict)
            else page_dict.get("url")
        )

        header = f"# {title}\n\n" if title else ""
        full_content = f"{header}{content}"

        return Source(
            id=f"confluence-{page_id}",
            type=SourceType.CONFLUENCE_PAGE,
            path_or_url=url or f"confluence://page/{page_id}",
            content=full_content,
            metadata={
                "page_id": page_id,
                "title": title,
                "space": space_key,
                "version": version,
                "url": url,
                "raw": page_dict,
            },
        )
