"""SQLite-backed registry for honey tokens.

The registry stores token metadata and the rendered token value. Because
the DB file itself is sensitive (whoever reads it learns the traps),
only WARNING-level messages are emitted and values are never logged.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterable, List, Optional

from .config import get_config

if TYPE_CHECKING:  # avoid circular import at runtime
    from .generator import HoneyToken

log = logging.getLogger("aegis.honeytokens.registry")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS honey_tokens (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    marker TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL,
    created_at REAL NOT NULL,
    seeded_locations TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_honey_category ON honey_tokens(category);
CREATE INDEX IF NOT EXISTS idx_honey_marker ON honey_tokens(marker);
"""


class HoneyTokenRegistry:
    """Thread-safe SQLite registry for honey tokens."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or get_config().registry_path
        self._lock = threading.RLock()
        parent = os.path.dirname(os.path.abspath(self._path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @property
    def path(self) -> str:
        return self._path

    @contextmanager
    def _connect(self):
        # `check_same_thread=False` paired with an RLock lets us share the
        # registry across FastAPI worker threads without per-call overhead.
        conn = sqlite3.connect(self._path, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------ CRUD

    def insert(self, token: "HoneyToken") -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO honey_tokens
                    (id, category, value, marker, fingerprint,
                     created_at, seeded_locations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token.id,
                    token.category,
                    token.value,
                    token.marker,
                    token.fingerprint,
                    token.created_at,
                    "\n".join(token.seeded_locations),
                ),
            )
            conn.commit()
        # Deliberately NO info-level log of the value.
        log.warning("honey token persisted id=%s category=%s", token.id, token.category)

    def all_markers(self) -> List[str]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT marker FROM honey_tokens").fetchall()
            return [r[0] for r in rows]

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM honey_tokens").fetchone()[0])

    def get_by_marker(self, marker: str) -> Optional[dict]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id, category, value, marker, fingerprint, created_at, "
                "seeded_locations FROM honey_tokens WHERE marker = ?",
                (marker,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "category": row[1],
                "value": row[2],
                "marker": row[3],
                "fingerprint": row[4],
                "created_at": row[5],
                "seeded_locations": [p for p in (row[6] or "").split("\n") if p],
            }

    def list_metadata(self) -> List[dict]:
        """Return metadata WITHOUT values. Safe for admin UI."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, category, marker, fingerprint, created_at, "
                "seeded_locations FROM honey_tokens ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0],
                "category": r[1],
                "marker": r[2],
                "fingerprint": r[3],
                "created_at": r[4],
                "seeded_locations": [p for p in (r[5] or "").split("\n") if p],
            }
            for r in rows
        ]

    def add_seeded_location(self, marker: str, location: str) -> None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT seeded_locations FROM honey_tokens WHERE marker = ?",
                (marker,),
            ).fetchone()
            if row is None:
                return
            existing = [p for p in (row[0] or "").split("\n") if p]
            if location not in existing:
                existing.append(location)
            conn.execute(
                "UPDATE honey_tokens SET seeded_locations = ? WHERE marker = ?",
                ("\n".join(existing), marker),
            )
            conn.commit()

    def delete(self, marker: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM honey_tokens WHERE marker = ?", (marker,))
            conn.commit()

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM honey_tokens")
            conn.commit()

    def markers_with_ids(self) -> Iterable[tuple[str, str]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT marker, id FROM honey_tokens").fetchall()
        return [(r[0], r[1]) for r in rows]
