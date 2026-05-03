"""Reverse index: ``artifact_id -> set of WikiPage slugs``.

Built once at vault load by walking every page's
:attr:`wiki.synthesizer.WikiPage.config_dependencies`. Updated
incrementally whenever the synthesizer writes a page (the
:class:`WikiEngine` calls :meth:`upsert_page` after a successful save).

We hold a single :class:`asyncio.Lock` for the whole index because
writes are rare (1-10/sec at most, when the synthesizer is busy) and
reads are tiny (one dict lookup). A more granular lock would buy
nothing and complicate reasoning about consistency.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from wiki.synthesizer import WikiPage


class DependencyIndex:
    """Reverse index from ``ConfigDependency.artifact_id`` to wiki slugs.

    Use :meth:`rebuild` once at vault load, :meth:`upsert_page` on every
    page write, and :meth:`lookup` from the invalidation engine. All
    methods are coroutine-safe — callers don't need to grab a lock.
    """

    def __init__(self) -> None:
        self._index: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def rebuild(self, pages: Iterable[WikiPage]) -> None:
        """Drop and rebuild the index from the supplied page list.

        Used at vault load and from the API for forced rebuilds. Pages
        with no ``config_dependencies`` are silently skipped — that's
        the dominant case (concept pages have no infra dependencies).
        """

        async with self._lock:
            self._index.clear()
            for page in pages:
                for dep in page.config_dependencies:
                    self._index.setdefault(dep.artifact_id, set()).add(page.slug)

    async def lookup(self, artifact_id: str) -> set[str]:
        """Return a copy of the slug set for ``artifact_id``.

        Returns the empty set when no pages depend on it — invalidation
        still logs that case so the audit log is exhaustive.
        """

        async with self._lock:
            return set(self._index.get(artifact_id, ()))

    async def upsert_page(self, page: WikiPage) -> None:
        """Refresh the index for one page after a write.

        We strip the slug from every artifact bucket first (the page may
        have removed dependencies it used to claim) and then re-insert
        from the current ``page.config_dependencies``. The cost is O(N)
        in the number of distinct artifact_ids — small in practice.
        """

        async with self._lock:
            # Remove existing references to this slug.
            empty_keys: list[str] = []
            for artifact_id, slugs in self._index.items():
                slugs.discard(page.slug)
                if not slugs:
                    empty_keys.append(artifact_id)
            for k in empty_keys:
                self._index.pop(k, None)
            # Re-insert under current dependencies.
            for dep in page.config_dependencies:
                self._index.setdefault(dep.artifact_id, set()).add(page.slug)

    async def remove_page(self, slug: str) -> None:
        """Drop ``slug`` from every bucket — call this on page deletion."""

        async with self._lock:
            empty_keys: list[str] = []
            for artifact_id, slugs in self._index.items():
                slugs.discard(slug)
                if not slugs:
                    empty_keys.append(artifact_id)
            for k in empty_keys:
                self._index.pop(k, None)

    async def snapshot(self) -> dict[str, set[str]]:
        """Return a deep copy of the index for diagnostics / dashboards."""

        async with self._lock:
            return {k: set(v) for k, v in self._index.items()}
