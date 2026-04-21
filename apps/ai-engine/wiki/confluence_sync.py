"""Sync Confluence pages into the LLM Wiki, flag stale ones, archive deleted ones.

Pulls every page in a Confluence Cloud space via REST API v2 (with pagination),
feeds each one through the Ingester + WikiEngine, and maintains a tracking
manifest so pages deleted upstream can be flagged ``archived`` locally instead
of silently disappearing from the vault.

Credential handling: tokens are wrapped in :class:`pydantic.SecretStr` so they
never leak into log output or error messages by accident. The caller is
responsible for passing a token with read-only scope on the target space.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, SecretStr

logger = logging.getLogger("aegis.wiki.sync")


# Default tracking paths under the vault. The _meta directory is the
# convention used across all sync modules so the Publisher can safely
# .gitignore it later if the user doesn't want sync state in git.
_META_DIR_NAME = "_meta"
_SYNCED_FILENAME = "confluence-synced.json"
_LOG_FILENAME = "confluence-sync-log.jsonl"

# Default vault root. Resolved per-call so tests can monkeypatch home.
_DEFAULT_VAULT_ROOT = Path("~/Documents/obsidian-sre").expanduser()

# httpx timeouts. Confluence pages with lots of embedded content can be
# slow to serialize on the server, so read timeout is generous.
_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)

# Rate-limit retry policy: SGI uses up to 3 attempts with exponential backoff
# starting at 2s. Confluence Cloud 429 responses include Retry-After in
# seconds; we honor that when present.
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 2.0


class ConfluenceConfig(BaseModel):
    """Connection + scheduling configuration for a single Confluence space."""

    base_url: str
    space_key: str
    api_token: SecretStr
    email: str
    sync_frequency: Literal["hourly", "daily", "weekly", "manual"] = "daily"


class ConfluenceSyncResult(BaseModel):
    """Summary of one sync pass — serializable so it can be logged / returned
    by the API router.
    """

    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    pages_fetched: int = 0
    pages_ingested: int = 0
    pages_flagged_stale: int = 0
    pages_deleted_upstream: int = 0
    errors: list[str] = Field(default_factory=list)


class ConfluenceSync:
    """Fetch → ingest → track pipeline for a Confluence space.

    One instance corresponds to one space. Callers that need to sync
    multiple spaces should construct multiple instances rather than
    mutating ``config`` between calls — it keeps the tracking JSON
    scoped per-space via the config's ``space_key``.
    """

    def __init__(
        self,
        config: ConfluenceConfig,
        engine: Any,
        ingester: Any,
        *,
        vault_root: Path | None = None,
    ) -> None:
        self.config = config
        self.engine = engine
        self.ingester = ingester
        self._vault_root = (vault_root or _DEFAULT_VAULT_ROOT).expanduser()
        self._meta_dir = self._vault_root / _META_DIR_NAME
        self._synced_path = self._meta_dir / _SYNCED_FILENAME
        self._log_path = self._meta_dir / _LOG_FILENAME

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _auth(self) -> tuple[str, str]:
        """Return the (email, token) tuple for httpx BasicAuth.

        Kept private so callers can't accidentally read the token off
        the instance.
        """

        return (self.config.email, self.config.api_token.get_secret_value())

    def _client(self) -> httpx.AsyncClient:
        """Construct an httpx client with sane timeouts + BasicAuth.

        Using a fresh client per call (rather than caching one on the
        instance) sidesteps the "event-loop-bound client" footgun when
        the same ConfluenceSync is reused across async tasks.
        """

        return httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            auth=self._auth(),
            headers={"Accept": "application/json"},
        )

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue a request with retry on 429 + transient 5xx.

        Auth failures (401/403) fail fast — retrying doesn't help, and
        the sooner we surface the error the sooner the user sees it in
        the sync log.
        """

        backoff = _INITIAL_BACKOFF_SECONDS
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.request(method, url, params=params)
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "confluence request error (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code in (401, 403):
                # Fail fast on auth — retries won't fix a bad token.
                raise httpx.HTTPStatusError(
                    f"confluence auth failed ({resp.status_code})",
                    request=resp.request,
                    response=resp,
                )
            if resp.status_code == 429 and attempt < _MAX_RETRIES:
                retry_after_header = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after_header) if retry_after_header else backoff
                except ValueError:
                    wait = backoff
                logger.warning(
                    "confluence rate limited; retrying in %.1fs (attempt %d/%d)",
                    wait,
                    attempt,
                    _MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                backoff *= 2
                continue
            if 500 <= resp.status_code < 600 and attempt < _MAX_RETRIES:
                logger.warning(
                    "confluence %d; retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    backoff,
                    attempt,
                    _MAX_RETRIES,
                )
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp

        # Should be unreachable — loop either returns or raises.
        raise RuntimeError(
            f"confluence request exhausted retries: {last_exc!r}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def test_connection(self) -> bool:
        """Return True if the credentials can list spaces.

        Hits ``/wiki/api/v2/spaces`` rather than the configured space
        specifically so a permission issue on a single space still
        surfaces as "connected but wrong key" rather than generic 401.
        """

        url = f"{self.config.base_url.rstrip('/')}/wiki/api/v2/spaces"
        try:
            async with self._client() as client:
                resp = await self._request_with_retry(
                    client, "GET", url, params={"limit": 1}
                )
            return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001 — summary for boolean result
            logger.warning("confluence test_connection failed: %s", exc)
            return False

    async def fetch_all_pages(self) -> list[dict[str, Any]]:
        """Fetch every page in the configured space, following pagination.

        Returns the raw page dicts (id, title, body.storage.value, version,
        metadata.labels). The ingester expects this exact shape.
        """

        base = self.config.base_url.rstrip("/")
        url = f"{base}/wiki/api/v2/spaces/{self.config.space_key}/pages"
        params: dict[str, Any] = {
            "limit": 100,
            "body-format": "storage",
        }

        pages: list[dict[str, Any]] = []
        async with self._client() as client:
            next_url: str | None = url
            next_params: dict[str, Any] | None = params
            while next_url:
                resp = await self._request_with_retry(
                    client, "GET", next_url, params=next_params
                )
                data = resp.json()
                for page in data.get("results", []) or []:
                    pages.append(page)
                # Confluence v2 returns _links.next as a path relative
                # to the Confluence host (starts with /wiki/...).
                links = data.get("_links") or {}
                next_rel = links.get("next")
                if next_rel:
                    # _links.next already starts with "/wiki/..." so we
                    # need just the scheme+host from base_url.
                    parsed = httpx.URL(base)
                    host_only = f"{parsed.scheme}://{parsed.host}"
                    if parsed.port:
                        host_only += f":{parsed.port}"
                    next_url = host_only + next_rel
                    next_params = None  # params are already in the next link
                else:
                    next_url = None

        logger.info(
            "fetched %d pages from confluence space %s",
            len(pages),
            self.config.space_key,
        )
        return pages

    async def sync(self) -> ConfluenceSyncResult:
        """Run one full sync: fetch, ingest, diff against last run, log."""

        result = ConfluenceSyncResult()

        try:
            pages = await self.fetch_all_pages()
        except Exception as exc:  # noqa: BLE001 — collected into result
            result.errors.append(f"fetch_all_pages: {exc!r}")
            self._append_log(result)
            return result

        result.pages_fetched = len(pages)

        current_ids: set[str] = set()
        for page in pages:
            page_id = str(page.get("id") or "")
            if not page_id:
                result.errors.append(
                    f"confluence page missing id: {page.get('title')!r}"
                )
                continue
            current_ids.add(page_id)
            try:
                source = await self.ingester.ingest_confluence_page(page)
                await self.engine.ingest(source)
                result.pages_ingested += 1
            except Exception as exc:  # noqa: BLE001 — per-page errors continue
                result.errors.append(
                    f"ingest page {page_id}: {exc!r}"
                )

        previously_synced = self._load_synced_ids()
        deleted_upstream = previously_synced - current_ids
        result.pages_deleted_upstream = len(deleted_upstream)
        # "Stale" here means any page we've seen before that's no longer
        # present — the UI surfaces these as "archived" so users can
        # decide whether to delete them from the vault manually.
        result.pages_flagged_stale = len(deleted_upstream)

        if deleted_upstream:
            logger.info(
                "confluence: %d pages removed upstream, flagging archived",
                len(deleted_upstream),
            )
            self._mark_archived(deleted_upstream)

        # Persist the current set for next run's diff.
        self._save_synced_ids(current_ids)
        self._append_log(result)
        return result

    # ------------------------------------------------------------------
    # Tracking state
    # ------------------------------------------------------------------
    def _load_synced_ids(self) -> set[str]:
        """Read the previously-synced page-id set from disk.

        Missing file returns empty set (first run). Corrupt file is
        logged + treated as empty rather than raising — a partial
        diff is preferable to blocking the whole sync.
        """

        if not self._synced_path.exists():
            return set()
        try:
            raw = self._synced_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            ids = data.get("ids") if isinstance(data, dict) else data
            return {str(x) for x in (ids or [])}
        except Exception as exc:  # noqa: BLE001 — graceful degrade
            logger.warning(
                "confluence tracking file unreadable, treating as empty: %s", exc
            )
            return set()

    def _save_synced_ids(self, ids: set[str]) -> None:
        """Persist the current set of synced page ids atomically-ish.

        We write to a temp file and rename so a crash mid-write can't
        leave a half-serialized JSON behind.
        """

        self._meta_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "space_key": self.config.space_key,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "ids": sorted(ids),
        }
        tmp = self._synced_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(self._synced_path)

    def _mark_archived(self, deleted_ids: set[str]) -> None:
        """Record deleted-upstream ids in a sidecar so the vault UI can
        surface them as ``freshness: archived``.

        We don't rewrite the page markdown here — that's the synthesizer's
        job once it sees the archive marker. This method just drops a
        breadcrumb.
        """

        self._meta_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self._meta_dir / "confluence-archived.json"
        try:
            existing: dict[str, Any] = {}
            if archive_path.exists():
                existing = json.loads(
                    archive_path.read_text(encoding="utf-8") or "{}"
                )
        except Exception:  # noqa: BLE001 — reset on corruption
            existing = {}
        archive_log: dict[str, Any] = existing.get("archived", {})
        stamp = datetime.now(timezone.utc).isoformat()
        for page_id in deleted_ids:
            archive_log.setdefault(page_id, {"archived_at": stamp})
        payload = {"archived": archive_log, "updated_at": stamp}
        archive_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _append_log(self, result: ConfluenceSyncResult) -> None:
        """Append a single JSONL record of this sync run.

        JSONL (one JSON object per line) is chosen over a rolling JSON
        array because appending a line doesn't require reading + re-
        writing the whole file — important if the vault's on slow disk
        or if many concurrent syncs happen.
        """

        self._meta_dir.mkdir(parents=True, exist_ok=True)
        record = result.model_dump(mode="json")
        record["space_key"] = self.config.space_key
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
