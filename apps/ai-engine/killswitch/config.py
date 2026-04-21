"""Kill switch configuration.

Pydantic ``BaseSettings`` subclass — loads from environment variables prefixed
with ``AEGIS_KILLSWITCH_`` or from the process ``.env`` file.

Examples:
    AEGIS_KILLSWITCH_REDIS_URL=redis://redis.internal:6379/0
    AEGIS_KILLSWITCH_BACKEND=redis
    AEGIS_KILLSWITCH_REVOKE_AWS_ON_PANIC=true
    AEGIS_KILLSWITCH_AWS_ROLE_ARN=arn:aws:iam::123456789012:role/aegis-agent
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KillSwitchConfig(BaseSettings):
    """Configuration for the Aegis kill switch.

    Attributes:
        redis_url: Redis connection URL used by the ``redis`` backend.
        backend: Preferred backend. ``redis`` is default; ``file`` is the
            local fallback used when Redis is unreachable or in tests.
        revoke_aws_on_panic: If ``True``, ``aegis panic`` will additionally
            attach a ``Deny *`` inline policy to ``aws_role_arn``.
        aws_role_arn: IAM role ARN of the agent's active credentials. Required
            when ``revoke_aws_on_panic`` is ``True``.
        state_key: Redis key (and file name) used to store the active flag.
        audit_log_path: JSONL file for trip/release audit trail.
        file_backend_path: On-disk flag file for the ``file`` backend.
    """

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_KILLSWITCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str = "redis://localhost:6379"
    backend: Literal["redis", "file"] = "redis"
    revoke_aws_on_panic: bool = False
    aws_role_arn: str | None = None

    state_key: str = "aegis:killswitch"
    audit_log_path: Path = Field(default_factory=lambda: Path("./aegis-audit.jsonl"))
    file_backend_path: Path = Field(
        default_factory=lambda: Path("./aegis-killswitch.flag")
    )
