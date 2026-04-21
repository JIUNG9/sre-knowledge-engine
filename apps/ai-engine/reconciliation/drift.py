"""Drift / staleness scoring for individual docs.

A doc is assigned a score between 0.0 (fresh) and 1.0 (extremely
stale) using four signals:

1. Age-of-last-modification (dominant signal).
2. Presence of year markers that look decommissioned (2022, 2023…).
3. Mentions of known-dead systems (configurable).
4. Stale-indicator phrases ("TODO: update this", "DEPRECATED", …).

Each signal contributes to the final score with capped weight so a
doc with a single suspicious phrase doesn't get marked as maximally
stale on its own.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Doc, StalenessScore


# Anything older than this caps the age contribution at 1.0.
_AGE_FLOOR_DAYS = 730  # 2 years

# Years before the current year that are suspicious to see hard-coded.
# Default list is conservative: callers can widen it.
_DEFAULT_SUSPICIOUS_YEARS = ("2022", "2023")

# Default stale-indicator phrases. The list is deliberately short —
# each one is high-precision. Users can extend via `extra_indicators`.
_DEFAULT_STALE_PHRASES = (
    "todo: update",
    "todo update",
    "fixme: update",
    "deprecated",
    "no longer used",
    "will be removed",
    "legacy",
    "obsolete",
    "xxx: stale",
    "outdated",
    "out of date",
)

# Default decommissioned systems — SRE-shaped defaults. Users pass
# their own list for accurate results.
_DEFAULT_DECOMMISSIONED = (
    "mesos",
    "marathon",
    "docker swarm",
    "python 2",
    "python2",
    "centos 6",
    "centos 7",
    "jenkins 1",
)


def score_staleness(
    doc: Doc,
    *,
    now: datetime | None = None,
    suspicious_years: tuple[str, ...] = _DEFAULT_SUSPICIOUS_YEARS,
    decommissioned_systems: tuple[str, ...] = _DEFAULT_DECOMMISSIONED,
    extra_indicators: tuple[str, ...] = (),
) -> StalenessScore:
    """Return a :class:`StalenessScore` for a single :class:`Doc`.

    The function is pure — it takes ``now`` as an argument so tests can
    freeze time without monkey-patching ``datetime``.
    """
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    stale_indicators: list[str] = []
    decommissioned_refs: list[str] = []

    # --- 1. Age --------------------------------------------------------
    age_days: int | None = None
    age_score = 0.0
    ts = doc.last_modified
    if ts is not None:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = now - ts
        age_days = max(delta.days, 0)
        age_score = min(age_days / _AGE_FLOOR_DAYS, 1.0)
        if age_days > 180:
            reasons.append(
                f"last modified {age_days} days ago (threshold: 180 days)"
            )
    else:
        # No timestamp is itself suspicious, but only mildly.
        age_score = 0.5
        reasons.append("no last_modified timestamp")

    # --- 2. Suspicious year markers ------------------------------------
    body_lower = (doc.body or "").lower()
    title_lower = (doc.title or "").lower()
    haystack = f"{title_lower}\n{body_lower}"
    year_hits: list[str] = []
    for year in suspicious_years:
        # Match the year as a standalone token to avoid false positives
        # like "route53" or IP addresses.
        pattern = re.compile(rf"\b{re.escape(year)}\b")
        if pattern.search(haystack):
            year_hits.append(year)
    if year_hits:
        reasons.append(f"references old years: {', '.join(year_hits)}")
    year_score = min(len(year_hits) * 0.15, 0.3)

    # --- 3. Decommissioned systems -------------------------------------
    for system in decommissioned_systems:
        if system.lower() in haystack:
            decommissioned_refs.append(system)
    if decommissioned_refs:
        reasons.append(
            f"references decommissioned systems: {', '.join(decommissioned_refs)}"
        )
    decommissioned_score = min(len(decommissioned_refs) * 0.2, 0.4)

    # --- 4. Stale-indicator phrases ------------------------------------
    indicators = tuple(_DEFAULT_STALE_PHRASES) + tuple(extra_indicators)
    for phrase in indicators:
        if phrase.lower() in haystack:
            stale_indicators.append(phrase)
    if stale_indicators:
        reasons.append(
            f"contains stale-indicator phrases: {', '.join(stale_indicators)}"
        )
    phrase_score = min(len(stale_indicators) * 0.15, 0.3)

    # --- Combine -------------------------------------------------------
    # Weighted sum, then clamp to [0.0, 1.0]. Age dominates (weight 1.0)
    # but the other signals can push a recent-but-suspicious doc over
    # the threshold.
    combined = (
        age_score * 0.55
        + year_score * 0.15
        + decommissioned_score * 0.2
        + phrase_score * 0.1
    )
    combined = max(0.0, min(combined, 1.0))

    return StalenessScore(
        doc_id=doc.id,
        source=doc.source,
        score=round(combined, 3),
        age_days=age_days,
        reasons=reasons,
        stale_indicators=stale_indicators,
        decommissioned_refs=decommissioned_refs,
    )


def is_stale(score: StalenessScore, threshold: float = 0.5) -> bool:
    """Convenience predicate: is ``score`` past the configurable threshold?"""
    return score.score >= threshold


__all__ = ["score_staleness", "is_stale"]
