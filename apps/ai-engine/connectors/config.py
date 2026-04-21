"""Configuration for the SigNoz connector.

Values are loaded from environment variables prefixed with
``AEGIS_SIGNOZ_`` (e.g. ``AEGIS_SIGNOZ_BASE_URL``). The connector is
deliberately small — if you need more knobs, push them into the
:class:`connectors.signoz_client.SigNozClient` at construction time.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class SigNozConnectorConfig(BaseSettings):
    """Runtime configuration for :class:`~connectors.signoz_client.SigNozClient`.

    Attributes:
        base_url: SigNoz query-service URL. Default matches the upstream
            docker-compose port.
        api_key: Optional bearer token. When empty, requests are sent
            without an ``Authorization`` header.
        verify_tls: Disable only for local self-signed stacks.
        timeout_seconds: Per-request timeout.
        retry_attempts: Total attempts (not retries-after-first). Must
            be >= 1. Transient 5xx and network errors are retried with
            exponential backoff; 4xx is surfaced immediately.
        use_mock: When True, :meth:`SigNozClient.from_config` returns a
            client wired to the in-process mock server — no network I/O.
    """

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_SIGNOZ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "http://localhost:3301"
    api_key: str | None = None
    verify_tls: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 3
    use_mock: bool = False
