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

    # ---------------------------------------------------------------- #
    # Layer 1.5 / 1.6 — State Subscription + Invalidation
    # ---------------------------------------------------------------- #
    # Master kill switch. False (default) keeps the entire CDC + invalidation
    # plane out of the app lifespan, even if other knobs are misconfigured.
    # Operators flip this to True once they've reviewed the rollout.
    invalidation_enabled: bool = False

    # The Phase 2 rollout flag from the design doc. When False (default), the
    # engine logs every record but never mutates a wiki page or appends to the
    # resynth queue. Operators run two weeks of shadow-mode observation
    # before flipping this to True. Internally we pass `shadow_mode = not
    # invalidation_write_frontmatter` so there's exactly one switch to flip.
    invalidation_write_frontmatter: bool = False

    # Per-event fanout cap. Caps the number of dependent slugs marked per
    # event before the cap engages and reconciliation has to sweep the tail.
    # 1000 is the design-doc default; tune lower under bursty TF applies.
    invalidation_fanout_cap: int = 1000

    # Coalescing window for consume_with_batching. Events within this many
    # milliseconds of each other for the same artifact_id collapse to a
    # single fan-out. 100ms is the design-doc default; raise under heavy
    # ConfigMap flap, lower for incident-grade detection latency.
    invalidation_batch_window_ms: int = 100

    # Override paths. Defaults derive from wiki_vault_root.
    invalidation_log_path: Path | None = None
    invalidation_resynth_queue_path: Path | None = None

    # Kubernetes consumer scope.
    invalidation_k8s_namespaces: list[str] = ["default"]
    invalidation_k8s_tracked_kinds: list[str] = [
        "Deployment", "StatefulSet", "ConfigMap", "Secret"
    ]
    # Skip the Kubernetes consumer entirely. Useful when running the
    # ai-engine outside a cluster and not pointed at a kubeconfig — without
    # this knob we'd noisy-warn at every startup. Defaults to True so the
    # safe state is "do not try to talk to a cluster we may not have".
    invalidation_k8s_disabled: bool = True


settings = Settings()
