"""Tests for the drift / staleness scorer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from reconciliation.drift import is_stale, score_staleness
from reconciliation.models import Doc


_NOW = datetime(2026, 4, 21, tzinfo=timezone.utc)


def _doc(**overrides) -> Doc:
    base = dict(
        id="runbooks/db.md",
        source="obsidian",
        title="Database Runbook",
        body="",
        last_modified=_NOW - timedelta(days=5),
    )
    base.update(overrides)
    return Doc(**base)


def test_fresh_doc_scores_near_zero():
    doc = _doc(body="Postgres 16 pool=50")
    score = score_staleness(doc, now=_NOW)
    assert score.score < 0.2
    assert score.age_days == 5


def test_old_doc_scores_high():
    doc = _doc(last_modified=_NOW - timedelta(days=1000), body="postgres 10")
    score = score_staleness(doc, now=_NOW)
    assert score.score > 0.5
    assert score.age_days == 1000


def test_year_reference_adds_to_score():
    fresh_body = _doc(body="The playbook from 2023 says run pg_dump.")
    score = score_staleness(fresh_body, now=_NOW)
    assert "2023" in " ".join(score.reasons)


def test_decommissioned_reference_adds_to_score():
    doc = _doc(body="We run this on CentOS 7 with docker swarm.")
    score = score_staleness(doc, now=_NOW)
    assert any("decommissioned" in r for r in score.reasons)
    assert "centos 7" in score.decommissioned_refs
    assert "docker swarm" in score.decommissioned_refs


def test_stale_indicator_phrase_adds_to_score():
    doc = _doc(body="TODO: update this once the new cluster is live.")
    score = score_staleness(doc, now=_NOW)
    assert score.stale_indicators


def test_missing_timestamp_produces_needs_review_reason():
    doc = _doc(last_modified=None, body="Run postgres 16.")
    score = score_staleness(doc, now=_NOW)
    assert "no last_modified" in " ".join(score.reasons)
    assert score.age_days is None


def test_is_stale_threshold():
    doc = _doc(last_modified=_NOW - timedelta(days=1500), body="legacy obsolete")
    score = score_staleness(doc, now=_NOW)
    assert is_stale(score, threshold=0.5)
    assert not is_stale(score, threshold=0.99)


def test_score_clamped_between_zero_and_one():
    doc = _doc(
        last_modified=_NOW - timedelta(days=5000),
        body=(
            "DEPRECATED — legacy. This was written in 2022 and 2023. "
            "Uses centos 7, docker swarm, mesos, marathon, python 2. TODO: update. FIXME: update. outdated."
        ),
    )
    score = score_staleness(doc, now=_NOW)
    assert 0.0 <= score.score <= 1.0


def test_extra_indicators_are_honoured():
    doc = _doc(body="This is ZOMBIE-CODE now, please update")
    score = score_staleness(doc, now=_NOW, extra_indicators=("zombie-code",))
    assert any("zombie-code" in s.lower() for s in score.stale_indicators)
