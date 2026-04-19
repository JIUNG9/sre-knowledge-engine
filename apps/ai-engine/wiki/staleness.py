"""Detect stale and archive-eligible wiki pages based on freshness rules.

The StalenessLinter computes a freshness label per page (current, stale,
archived, needs_review) using per-source-type thresholds, identifies orphan
pages with no inbound [[wikilinks]], and can move archivable pages into a
vault ``_archive`` directory while preserving their frontmatter.

Reports persist to ``~/Documents/obsidian-sre/_meta/staleness-report.json``.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING

import anyio
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .synthesizer import WikiPage


log = logging.getLogger("aegis.wiki")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STALENESS_REPORT_PATH = (
    Path.home() / "Documents" / "obsidian-sre" / "_meta" / "staleness-report.json"
)

FreshnessT = Literal["current", "stale", "archived", "needs_review"]
SourceTypeT = Literal["confluence", "github_docs", "runbook", "incident", "manual"]
CheckFreqT = Literal["hourly", "daily", "weekly"]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class StalenessRule(BaseModel):
    """Per-source-type freshness thresholds."""

    source_type: SourceTypeT
    stale_threshold_days: int
    archive_threshold_days: int
    check_frequency: CheckFreqT


DEFAULT_RULES: dict[str, StalenessRule] = {
    "confluence": StalenessRule(
        source_type="confluence",
        stale_threshold_days=90,
        archive_threshold_days=180,
        check_frequency="daily",
    ),
    "github_docs": StalenessRule(
        source_type="github_docs",
        stale_threshold_days=60,
        archive_threshold_days=180,
        check_frequency="daily",
    ),
    "runbook": StalenessRule(
        source_type="runbook",
        stale_threshold_days=120,
        archive_threshold_days=365,
        check_frequency="weekly",
    ),
    "incident": StalenessRule(
        source_type="incident",
        stale_threshold_days=365,
        archive_threshold_days=730,
        check_frequency="weekly",
    ),
    "manual": StalenessRule(
        source_type="manual",
        stale_threshold_days=30,
        archive_threshold_days=180,
        check_frequency="daily",
    ),
}


class StaleEntry(BaseModel):
    """A page flagged as stale, archivable, or orphaned."""

    slug: str
    reason: str
    days_old: int | None = None
    source_type: str | None = None
    current_freshness: FreshnessT | None = None


class StalenessReport(BaseModel):
    """Vault-wide freshness summary."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_pages: int = 0
    current_count: int = 0
    stale_count: int = 0
    archived_count: int = 0
    needs_review_count: int = 0
    stale_pages: list[StaleEntry] = Field(default_factory=list)
    archivable_pages: list[StaleEntry] = Field(default_factory=list)
    orphan_pages: list[StaleEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------


class StalenessLinter:
    """Applies StalenessRule set to a list of WikiPages."""

    def __init__(
        self,
        rules: dict[str, StalenessRule] | None = None,
        persist_path: Path | None = None,
    ) -> None:
        merged: dict[str, StalenessRule] = dict(DEFAULT_RULES)
        if rules:
            merged.update(rules)
        self.rules = merged
        self.persist_path = persist_path or STALENESS_REPORT_PATH

    # --- public API --------------------------------------------------------

    async def lint_page(self, page: "WikiPage") -> FreshnessT:
        """Return the computed freshness label for a single page."""
        # Manual override: frontmatter can pin freshness (e.g. "evergreen" ==
        # current). Honor an explicit archived flag regardless.
        fm = getattr(page, "frontmatter", None) or {}
        explicit = fm.get("freshness") if isinstance(fm, dict) else None
        if explicit == "archived":
            return "archived"

        rule = self._rule_for(page)
        days = _days_since(getattr(page, "last_updated", None))
        if days is None:
            # No last_updated -> demand a human look.
            return "needs_review"

        if days >= rule.archive_threshold_days:
            return "archived"
        if days >= rule.stale_threshold_days:
            return "stale"
        return "current"

    async def find_orphans(self, pages: list["WikiPage"]) -> list["WikiPage"]:
        """Return pages that no other page links to via [[wikilinks]]."""
        linked: set[str] = set()
        for p in pages:
            for target in _extract_wikilink_targets(getattr(p, "body", "") or ""):
                linked.add(target.lower())

        orphans: list["WikiPage"] = []
        for p in pages:
            slug = (p.slug or "").lower()
            title = (getattr(p, "title", "") or "").lower()
            # Check both slug and title — Obsidian links are often by title.
            if slug and slug in linked:
                continue
            if title and title in linked:
                continue
            # Allow index-like pages to be exempt via frontmatter flag.
            fm = getattr(p, "frontmatter", None) or {}
            if isinstance(fm, dict) and fm.get("index_page") is True:
                continue
            orphans.append(p)
        return orphans

    async def scan_vault(self, pages: list["WikiPage"]) -> StalenessReport:
        """Compute freshness for every page, mutate in place, return report."""
        report = StalenessReport(total_pages=len(pages))

        for page in pages:
            freshness = await self.lint_page(page)
            # Mutate in place per spec.
            try:
                page.freshness = freshness
            except Exception:
                log.warning("staleness: could not set freshness on %s", getattr(page, "slug", "?"))

            days = _days_since(getattr(page, "last_updated", None))
            rule = self._rule_for(page)
            entry = StaleEntry(
                slug=page.slug,
                reason=_reason_for(freshness, days, rule),
                days_old=days,
                source_type=rule.source_type,
                current_freshness=freshness,
            )

            if freshness == "current":
                report.current_count += 1
            elif freshness == "stale":
                report.stale_count += 1
                report.stale_pages.append(entry)
            elif freshness == "archived":
                report.archived_count += 1
                report.archivable_pages.append(entry)
            elif freshness == "needs_review":
                report.needs_review_count += 1
                report.stale_pages.append(entry)

        orphans = await self.find_orphans(pages)
        report.orphan_pages = [
            StaleEntry(
                slug=p.slug,
                reason="no inbound [[wikilinks]] found in vault",
                days_old=_days_since(getattr(p, "last_updated", None)),
                source_type=self._rule_for(p).source_type,
                current_freshness=getattr(p, "freshness", None),
            )
            for p in orphans
        ]

        await self._persist(report)
        return report

    async def auto_archive(self, report: StalenessReport, vault_root: Path) -> int:
        """Move archivable pages to ``vault_root/_archive/<source_type>/``.

        Preserves frontmatter but sets ``freshness: archived``. Returns the
        number of pages actually moved. Missing files are skipped with a
        warning (the caller may have re-ingested in the meantime).
        """
        if not report.archivable_pages:
            return 0

        vault_root = Path(vault_root)
        moved = 0
        # Build a lookup from entry.slug -> actual Path on disk by scanning the
        # vault. This is O(n) but avoids taking pages as a second argument.
        slug_to_path = await _build_slug_index(vault_root)

        for entry in report.archivable_pages:
            src = slug_to_path.get(entry.slug)
            if src is None or not src.exists():
                log.warning("staleness.auto_archive: no file for slug=%s", entry.slug)
                continue

            dest_dir = vault_root / "_archive" / (entry.source_type or "manual")
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / src.name

                # Rewrite frontmatter: set freshness: archived.
                try:
                    raw = src.read_text(encoding="utf-8")
                    rewritten = _set_frontmatter_key(raw, "freshness", "archived")
                    dest.write_text(rewritten, encoding="utf-8")
                    src.unlink()
                except UnicodeDecodeError:
                    # Binary or oddly-encoded — just move without rewrite.
                    shutil.move(str(src), str(dest))

                moved += 1
                log.info("staleness.auto_archive: %s -> %s", src, dest)
            except Exception:
                log.exception("staleness.auto_archive: failed for %s", src)

        return moved

    # --- internals ---------------------------------------------------------

    def _rule_for(self, page: "WikiPage") -> StalenessRule:
        """Resolve the rule by page frontmatter source_type or page.type."""
        fm = getattr(page, "frontmatter", None) or {}
        source_type = None
        if isinstance(fm, dict):
            source_type = fm.get("source_type")
        if not source_type:
            # Fall back to WikiPage.type if it matches a known key.
            source_type = getattr(page, "type", None)
        key = str(source_type or "manual").lower()
        return self.rules.get(key, self.rules["manual"])

    async def _persist(self, report: StalenessReport) -> None:
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = report.model_dump(mode="json")
            async with await anyio.open_file(self.persist_path, "w") as f:
                await f.write(json.dumps(payload, indent=2, default=str))
            log.info(
                "staleness: persisted report (stale=%d archivable=%d orphans=%d) to %s",
                report.stale_count,
                report.archived_count,
                len(report.orphan_pages),
                self.persist_path,
            )
        except Exception:
            log.exception("staleness: failed to persist report")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _days_since(ts: Any) -> int | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(ts, datetime):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    return max(delta.days, 0)


def _extract_wikilink_targets(body: str) -> set[str]:
    return {m.group(1).strip() for m in _WIKILINK_RE.finditer(body or "")}


def _reason_for(freshness: FreshnessT, days: int | None, rule: StalenessRule) -> str:
    if freshness == "needs_review":
        return "no last_updated timestamp — needs manual review"
    if days is None:
        return f"freshness={freshness}"
    if freshness == "archived":
        return (
            f"{days} days old (archive threshold for {rule.source_type}: "
            f"{rule.archive_threshold_days} days)"
        )
    if freshness == "stale":
        return (
            f"{days} days old (stale threshold for {rule.source_type}: "
            f"{rule.stale_threshold_days} days)"
        )
    return f"{days} days old — within {rule.source_type} freshness window"


async def _build_slug_index(vault_root: Path) -> dict[str, Path]:
    """Walk the vault once and map slug -> .md file path.

    Slug is assumed to be the filename stem (matches synthesizer conventions).
    The _archive and _meta directories are skipped.
    """
    index: dict[str, Path] = {}
    if not vault_root.exists():
        return index
    for path in vault_root.rglob("*.md"):
        parts = set(path.parts)
        if "_archive" in parts or "_meta" in parts:
            continue
        slug = path.stem
        # Later files with the same stem are ambiguous — keep the first.
        index.setdefault(slug, path)
    return index


def _set_frontmatter_key(raw: str, key: str, value: str) -> str:
    """Rewrite/inject a YAML frontmatter key=value at the top of a markdown doc.

    Intentionally minimal: we don't bring in PyYAML just for this. If the
    frontmatter block is present we do a line-level replace; otherwise we
    prepend a fresh block.
    """
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return f"---\n{key}: {value}\n---\n\n{raw}"

    block = match.group(1)
    lines = block.split("\n")
    key_re = re.compile(rf"^\s*{re.escape(key)}\s*:")
    replaced = False
    for i, line in enumerate(lines):
        if key_re.match(line):
            lines[i] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}: {value}")
    new_block = "\n".join(lines)
    return raw[: match.start()] + f"---\n{new_block}\n---\n" + raw[match.end() :]
