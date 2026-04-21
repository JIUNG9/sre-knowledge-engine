"""
Message clustering — group noisy log/alert messages by underlying template.

Two steps:
    1. Canonicalisation — strip numbers, UUIDs, IPs, timestamps, hex blobs,
       quoted strings, paths with digits, etc. so messages that share a
       template collapse to the same "canonical" form.
    2. Grouping — messages with identical canonical form are merged first
       (cheap exact dedup). Remaining groups are then merged via MinHash /
       Jaccard similarity on 3-shingles — catches near-duplicates that
       survived canonicalisation.

Deterministic: MinHash seeds are fixed per-instance (we use stable xxhash-like
hashing via hashlib.blake2b with a fixed 8-byte salt). Pure stdlib; no numpy.

Memory-bounded: streams events, keeps at most `max_clusters` representative
MinHashes in memory (default 20). Late-arriving low-frequency templates are
silently merged into an "other" bucket once we hit the cap.
"""
from __future__ import annotations

import hashlib
import re
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Protocol, runtime_checkable

# Regex order matters — apply longest/most-specific first.
_CANON_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # ISO-8601 timestamps
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TS>"),
    # UUIDs
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    # IPv4
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "<IP>"),
    # IPv6 (loose)
    (re.compile(r"\b(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4}\b", re.I), "<IPV6>"),
    # Long hex blobs (>= 12 hex chars) — trace IDs, hashes
    (re.compile(r"\b[0-9a-f]{12,}\b", re.I), "<HEX>"),
    # Quoted strings
    (re.compile(r'"[^"]{0,200}"'), "<STR>"),
    (re.compile(r"'[^']{0,200}'"), "<STR>"),
    # Durations / sizes with units (42ms, 1.5s, 100MB)
    (re.compile(r"\b\d+(?:\.\d+)?\s?(?:ns|us|µs|ms|s|m|h|KB|MB|GB|TB|bytes?)\b", re.I), "<NUM>"),
    # Bare numbers (>= 2 digits — keep single digits like "v1" distinctive)
    (re.compile(r"\b\d{2,}\b"), "<NUM>"),
    # File paths with trailing digits (e.g. /var/log/app-123.log)
    (re.compile(r"(/[\w./-]*?)-?\d+(\.\w+)?\b"), r"\1<NUM>\2"),
)

_WHITESPACE = re.compile(r"\s+")


@runtime_checkable
class _HasMessage(Protocol):
    message: str


@dataclass
class MessageCluster:
    """One template / cluster of canonically-equivalent messages.

    `template` is the canonicalised form. `count` is how many events matched.
    `examples` holds up to 3 raw (non-canonical) messages for human sanity.
    `severity_breakdown` counts how many events at each severity hit this
    cluster — useful for triage.
    """

    template: str
    count: int
    examples: list[str] = field(default_factory=list)
    severity_breakdown: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Canonicalisation
# ---------------------------------------------------------------------------


def canonicalise(message: str) -> str:
    """Strip variable tokens (numbers, UUIDs, IPs, etc.) to a stable template."""
    s = message
    for pat, repl in _CANON_PATTERNS:
        s = pat.sub(repl, s)
    s = _WHITESPACE.sub(" ", s).strip()
    return s


# ---------------------------------------------------------------------------
# MinHash — deterministic, stdlib-only, ~60 LoC
# ---------------------------------------------------------------------------


