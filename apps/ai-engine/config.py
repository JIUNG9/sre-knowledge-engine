"""Configuration for the Aegis AI Engine.

Uses pydantic-settings to load configuration from environment variables
and .env files. All settings can be overridden via environment variables
prefixed with AEGIS_ (e.g., AEGIS_ANTHROPIC_API_KEY).
"""

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


settings = Settings()
