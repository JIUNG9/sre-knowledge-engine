"""Async HTTP client for the SigNoz query-service REST API.

This module is intentionally small. It owns:

* httpx ``AsyncClient`` lifecycle
* bearer-token auth
* exponential-backoff retries on transient failures (5xx, timeouts,
  connection errors) — hand-rolled, no ``tenacity`` dependency
* request-ID logging (a short uuid per outbound call, for correlation)
* normalization of ``httpx.HTTPStatusError`` into :class:`SigNozError`
  with useful attributes so callers don't have to parse httpx internals

Higher-level fetchers (:mod:`connectors.log_fetcher` etc.) are thin
wrappers that delegate HTTP work here.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx

from connectors.config import SigNozConnectorConfig


logger = logging.getLogger("aegis.connectors.signoz")


class SigNozError(Exception):
    """Raised for any non-2xx SigNoz API response or transport failure.

    Attributes:
        status_code: HTTP status code (0 for transport-level errors).
        method: HTTP method of the failing request.
        url: Fully-qualified URL of the failing request.
        body: Truncated response body (for diagnostics; may be empty).
        request_id: The Aegis-generated request id logged alongside the
            call. Useful when correlating against structured logs.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        method: str = "",
        url: str = "",
        body: str = "",
        request_id: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.url = url
        self.body = body
        self.request_id = request_id

    def __repr__(self) -> str:  # pragma: no cover — debug aid
        return (
            f"SigNozError(status={self.status_code}, method={self.method!r}, "
            f"url={self.url!r}, request_id={self.request_id!r})"
        )


# Status codes we retry. 429 is included because SigNoz Cloud rate-limits.
_RETRYABLE_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class SigNozClient:
    """Thin async wrapper over the SigNoz REST API.

    Use :meth:`from_config` for env-driven construction, or pass
    explicit values for tests. Always use as an async context manager
    (or call :meth:`aclose` explicitly) to release httpx connections.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        verify_tls: bool = True,
        timeout_seconds: int = 30,
        retry_attempts: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be >= 1")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.verify_tls = verify_tls
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts

        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            # SigNoz Cloud accepts Bearer tokens; self-hosted SigNoz also
            # accepts them when auth is enabled. Fetchers should not
            # override this header.
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout_seconds,
            verify=verify_tls,
            transport=transport,
        )

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_config(
        cls,
        config: SigNozConnectorConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> "SigNozClient":
        """Build a client from a :class:`SigNozConnectorConfig`.

        When ``config.use_mock=True`` the client is wired to the
        in-process mock server — no real network I/O is possible.
        """
        if config.use_mock and transport is None:
            # Local import avoids a circular dependency at module import
            # time (mock_server imports client fixtures).
            from connectors.mock_server import build_mock_transport

            transport = build_mock_transport()

        return cls(
            base_url=config.base_url,
            api_key=config.api_key,
            verify_tls=config.verify_tls,
            timeout_seconds=config.timeout_seconds,
            retry_attempts=config.retry_attempts,
            transport=transport,
        )

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "SigNozClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying httpx client."""
        await self._client.aclose()

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #
    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Issue a GET request and return the decoded JSON body."""
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Issue a POST request and return the decoded JSON body."""
        return await self._request("POST", path, json=json, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        request_id = uuid.uuid4().hex[:12]
        url_for_log = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            logger.debug(
                "signoz request start method=%s url=%s request_id=%s attempt=%d",
                method,
                url_for_log,
                request_id,
                attempt,
            )
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                logger.warning(
                    "signoz transport error method=%s url=%s request_id=%s "
                    "attempt=%d error=%s",
                    method,
                    url_for_log,
                    request_id,
                    attempt,
                    exc,
                )
                if attempt >= self.retry_attempts:
                    raise SigNozError(
                        f"transport error: {exc}",
                        status_code=0,
                        method=method,
                        url=url_for_log,
                        body="",
                        request_id=request_id,
                    ) from exc
                await self._sleep_backoff(attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS and attempt < self.retry_attempts:
                logger.warning(
                    "signoz retryable status method=%s url=%s request_id=%s "
                    "attempt=%d status=%d",
                    method,
                    url_for_log,
                    request_id,
                    attempt,
                    response.status_code,
                )
                await self._sleep_backoff(attempt)
                continue

            if response.is_error:
                body_text = _truncate(response.text)
                logger.error(
                    "signoz error response method=%s url=%s request_id=%s "
                    "status=%d body=%s",
                    method,
                    url_for_log,
                    request_id,
                    response.status_code,
                    body_text,
                )
                raise SigNozError(
                    f"{method} {path} returned {response.status_code}",
                    status_code=response.status_code,
                    method=method,
                    url=url_for_log,
                    body=body_text,
                    request_id=request_id,
                )

            logger.debug(
                "signoz request ok method=%s url=%s request_id=%s status=%d",
                method,
                url_for_log,
                request_id,
                response.status_code,
            )
            try:
                return response.json()
            except ValueError as exc:
                raise SigNozError(
                    f"non-JSON response: {exc}",
                    status_code=response.status_code,
                    method=method,
                    url=url_for_log,
                    body=_truncate(response.text),
                    request_id=request_id,
                ) from exc

        # Fallthrough — should only happen if retry_attempts=0, which we
        # already reject in __init__. Keep a clear error just in case.
        raise SigNozError(
            f"retry loop exhausted: {last_exc}",
            method=method,
            url=url_for_log,
            request_id=request_id,
        )

    async def _sleep_backoff(self, attempt: int) -> None:
        """Exponential backoff with small jitter (0.25s, 0.5s, 1s ...)."""
        base = 0.25 * (2 ** (attempt - 1))
        await asyncio.sleep(base + random.uniform(0, 0.05))


def _truncate(text: str, limit: int = 512) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


# --------------------------------------------------------------------------- #
# Convenience
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def signoz_client(
    config: SigNozConnectorConfig,
) -> AsyncIterator[SigNozClient]:
    """Shortcut async context manager for scripts/tests.

    Example::

        async with signoz_client(cfg) as client:
            data = await client.get("/api/v1/rules")
    """
    client = SigNozClient.from_config(config)
    try:
        yield client
    finally:
        await client.aclose()