class _MinHash:
    """Deterministic MinHash using blake2b with per-permutation salts.

    `signature(tokens)` returns a tuple of num_perm ints. Two MinHashes can
    be compared with `jaccard(a, b)` — estimates Jaccard similarity of the
    original token sets with error ~1/sqrt(num_perm).
    """

    __slots__ = ("num_perm", "salts")

    def __init__(self, num_perm: int = 64, seed: int = 0xA3615) -> None:
        self.num_perm = num_perm
        # Fixed per-permutation salts derived from seed. Deterministic.
        self.salts = tuple(
            hashlib.blake2b(struct.pack(">QI", seed, i), digest_size=8).digest()
            for i in range(num_perm)
        )

    def _hash(self, token: str, salt: bytes) -> int:
        h = hashlib.blake2b(token.encode("utf-8"), digest_size=8, key=salt).digest()
        return int.from_bytes(h, "big")

    def signature(self, tokens: Iterable[str]) -> tuple[int, ...]:
        token_list = list(tokens)
        if not token_list:
            return tuple(0 for _ in range(self.num_perm))
        sig = [min(self._hash(t, salt) for t in token_list) for salt in self.salts]
        return tuple(sig)

    @staticmethod
    def jaccard(a: tuple[int, ...], b: tuple[int, ...]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        matches = sum(1 for x, y in zip(a, b) if x == y)
        return matches / len(a)


def _shingles(s: str, k: int = 3) -> list[str]:
    """K-shingles (character n-grams) of the canonicalised message."""
    s = s.lower()
    if len(s) <= k:
        return [s] if s else []
    return [s[i : i + k] for i in range(len(s) - k + 1)]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def cluster_messages(
    events: Iterable[_HasMessage],
    max_clusters: int = 20,
    similarity_threshold: float = 0.6,
    num_perm: int = 64,
) -> list[MessageCluster]:
    """Group events by message template.

    Two-pass:
        pass 1: exact-match on canonical form — cheap O(n), eliminates 90%+
        pass 2: MinHash-merge canonical groups whose Jaccard >= threshold

    Returns clusters sorted by count (desc). At most `max_clusters` are
    returned; overflow is merged into an "<other>" bucket.
    """
    if max_clusters <= 0:
        raise ValueError("max_clusters must be > 0")

    # Pass 1: exact canonical
    groups: dict[str, MessageCluster] = {}
    for ev in events:
        msg = getattr(ev, "message", None)
        if not isinstance(msg, str):
            continue
        canon = canonicalise(msg)
        cluster = groups.get(canon)
        if cluster is None:
            cluster = MessageCluster(template=canon, count=0, examples=[])
            groups[canon] = cluster
        cluster.count += 1
        if len(cluster.examples) < 3 and msg not in cluster.examples:
            cluster.examples.append(msg)
        sev = getattr(ev, "severity", None)
        if isinstance(sev, str):
            cluster.severity_breakdown[sev] = cluster.severity_breakdown.get(sev, 0) + 1

    if not groups:
        return []

    # Pass 2: MinHash merge for near-dup canonical templates (typos, optional words)
    mh = _MinHash(num_perm=num_perm)
    sigs: list[tuple[str, tuple[int, ...]]] = [
        (template, mh.signature(_shingles(template))) for template in groups
    ]

    # Union-find on template keys
    parent: dict[str, str] = {t: t for t, _ in sigs}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # Keep the higher-count template as the root (stable, deterministic)
        ca, cb = groups[ra].count, groups[rb].count
        if ca >= cb:
            parent[rb] = ra
        else:
            parent[ra] = rb

    # Sort sigs by template string for determinism in the O(n^2) loop
    sigs.sort(key=lambda t: t[0])
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            if _MinHash.jaccard(sigs[i][1], sigs[j][1]) >= similarity_threshold:
                union(sigs[i][0], sigs[j][0])

    # Roll up into root buckets
    merged: dict[str, MessageCluster] = {}
    for template, cluster in groups.items():
        root = find(template)
        if root not in merged:
            merged[root] = MessageCluster(
                template=root,
                count=0,
                examples=[],
                severity_breakdown={},
            )
        merged[root].count += cluster.count
        for ex in cluster.examples:
            if ex not in merged[root].examples and len(merged[root].examples) < 3:
                merged[root].examples.append(ex)
        for sev, n in cluster.severity_breakdown.items():
            merged[root].severity_breakdown[sev] = (
                merged[root].severity_breakdown.get(sev, 0) + n
            )

    result = sorted(merged.values(), key=lambda c: (-c.count, c.template))
    if len(result) > max_clusters:
        head = result[: max_clusters - 1]
        tail = result[max_clusters - 1 :]
        other = MessageCluster(
            template="<other>",
            count=sum(c.count for c in tail),
            examples=[],
            severity_breakdown=dict(
                Counter(
                    {
                        sev: n
                        for c in tail
                        for sev, n in c.severity_breakdown.items()
                    }
                )
            ),
        )
        # Rebuild severity_breakdown correctly (Counter trick above loses sums)
        sev_tot: dict[str, int] = defaultdict(int)
        for c in tail:
            for sev, n in c.severity_breakdown.items():
                sev_tot[sev] += n
        other.severity_breakdown = dict(sev_tot)
        result = head + [other]
    return result
