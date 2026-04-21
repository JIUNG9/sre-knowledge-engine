"""Configuration for the Aegis AI Engine.

Uses pydantic-settings to load configuration from environment variables
and .env files. All settings can be overridden via environment variables
prefixed with AEGIS_ (e.g., AEGIS_ANTHROPIC_API_KEY).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-4-6"
    api_port: int = 8000
    debug: bool = False

    # Wiki
    wiki_vault_root: Path = Path.home() / "Documents" / "obsidian-sre"
    wiki_stale_threshold_days: int = 30
    wiki_archive_threshold_days: int = 180
    wiki_synthesis_model: str = "claude-haiku-4-5-20251001"
    wiki_contradiction_model: str = "claude-sonnet-4-6"

    # Confluence (optional — empty means disabled)
    confluence_base_url: str = ""
    confluence_space_key: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""

    # SigNoz (optional)
    signoz_base_url: str = ""
    signoz_api_key: str = ""
    signoz_lookback_days: int = 30

    # Wiki publisher — per-deployment, supply via env vars or override.
    # Defaults are intentionally generic so strangers cloning the repo do
    # not accidentally publish under the upstream author's identity.
    wiki_remote_url: str = ""
    wiki_git_author_name: str = "Aegis Bot"
    wiki_git_author_email: str = "aegis-bot@localhost"
    wiki_auto_push: bool = False


settings = Settings()
