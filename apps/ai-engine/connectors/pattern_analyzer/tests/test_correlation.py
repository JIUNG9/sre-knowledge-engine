"""Tests for the service correlation graph."""
from __future__ import annotations

from connectors.pattern_analyzer.correlation import service_correlation_graph
from connectors.pattern_analyzer.tests.fixtures import correlated_services


def test_paired_services_are_highly_correlated():
    events = correlated_services(n_pairs=30, seed=11)
    graph = service_correlation_graph(events, window_seconds=300, min_score=0.3)

    # a -> b edge should exist with near-1.0 score
    ab_edges = [e for e in graph.edges if e.source == "service-a" and e.target == "service-b"]
    assert ab_edges, "expected a -> b edge"
    ab = ab_edges[0]
    assert ab.score >= 0.9, f"a->b score too low: {ab.score}"

    # b -> a should also exist (symmetric within window)
    ba_edges = [e for e in graph.edges if e.source == "service-b" and e.target == "service-a"]
    assert ba_edges
    assert ba_edges[0].score >= 0.9


def test_independent_service_has_no_strong_edge():
    events = correlated_services(n_pairs=30, seed=11)
    graph = service_correlation_graph(events, window_seconds=300, min_score=0.3)
    # service-c should not appear in any edge (score below threshold)
    c_edges = [
        e for e in graph.edges if e.source == "service-c" or e.target == "service-c"
    ]
    assert not c_edges, f"service-c should have no strong edges, got: {c_edges}"


def test_firing_counts_are_correct():
    events = correlated_services(n_pairs=30, seed=11)
    graph = service_correlation_graph(events)
    assert graph.firing_counts["service-a"] == 30
    assert graph.firing_counts["service-b"] == 30
    assert graph.firing_counts["service-c"] == 30


def test_empty_input_returns_empty_graph():
    graph = service_correlation_graph([])
    assert graph.services == []
    assert graph.edges == []


def test_top_pairs_is_sorted_by_score():
    events = correlated_services(n_pairs=30, seed=11)
    graph = service_correlation_graph(events)
    pairs = graph.top_pairs(5)
    scores = [p.score for p in pairs]
    assert scores == sorted(scores, reverse=True)
