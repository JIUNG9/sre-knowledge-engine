"""``aegis panic`` / ``aegis status`` / ``aegis release`` commands.

Design notes:

- ``panic`` is the loudest command: it requires an operator name and a reason
  before it will trip the switch. ``--force`` bypasses the interactive "type
  PANIC to confirm" prompt (useful for PagerDuty webhooks / CI).
- AWS session revocation is **explicit opt-in only** — either via
  ``AEGIS_KILLSWITCH_REVOKE_AWS_ON_PANIC=true`` + ``AEGIS_KILLSWITCH_AWS_ROLE_ARN``,
  or via the ``--revoke-aws`` / ``--aws-role-arn`` flags.
- The commands print a human-friendly summary; the structured event is
  already in the audit log via :class:`KillSwitch`.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from killswitch.aws_revoke import revoke_aws_session
from killswitch.config import KillSwitchConfig
from killswitch.switch import KillSwitch

CONFIRM_TOKEN = "PANIC"


def _build_switch(
    redis_url: Optional[str],
    backend: Optional[str],
) -> KillSwitch:
    """Construct a :class:`KillSwitch` honoring CLI overrides."""
    base = KillSwitchConfig()
    overrides: dict = {}
    if redis_url:
        overrides["redis_url"] = redis_url
    if backend:
        overrides["backend"] = backend
    if overrides:
        data = base.model_dump()
        data.update(overrides)
        cfg = KillSwitchConfig(**data)
    else:
        cfg = base
    return KillSwitch(cfg)


def panic_command(
    operator: Optional[str] = typer.Option(
        None,
        "--operator",
        "-o",
        help="Who is tripping the switch (recorded in audit log).",
    ),
    reason: Optional[str] = typer.Option(
        None,
        "--reason",
        "-r",
        help="Why the switch is being tripped.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip the interactive 'type PANIC to confirm' prompt.",
    ),
    revoke_aws: bool = typer.Option(
        False,
        "--revoke-aws",
        help="Also attach a Deny-all inline policy to the configured AWS role.",
    ),
    aws_role_arn: Optional[str] = typer.Option(
        None,
        "--aws-role-arn",
        help="IAM role ARN to revoke. Defaults to config.aws_role_arn.",
    ),
    redis_url: Optional[str] = typer.Option(
        None,
        "--redis-url",
        help="Override AEGIS_KILLSWITCH_REDIS_URL.",
    ),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        help="Force 'redis' or 'file' backend.",
    ),
) -> None:
    """Trip the kill switch, stopping every MCP tool call immediately."""
    switch = _build_switch(redis_url, backend)

    if not force:
        typer.secho(
            "*** AEGIS KILL SWITCH — EMERGENCY STOP ***",
            fg=typer.colors.RED,
            bold=True,
        )
        typer.echo(
            "This will immediately block every MCP tool call across the fleet."
        )
        confirm = typer.prompt(f"Type '{CONFIRM_TOKEN}' to confirm")
        if confirm.strip() != CONFIRM_TOKEN:
            typer.secho("Aborted — confirmation token did not match.",
                        fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)

    if not operator:
        operator = typer.prompt("Operator name (e.g. june.gu)")
    if not reason:
        reason = typer.prompt("Reason for tripping the switch")

    operator = (operator or "").strip()
    reason = (reason or "").strip()
    if not operator or not reason:
        typer.secho(
            "Operator and reason are both required. Aborted.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    status = switch.trip(reason=reason, operator=operator)
    typer.secho(
        f"\nKILL SWITCH TRIPPED (backend={status.backend})",
        fg=typer.colors.RED,
        bold=True,
    )
    typer.echo(f"  operator:   {status.operator}")
    typer.echo(f"  reason:     {status.reason}")
    typer.echo(f"  tripped_at: {status.tripped_at}")

    # AWS revocation — explicit opt-in from either flag or config.
    want_revoke = revoke_aws or switch.config.revoke_aws_on_panic
    if want_revoke:
        role = aws_role_arn or switch.config.aws_role_arn
        if not role:
            typer.secho(
                "\n[warn] AWS revocation requested but no role ARN configured. "
                "Pass --aws-role-arn or set AEGIS_KILLSWITCH_AWS_ROLE_ARN.",
                fg=typer.colors.YELLOW,
            )
        else:
            try:
                result = revoke_aws_session(role)
                typer.secho(
                    f"\nAWS session revoked on {result['role_name']}",
                    fg=typer.colors.MAGENTA,
                    bold=True,
                )
                typer.echo(f"  policy:         {result['policy_name']}")
                typer.echo(f"  issued_before:  {result['issued_before']}")
            except Exception as exc:  # noqa: BLE001 — log + continue
                typer.secho(
                    f"\n[error] AWS revocation failed: {exc}",
                    fg=typer.colors.RED,
                )
                # We still exit 0 — the switch trip itself succeeded.

    typer.echo("\nRun `aegis release` to resume agent operations.")


def status_command(
    redis_url: Optional[str] = typer.Option(None, "--redis-url"),
    backend: Optional[str] = typer.Option(None, "--backend"),
    as_json: bool = typer.Option(
        False, "--json", help="Emit JSON instead of a human-readable summary."
    ),
) -> None:
    """Print the current kill-switch status."""
    switch = _build_switch(redis_url, backend)
    status = switch.status()

    if as_json:
        typer.echo(json.dumps(status.to_dict(), indent=2))
        raise typer.Exit(code=1 if status.active else 0)

    if status.active:
        typer.secho("ACTIVE", fg=typer.colors.RED, bold=True)
        typer.echo(f"  backend:    {status.backend}")
        typer.echo(f"  operator:   {status.operator or '(unknown)'}")
        typer.echo(f"  reason:     {status.reason or '(unknown)'}")
        typer.echo(f"  tripped_at: {status.tripped_at or '(unknown)'}")
        raise typer.Exit(code=1)

    typer.secho("CLEAR", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  backend: {status.backend}")


def release_command(
    operator: Optional[str] = typer.Option(
        None,
        "--operator",
        "-o",
        help="Who is releasing the switch (audit log).",
    ),
    force: bool = typer.Option(False, "--force", "-f"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url"),
    backend: Optional[str] = typer.Option(None, "--backend"),
) -> None:
    """Release the kill switch so the agent can resume."""
    switch = _build_switch(redis_url, backend)
    if not operator:
        operator = typer.prompt("Operator name (e.g. june.gu)")
    operator = (operator or "").strip()
    if not operator:
        typer.secho("Operator required.", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    if not force:
        confirm = typer.confirm(
            f"Release the kill switch as '{operator}'? This will re-enable MCP tools.",
            default=False,
        )
        if not confirm:
            typer.secho("Aborted.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)

    status = switch.release(operator=operator)
    typer.secho("Kill switch RELEASED.", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  backend: {status.backend}")


# Re-export for testability: lets tests import the command callables directly.
__all__ = ["panic_command", "release_command", "status_command"]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0)
