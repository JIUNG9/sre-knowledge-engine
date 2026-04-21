"""Aegis CLI — ``aegis`` entry point.

Currently exposes emergency subcommands:

- ``aegis panic`` — trip the kill switch (and optionally revoke AWS creds).
- ``aegis status`` — inspect the current switch state.
- ``aegis release`` — clear the switch.

The CLI is Typer-based. The ``[project.scripts]`` block in ``pyproject.toml``
maps ``aegis`` to :func:`cli.main.app`.
"""

from __future__ import annotations

from cli.main import app

__all__ = ["app"]
