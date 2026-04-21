"""Tests for the cross-source :class:`Reconciler`."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from reconciliation.models import Doc, DocRef
from reconciliation.reconciler import Reconciler
from reconciliation.sources import DocSource


class _InMemorySource(DocSource):
    """Tiny in-memory DocSource used only in tests."""

    def __init__(self, name: str, docs: list[Doc]) -> None:
        self.name = name  # type: ignore[assignment]
        self._docs = {d.id: d for d in docs}

    def list(self) -> list[str]:
        return list(self._docs.keys())

    def fetch(self, doc_id: str) -> Doc | None:
        return self._docs.get(doc_id)


class _FakeResponse:
    def __init__(self, text: str, backend: str = "ollama") -> None:
        self.text = text
        self.backend = backend
        self.decision = None
        self.usage = {}


class _FakeRouter:
    def __init__(self, payload: str, backend: str = "ollama") -> None:
        self.payload = payload
        self.backend = backend
        self.calls: list[dict[str, Any]] = []

    async def complete(self, messages, *, sensitivity_override=None):
        self.calls.append(
            {"messages": messages, "sensitivity_override": sensitivity_override}
        )
        return _FakeResponse(self.payload, self.backend)


class _UnavailableRouter:
    async def complete(self, messages, *, sensitivity_override=None):
        raise RuntimeError("OllamaUnavailable: connection refused")


@pytest.fixture
def two_sources(contradicting_docs):
    obsidian = _InMemorySource("obsidian", [contradicting_docs[0]])
    confluence = _InMemorySource("confluence", [contradicting_docs[1]])
    return [obsidian, confluence]


# --- find ---------------------------------------------------------------- #


def test_find_returns_ranked_docrefs(two_sources):
    r = Reconciler(sources=two_sources)
    refs = r.find("postgres")
    assert len(refs) == 2
    # Fresher doc first.
    assert refs[0].freshness_score >= refs[1].freshness_score
    assert isinstance(refs[0], DocRef)


def test_find_empty_topic_returns_empty(two_sources):
    r = Reconciler(sources=two_sources)
    assert r.find("") == []


def test_find_respects_source_filter(two_sources):
    r = Reconciler(sources=two_sources)
    refs = r.find("postgres", sources=["obsidian"])
    assert len(refs) == 1
    assert refs[0].source == "obsidian"


def test_find_ranks_by_freshness(contradicting_docs):
    # Reverse the source order — ranking must still put the recent one first.
    obs = _InMemorySource("obsidian", [contradicting_docs[0]])
    conf = _InMemorySource("confluence", [contradicting_docs[1]])
    r = Reconciler(sources=[conf, obs])
    refs = r.find("postgres")
    assert refs[0].source == "obsidian"


# --- compare: string diff layer ----------------------------------------- #


@pytest.mark.asyncio
async def test_compare_without_router_still_flags_version_mismatch(two_sources):
    r = Reconciler(sources=two_sources, llm_router=None)
    report = await r.compare("postgres")
    assert report.llm_available is False
    assert report.llm_backend is None
    assert report.contradictions, "string-diff should detect version mismatch"
    categories = {c.category for c in report.contradictions}
    assert "version_mismatch" in categories
    assert "llm_router not configured" in " ".join(report.notes)


@pytest.mark.asyncio
async def test_compare_includes_topic_and_sources_queried(two_sources):
    r = Reconciler(sources=two_sources)
    report = await r.compare("postgres")
    assert report.topic == "postgres"
    assert set(report.sources_queried) == {"obsidian", "confluence"}


# --- compare: LLM layer --------------------------------------------------- #


_LLM_PAYLOAD = json.dumps(
    [
        {
            "claim_a": "Use postgres 16",
            "claim_b": "Use postgres 13",
            "severity": "critical",
            "category": "version_mismatch",
            "explanation": "disagrees on the major version",
        },
        {
            "claim_a": "scale the deployment to 0",
            "claim_b": "restart the deployment",
            "severity": "warning",
            "category": "procedure_conflict",
            "explanation": "different remediation steps",
        },
    ]
)


@pytest.mark.asyncio
async def test_compare_with_router_adds_semantic_contradictions(two_sources):
    router = _FakeRouter(_LLM_PAYLOAD)
    r = Reconciler(sources=two_sources, llm_router=router)
    report = await r.compare("postgres")
    assert report.llm_available is True
    assert report.llm_backend == "ollama"
    # At least two semantic + one string-diff finding.
    assert len(report.contradictions) >= 3
    sev = [c.severity for c in report.contradictions]
    assert "critical" in sev
    # Sensitive content should route to local by default.
    assert router.calls[0]["sensitivity_override"] is True


@pytest.mark.asyncio
async def test_compare_gracefully_handles_local_llm_unavailable(two_sources):
    r = Reconciler(sources=two_sources, llm_router=_UnavailableRouter())
    report = await r.compare("postgres")
    assert report.llm_available is False
    assert any("unavailable" in n.lower() for n in report.notes)
    # String-diff layer still runs → version mismatch remains.
    assert any(c.category == "version_mismatch" for c in report.contradictions)


@pytest.mark.asyncio
async def test_compare_handles_garbled_llm_payload(two_sources):
    router = _FakeRouter("not-json at all ```json {bad}```")
    r = Reconciler(sources=two_sources, llm_router=router)
    report = await r.compare("postgres")
    # Semantic findings should be zero but the report should still exist.
    assert report.llm_available is True
    # Only string-diff finding(s).
    categories = {c.category for c in report.contradictions}
    assert categories <= {"version_mismatch", "procedure_conflict", "coverage_gap", "factual_contradiction"}


@pytest.mark.asyncio
async def test_llm_pair_limit_caps_router_calls():
    now = datetime.now(timezone.utc)
    docs = [
        Doc(id=f"a{i}", source="obsidian", title=f"DB {i}", body=f"postgres {13+i}", last_modified=now - timedelta(days=i))
        for i in range(5)
    ]
    src = _InMemorySource("obsidian", docs)
    router = _FakeRouter("[]")
    r = Reconciler(sources=[src], llm_router=router, llm_pair_limit=2)
    await r.compare("postgres")
    assert len(router.calls) == 2
