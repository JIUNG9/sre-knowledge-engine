"""Seed honey tokens into a demo Obsidian/Markdown vault.

The seeder is deliberately idempotent: it looks for a sentinel comment
at the top of any file it has already touched and refuses to write
twice. Real content is never overwritten — seeded tokens are appended
below a clearly marked footer section (invisible to readers scanning
the page but obvious to the scanner once exfiltrated).
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .generator import HoneyTokenGenerator, TokenCategory

if TYPE_CHECKING:
    from .generator import HoneyToken

log = logging.getLogger("aegis.honeytokens.seeder")

SEED_SENTINEL = "<!-- aegis-honey-seeded -->"
SEED_SECTION_HEADER = "\n\n---\n\n<!-- aegis-honey-seeded -->\n## Deprecated legacy credentials\n\n"
SEED_SECTION_FOOTER = "\n<!-- /aegis-honey-seeded -->\n"


def _iter_markdown(vault_dir: Path) -> List[Path]:
    return [p for p in vault_dir.rglob("*.md") if p.is_file()]


def _is_already_seeded(text: str) -> bool:
    return SEED_SENTINEL in text


def _render_block(tokens: List["HoneyToken"]) -> str:
    lines: List[str] = []
    for t in tokens:
        lines.append(f"### {t.category}")
        lines.append("```")
        lines.append(t.value)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def seed_vault(
    vault_dir: Path,
    count_per_category: int = 2,
    *,
    generator: Optional[HoneyTokenGenerator] = None,
    rng: Optional[random.Random] = None,
    categories: Optional[List[TokenCategory]] = None,
) -> Dict[str, List[str]]:
    """Insert honey tokens into a markdown vault.

    Args:
        vault_dir: Root of the Obsidian-style vault.
        count_per_category: How many tokens of each category to create.
        generator: Inject a generator to share a registry; a default
            one is created if omitted.
        rng: Optional random source so tests can seed placement.
        categories: Override the category list (defaults to all).

    Returns:
        Mapping of file-path string -> list of marker IDs seeded there.
        Idempotent: if a file is already seeded it is silently skipped.
    """
    vault_dir = Path(vault_dir)
    if not vault_dir.is_dir():
        raise FileNotFoundError(f"vault_dir does not exist: {vault_dir}")

    gen = generator or HoneyTokenGenerator()
    rng = rng or random.Random()
    cats: List[TokenCategory] = list(categories) if categories else list(gen.all_categories())

    md_files = _iter_markdown(vault_dir)
    if not md_files:
        log.warning("no markdown files in %s; nothing seeded", vault_dir)
        return {}

    # Generate tokens.
    tokens: List["HoneyToken"] = []
    for cat in cats:
        for _ in range(count_per_category):
            tokens.append(gen.create(cat))

    # Distribute them across markdown files (round-robin from a shuffled
    # list so the placement is deterministic given the rng).
    rng.shuffle(md_files)
    placements: Dict[Path, List["HoneyToken"]] = {}
    for i, t in enumerate(tokens):
        target = md_files[i % len(md_files)]
        placements.setdefault(target, []).append(t)

    result: Dict[str, List[str]] = {}
    for path, token_group in placements.items():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if _is_already_seeded(existing):
            log.warning("skipping already-seeded file: %s", path)
            continue
        block = SEED_SECTION_HEADER + _render_block(token_group) + SEED_SECTION_FOOTER
        path.write_text(existing.rstrip() + block, encoding="utf-8")
        markers = [t.marker for t in token_group]
        result[str(path)] = markers
        for t in token_group:
            gen.registry.add_seeded_location(t.marker, str(path))
    log.warning(
        "seeded %d tokens across %d files in %s",
        sum(len(v) for v in result.values()),
        len(result),
        vault_dir,
    )
    return result
