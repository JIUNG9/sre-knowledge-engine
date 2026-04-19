"""Sync SigNoz alert history + resolved incidents into the LLM Wiki.

SigNoz exposes its alert rules + firing state under ``/api/v1/alerts`` and
individual rule definitions under ``/api/v1/rules/{id}``. We pull resolved
incidents in a lookback window, enrich each one with its rule definition
(the query / threshold that fired), and hand the merged dict off to the
Ingester so the synthesizer can turn it into a postmortem-style page.

Deduplication is handled by the ``signoz-synced.json`` manifest — rerunning
a sync won't re-ingest the same incident twice unless the incident_id
changes on SigNoz's side.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, SecretStr

logger = logging.getLogger("aegis.wiki.sync")


_META_DIR_NAME = "_meta"
_SYNCED_FILENAME = "signoz-synced.json"
_LOG_FILENAME = "signoz-sync-log.jsonl"

_DEFAULT_VAULT_ROOT = Path("~/Documents/obsidian-sre").expanduser()

_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)

_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 2.0


class SignozConfig(BaseModel):
    """Connection + scheduling configuration for a SigNoz instance."""

    base_url: str
    api_key: SecretStr
    sync_frequency: Literal["hourly", "daily", "manual"] = "hourly"
    lookback_days: int = 30


class SignozSyncResult(BaseModel):
    """One-pass sync summary; same shape style as ConfluenceSyncResult so
    the API router can handle both with a common Pydantic discriminator.
    """

    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    alerts_fetched: int = 0
    incidents_ingested: int = 0
    errors: list[str] = Field(default_factory=list)


class SignozSync:
    """Fetch → filter → enrich → ingest pipeline for SigNoz incidents."""

    def __init__(
        self,
        config: SignozConfig,
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
    def _headers(self) -> dict[str, str]:
        """SigNoz uses a header-based API key rather than Bearer/Basic.

        The format is ``SIGNOZ-API-KEY <token>`` — documented at
        https://signoz.io/docs/userguide/alerts-management/.
        """

        return {
            "Authorization": f"SIGNOZ-API-KEY {self.config.api_key.get_secret_value()}",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            headers=self._headers(),
        )

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Retry policy mirrors ConfluenceSync — see that module's
        docstring. Kept as two implementations rather than a shared
        helper because the auth model is different and the error
        envelopes differ enough that a generic helper would muddy
        error messages.
        """

        backoff = _INITIAL_BACKOFF_SECONDS
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.request(method, url, params=params)
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "signoz request error (attempt %d/%d): %s",
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
                raise httpx.HTTPStatusError(
                    f"signoz auth failed ({resp.status_code})",
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
                    "signoz rate limited; retrying in %.1fs (attempt %d/%d)",
                    wait,
                    attempt,
                    _MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                backoff *= 2
                continue
            if 500 <= resp.status_code < 600 and attempt < _MAX_RETRIES:
                logger.warning(
                    "signoz %d; retrying in %.1fs (attempt %d/%d)",
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

        raise RuntimeError(f"signoz request exhausted retries: {last_exc!r}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def test_connection(self) -> bool:
        """Return True if ``/api/v1/alerts`` responds 200 with the key.

        We don't care about the body; we care that auth is valid and
        the host is reachable.
        """

        url = f"{self.config.base_url.rstrip('/')}/api/v1/alerts"
        try:
            async with self._client() as client:
                resp = await self._request_with_retry(client, "GET", url)
            return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001 — boolean summary
            logger.warning("signoz test_connection failed: %s", exc)
            return False

    async def fetch_alerts(self, hours: int) -> list[dict[str, Any]]:
        """Fetch all alerts seen in the last ``hours`` hours.

        SigNoz's alerts endpoint returns the current alert state plus
        recent history; callers filter for resolved vs firing downstream.
        """

        base = self.config.base_url.rstrip("/")
        url = f"{base}/api/v1/alerts"
        # SigNoz supports ?active=true/false and time range params in
        # later API revisions; we pass the full list and filter client-
        # side to stay compatible across versions.
        async with self._client() as client:
            resp = await self._request_with_retry(client, "GET", url)
        body = resp.json()
        # API sometimes wraps in {"status": "success", "data": [...]}
        if isinstance(body, dict):
            alerts = body.get("data") or body.get("alerts") or []
        else:
            alerts = body
        if not isinstance(alerts, list):
            alerts = []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        filtered: list[dict[str, Any]] = []
        for alert in alerts:
            ts_raw = (
                alert.get("updatedAt")
                or alert.get("startsAt")
                or alert.get("created_at")
            )
            if not ts_raw:
                # If we can't tell when it happened, keep it — better
                # to ingest than to silently drop.
                filtered.append(alert)
                continue
            try:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            except ValueError:
                filtered.append(alert)
                continue
            if ts >= cutoff:
                filtered.append(alert)

        logger.info(
            "signoz: fetched %d alerts, %d within last %dh",
            len(alerts),
            len(filtered),
            hours,
        )
        return filtered

    async def fetch_resolved_incidents(self, days: int) -> list[dict[str, Any]]:
        """Return resolved incidents in the lookback window, enriched
        with their rule definitions.

        An incident is "resolved" when:
          - ``state`` is ``inactive`` / ``resolved`` / ``ok``, OR
          - ``resolved_at`` / ``endsAt`` is populated.
        """

        hours = days * 24
        alerts = await self.fetch_alerts(hours)
        resolved: list[dict[str, Any]] = []
        for alert in alerts:
            state = (
                alert.get("state")
                or alert.get("status")
                or alert.get("labels", {}).get("alertstate")
            )
            resolved_at = (
                alert.get("resolved_at")
                or alert.get("resolvedAt")
                or alert.get("endsAt")
            )
            is_resolved = (
                isinstance(state, str)
                and state.lower() in {"inactive", "resolved", "ok"}
            ) or bool(resolved_at)
            if is_resolved:
                resolved.append(alert)

        # Enrich with rule definition so the synthesizer has the
        # actual query / threshold, not just the firing metadata.
        base = self.config.base_url.rstrip("/")
        enriched: list[dict[str, Any]] = []
        async with self._client() as client:
            for alert in resolved:
                rule_id = (
                    alert.get("ruleId")
                    or alert.get("rule_id")
                    or alert.get("id")
                )
                if rule_id:
                    rule_url = f"{base}/api/v1/rules/{rule_id}"
                    try:
                        rule_resp = await self._request_with_retry(
                            client, "GET", rule_url
                        )
                        rule_body = rule_resp.json()
                        rule_def = (
                            rule_body.get("data")
                            if isinstance(rule_body, dict)
                            else rule_body
                        ) or rule_body
                        alert = {**alert, "rule_definition": rule_def}
                    except Exception as exc:  # noqa: BLE001 — partial ok
                        logger.debug(
                            "signoz rule enrich failed for %s: %s",
                            rule_id,
                            exc,
                        )
                enriched.append(alert)

        logger.info(
            "signoz: %d resolved incidents over %d days (enriched)",
            len(enriched),
            days,
        )
        return enriched

    async def sync(self) -> SignozSyncResult:
        """Fetch + deduplicate + ingest resolved incidents."""

        result = SignozSyncResult()
        try:
            incidents = await self.fetch_resolved_incidents(
                self.config.lookback_days
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"fetch_resolved_incidents: {exc!r}")
            self._append_log(result)
            return result

        result.alerts_fetched = len(incidents)

        already_ingested = self._load_synced_ids()
        new_ids: set[str] = set(already_ingested)

        for incident in incidents:
            incident_id = str(
                incident.get("id")
                or incident.get("incident_id")
                or incident.get("alertId")
                or ""
            )
            if not incident_id:
                result.errors.append(
                    f"signoz incident missing id: {incident.get('name')!r}"
                )
                continue
            if incident_id in already_ingested:
                continue
            try:
                source = await self.ingester.ingest_signoz_incident(incident)
                await self.engine.ingest(source)
                result.incidents_ingested += 1
                new_ids.add(incident_id)
            except Exception as exc:  # noqa: BLE001
                result.errors.append(
                    f"ingest incident {incident_id}: {exc!r}"
                )

        self._save_synced_ids(new_ids)
        self._append_log(result)
        return result

    # ------------------------------------------------------------------
    # Tracking state
    # ------------------------------------------------------------------
    def _load_synced_ids(self) -> set[str]:
        if not self._synced_path.exists():
            return set()
        try:
            raw = self._synced_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            ids = data.get("ids") if isinstance(data, dict) else data
            return {str(x) for x in (ids or [])}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "signoz tracking file unreadable, treating as empty: %s", exc
            )
            return set()

    def _save_synced_ids(self, ids: set[str]) -> None:
        self._meta_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "ids": sorted(ids),
        }
        tmp = self._synced_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(self._synced_path)

    def _append_log(self, result: SignozSyncResult) -> None:
        self._meta_dir.mkdir(parents=True, exist_ok=True)
        record = result.model_dump(mode="json")
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
