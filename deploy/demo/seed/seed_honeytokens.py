"""
Seed honeytokens into the demo Aegis vault.

Delegates to Layer 0.6's honeytoken seeder if available; otherwise
writes a minimal placeholder file into /var/lib/aegis/vault.

Usage:
    python seed_honeytokens.py [--vault /var/lib/aegis/vault]
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

HONEYTOKENS = [
    {"label": "demo-aws-key", "pattern": "AKIA", "note": "fake AWS key — triggers alert if used"},
    {"label": "demo-github-pat", "pattern": "ghp_", "note": "fake GitHub PAT"},
    {"label": "demo-slack-webhook", "pattern": "https://hooks.slack.com/services/", "note": "fake Slack webhook"},
    {"label": "demo-db-password", "pattern": "p@ssw0rd", "note": "obvious bait"},
    {"label": "demo-stripe-key", "pattern": "sk_live_", "note": "fake Stripe live key"},
]


def try_real_seeder(vault: Path) -> bool:
    """Try to call the real Layer 0.6 seeder if importable."""
    try:
        sys.path.insert(0, "/app")
        from services.honeytoken import seed_all_tokens  # type: ignore
        seed_all_tokens(vault_path=str(vault))
        print(f"[seed_honeytokens] used real Layer-0.6 seeder into {vault}")
        return True
    except Exception:
        return False


def fallback_seed(vault: Path) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    out = vault / "honeytokens.json"
    tokens = [
        {
            **t,
            "id": f"demo-{i}",
            "value": f"{t['pattern']}{secrets.token_hex(16)}",
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        for i, t in enumerate(HONEYTOKENS)
    ]
    out.write_text(json.dumps({"tokens": tokens}, indent=2))
    print(f"[seed_honeytokens] fallback seeded {len(tokens)} tokens into {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.environ.get("AEGIS_VAULT_PATH", "/var/lib/aegis/vault"))
    args = ap.parse_args()
    vault = Path(args.vault)

    if not try_real_seeder(vault):
        fallback_seed(vault)


if __name__ == "__main__":
    main()
