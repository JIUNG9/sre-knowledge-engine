"""Read-scope tool: check_doc_links.

Validates internal + external links in a single document.

External URLs are probed with HEAD requests, a 3-second timeout by
default, and honour robots.txt (``Disallow: /`` blocks the request and
the link is returned with ``status=skipped_robots``).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from mcp.scoped_tool import scoped_tool
from reconciliation.models import LinkCheckResult, LinkReport
from reconciliation.sources import extract_links

from . import _docs_runtime as runtime

logger = logging.getLogger("aegis.mcp.docs_link_check")


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "string",
            "description": (
                "Fully qualified doc id in the form 'source:local_id' "
                "(e.g. 'obsidian:runbooks/db.md', 'confluence:12345')."
            ),
        },
        "timeout_s": {
            "type": "number",
            "description": "Per-request HTTP timeout in seconds (default 3).",
            "default": 3.0,
            "minimum": 0.1,
            "maximum": 15.0,
        },
        "respect_robots": {
            "type": "boolean",
            "description": "Honour robots.txt conventions (default True).",
            "default": True,
        },
    },
    "required": ["doc_id"],
}


_USER_AGENT = "Aegis-Reconciler/1.0 (+https://github.com/aegis)"


@scoped_tool("read")
def check_doc_links(
    doc_id: str,
    timeout_s: float = 3.0,
    respect_robots: bool = True,
) -> dict:
    """Validate every link in the document identified by ``doc_id``."""
    reconciler = runtime.get_reconciler()
    if ":" not in doc_id:
        return {
            "status": "error",
            "tool": "check_doc_links",
            "error": (
                "doc_id must be 'source:local_id' (e.g. 'obsidian:runbooks/db.md')"
            ),
        }
    source_name, _, local_id = doc_id.partition(":")
    src = next((s for s in reconciler.sources if s.name == source_name), None)
    if src is None:
        return {
            "status": "error",
            "tool": "check_doc_links",
            "error": f"unknown source: {source_name}",
            "available_sources": [s.name for s in reconciler.sources],
        }
    doc = src.fetch(local_id)
    if doc is None:
        return {
            "status": "error",
            "tool": "check_doc_links",
            "error": f"doc not found: {doc_id}",
        }

    internal, external = extract_links(doc.body or "")
    report = LinkReport(
        doc_id=doc.id,
        source=doc.source,
        internal_links=internal,
        external_links=external,
    )

    # Internal links — mark as unchecked; reconciling against other
    # sources is out of scope for link_check. This preserves the list
    # so the caller can decide.
    for link in internal:
        report.checked.append(
            LinkCheckResult(
                url=link,
                status="unchecked",
                reason="internal link (resolve via find_docs)",
            )
        )

    # External links
    client = httpx.Client(
        timeout=timeout_s,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )
    robots_cache: dict[str, RobotFileParser | None] = {}
    try:
        for url in external:
            report.checked.append(
                _probe(client, url, respect_robots=respect_robots, cache=robots_cache)
            )
    finally:
        client.close()

    return {
        "status": "success",
        "tool": "check_doc_links",
        "doc_id": doc_id,
        "broken_count": report.broken_count,
        "report": report.model_dump(mode="json"),
    }


check_doc_links.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


def _probe(
    client: httpx.Client,
    url: str,
    *,
    respect_robots: bool,
    cache: dict[str, RobotFileParser | None],
) -> LinkCheckResult:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return LinkCheckResult(url=url, status="broken", reason="malformed url")

    if respect_robots and not _robots_allowed(client, parsed, cache):
        return LinkCheckResult(
            url=url,
            status="skipped_robots",
            reason="robots.txt disallows this path",
        )

    try:
        resp = client.head(url)
        # Some servers don't implement HEAD — fall back to a tiny GET.
        if resp.status_code == 405:
            resp = client.get(url)
        if 200 <= resp.status_code < 400:
            return LinkCheckResult(url=url, status="ok", http_status=resp.status_code)
        return LinkCheckResult(
            url=url,
            status="broken",
            http_status=resp.status_code,
            reason=f"HTTP {resp.status_code}",
        )
    except httpx.TimeoutException as exc:
        return LinkCheckResult(url=url, status="timeout", reason=str(exc))
    except httpx.RequestError as exc:
        return LinkCheckResult(url=url, status="broken", reason=str(exc))


def _robots_allowed(
    client: httpx.Client,
    parsed: Any,
    cache: dict[str, RobotFileParser | None],
) -> bool:
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in cache:
        robots_url = f"{base}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            resp = client.get(robots_url)
            if resp.status_code >= 400:
                cache[base] = None  # No robots.txt — allow
                return True
            parser.parse(resp.text.splitlines())
            cache[base] = parser
        except httpx.RequestError:
            cache[base] = None  # Treat fetch failure as permissive
            return True
    parser = cache[base]
    if parser is None:
        return True
    return parser.can_fetch(_USER_AGENT, parsed.geturl())


__all__ = ["check_doc_links", "INPUT_SCHEMA"]
