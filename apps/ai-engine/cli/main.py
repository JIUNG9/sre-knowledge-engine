"""Typer app wiring for the ``aegis`` CLI.

The app is intentionally tiny — each subcommand lives in its own module so
the CLI surface can grow without a single mega-file. Today we only wire the
panic/status/release triad from Layer 0.3.
"""

from __future__ import annotations

import typer

from cli.panic import panic_command, release_command, status_command

app = typer.Typer(
    name="aegis",
    help="Aegis — AI-Native DevSecOps Command Center CLI.",
    no_args_is_help=True,
    add_completion=False,
)

app.command(name="panic", help="Trip the Aegis kill switch (emergency stop).")(
    panic_command
)
app.command(name="status", help="Show the current kill-switch status.")(
    status_command
)
app.command(name="release", help="Release the kill switch and resume agent ops.")(
    release_command
)


def run() -> None:
    """Entry point for console scripts."""
    app()


if __name__ == "__main__":  # pragma: no cover
    run()
