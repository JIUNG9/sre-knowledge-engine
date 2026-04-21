"""Tests for canonicalisation and MinHash message clustering."""
from __future__ import annotations

from connectors.pattern_analyzer.message_clustering import (
    _MinHash,
    _shingles,
    canonicalise,
    cluster_messages,
)
from connectors.pattern_analyzer.tests.fixtures import Event, templated_log_lines


def test_canonicalise_strips_numbers_and_uuids():
    msg = "User 12345 logged in from 192.168.1.10 trace=a1b2c3d4e5f60718 at 2026-04-21T12:00:00Z"
    canon = canonicalise(msg)
    assert "12345" not in canon
    assert "192.168.1.10" not in canon
    assert "a1b2c3d4e5f60718" not in canon
    assert "2026-04-21" not in canon
    assert "<NUM>" in canon or "<HEX>" in canon or "<IP>" in canon


def test_canonicalise_is_idempotent():
    msg = "Slow query took 542ms on shard 3"
    c1 = canonicalise(msg)
    c2 = canonicalise(c1)
    assert c1 == c2


def test_clustering_recovers_five_templates_from_50_lines():
    events = templated_log_lines(per_template=10, seed=7)  # 50 events / 5 templates
    clusters = cluster_messages(events, max_clusters=20, similarity_threshold=0.5)
    # We should converge to 5 clusters (one per template).
    assert len(clusters) == 5, f"expected 5 clusters, got {len(clusters)}: {[c.template for c in clusters]}"
    # Each should have ~10 events.
    for c in clusters:
        assert c.count == 10, f"uneven cluster: {c.template} -> {c.count}"
    # Templates should be stripped of variables.
    for c in clusters:
        assert "<" in c.template, f"template not canonicalised: {c.template}"


def test_minhash_is_deterministic():
    mh1 = _MinHash(num_perm=32)
    mh2 = _MinHash(num_perm=32)
    s = _shingles("hello world test string")
    assert mh1.signature(s) == mh2.signature(s)


def test_minhash_jaccard_of_identical_is_one():
    mh = _MinHash(num_perm=64)
    sig = mh.signature(_shingles("identical text"))
    assert _MinHash.jaccard(sig, sig) == 1.0


def test_minhash_jaccard_of_disjoint_is_low():
    mh = _MinHash(num_perm=64)
    a = mh.signature(_shingles("completely different words here"))
    b = mh.signature(_shingles("zzz yyy xxx vvv uuu"))
    # Tolerate some hash collisions
    assert _MinHash.jaccard(a, b) < 0.3


def test_cluster_messages_handles_empty_input():
    assert cluster_messages([]) == []


def test_cluster_messages_examples_preserve_originals():
    events = [
        Event(
            timestamp=None,  # type: ignore[arg-type]
            service="s",
            severity="info",
            message="User 1 logged in from 10.0.0.1",
            trace_id=None,
        ),
        Event(
            timestamp=None,  # type: ignore[arg-type]
            service="s",
            severity="info",
            message="User 2 logged in from 10.0.0.2",
            trace_id=None,
        ),
    ]
    clusters = cluster_messages(events)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.count == 2
    # Examples keep raw, non-canonicalised messages
    assert any("10.0.0.1" in e for e in cluster.examples)
