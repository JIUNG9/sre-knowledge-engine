"""Outbound honey-token scanner.

Uses Aho-Corasick multi-pattern matching when `pyahocorasick` is
installed, otherwise falls back to a pure-Python implementation built
on top of the goto/failure-link automaton. Both paths are O(n) in the
haystack size regardless of the number of registered tokens.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Sequence

from .registry import HoneyTokenRegistry

if TYPE_CHECKING:
    from .generator import HoneyToken

log = logging.getLogger("aegis.honeytokens.scanner")

try:  # pragma: no cover - optional dependency
    import ahocorasick  # type: ignore

    _HAS_AC = True
except Exception:  # pragma: no cover
    _HAS_AC = False


@dataclass(frozen=True)
class HoneyTokenHit:
    """A single match of a honey token in scanned text."""

    marker: str
    token_id: str
    category: str
    offset: int
    context: str  # ~60 chars either side of the marker (redacted-safe)


# --------------------------------------------------------------------- fallback


class _PurePythonAhoCorasick:
    """Minimal Aho-Corasick automaton for multi-pattern exact matching.

    We keep this lightweight because markers are short, ASCII, and few
    (dozens to low thousands). The automaton is built once per scanner
    rebuild and reused for every `find_all` call.
    """

    __slots__ = ("_goto", "_fail", "_out")

    def __init__(self, patterns: Sequence[str]) -> None:
        # Trie with goto function.
        goto: list[dict[str, int]] = [{}]
        out: list[list[str]] = [[]]
        for pat in patterns:
            node = 0
            for ch in pat:
                nxt = goto[node].get(ch)
                if nxt is None:
                    goto.append({})
                    out.append([])
                    nxt = len(goto) - 1
                    goto[node][ch] = nxt
                node = nxt
            out[node].append(pat)

        # BFS to build failure links.
        fail = [0] * len(goto)
        queue: deque[int] = deque()
        for ch, nxt in goto[0].items():
            fail[nxt] = 0
            queue.append(nxt)
        while queue:
            r = queue.popleft()
            for ch, u in goto[r].items():
                queue.append(u)
                state = fail[r]
                while state and ch not in goto[state]:
                    state = fail[state]
                fail[u] = goto[state].get(ch, 0) if state or ch in goto[0] else 0
                out[u].extend(out[fail[u]])

        self._goto = goto
        self._fail = fail
        self._out = out

    def find_all(self, text: str):
        goto, fail, out = self._goto, self._fail, self._out
        state = 0
        for i, ch in enumerate(text):
            while state and ch not in goto[state]:
                state = fail[state]
            state = goto[state].get(ch, 0)
            if out[state]:
                for pat in out[state]:
                    yield i - len(pat) + 1, pat


# --------------------------------------------------------------------- scanner


class OutboundScanner:
    """Scan arbitrary text for honey tokens. Safe to share across threads.

    The automaton rebuilds lazily on first `scan()` after `invalidate()`,
    so callers can register new tokens without forcing a manual refresh.
    """

    def __init__(self, registry: Optional[HoneyTokenRegistry] = None) -> None:
        self._registry = registry or HoneyTokenRegistry()
        self._lock = threading.RLock()
        self._automaton = None  # type: ignore[assignment]
        self._marker_to_meta: dict[str, dict] = {}

    def invalidate(self) -> None:
        with self._lock:
            self._automaton = None
            self._marker_to_meta.clear()

    def _build(self) -> None:
        markers = self._registry.all_markers()
        # Cache metadata lookup once so hit construction stays O(1).
        self._marker_to_meta = {}
        for m in markers:
            meta = self._registry.get_by_marker(m)
            if meta is not None:
                self._marker_to_meta[m] = {
                    "id": meta["id"],
                    "category": meta["category"],
                }
        if not markers:
            self._automaton = None
            return
        if _HAS_AC:  # pragma: no cover - tested only when lib present
            auto = ahocorasick.Automaton()
            for m in markers:
                auto.add_word(m, m)
            auto.make_automaton()
            self._automaton = auto
        else:
            self._automaton = _PurePythonAhoCorasick(markers)

    def _ensure(self) -> None:
        if self._automaton is None:
            with self._lock:
                if self._automaton is None:
                    self._build()

    def scan(self, text: str) -> List[HoneyTokenHit]:
        """Return every honey-token hit in `text`. Empty on no tokens."""
        if not text:
            return []
        self._ensure()
        if self._automaton is None:
            return []
        hits: List[HoneyTokenHit] = []
        seen: set[tuple[str, int]] = set()
        if _HAS_AC:  # pragma: no cover
            for end_idx, marker in self._automaton.iter(text):
                start = end_idx - len(marker) + 1
                if (marker, start) in seen:
                    continue
                seen.add((marker, start))
                hits.append(self._make_hit(marker, start, text))
        else:
            for start, marker in self._automaton.find_all(text):
                if (marker, start) in seen:
                    continue
                seen.add((marker, start))
                hits.append(self._make_hit(marker, start, text))
        if hits:
            # One WARNING per scan, no token values logged.
            log.warning(
                "honey token hits=%d sample_marker=%s", len(hits), hits[0].marker
            )
        return hits

    def _make_hit(self, marker: str, start: int, text: str) -> HoneyTokenHit:
        meta = self._marker_to_meta.get(marker, {})
        ctx_start = max(0, start - 60)
        ctx_end = min(len(text), start + len(marker) + 60)
        context = text[ctx_start:ctx_end]
        return HoneyTokenHit(
            marker=marker,
            token_id=meta.get("id", marker),
            category=meta.get("category", "unknown"),
            offset=start,
            context=context,
        )

    def scan_many(self, texts: Sequence[str]) -> List[HoneyTokenHit]:
        out: List[HoneyTokenHit] = []
        for t in texts:
            out.extend(self.scan(t))
        return out


# Module-level convenience scanner. Lazily initialised so importing the
# module has no filesystem side effects.
_default_scanner: Optional[OutboundScanner] = None
_default_lock = threading.Lock()


def get_default_scanner() -> OutboundScanner:
    global _default_scanner
    if _default_scanner is None:
        with _default_lock:
            if _default_scanner is None:
                _default_scanner = OutboundScanner()
    return _default_scanner
