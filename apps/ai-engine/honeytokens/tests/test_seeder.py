"""Seeder idempotency + non-destructive behavior tests."""

from __future__ import annotations

import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

_THIS = os.path.dirname(os.path.abspath(__file__))
_AI_ENGINE = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _AI_ENGINE not in sys.path:
    sys.path.insert(0, _AI_ENGINE)

from honeytokens.generator import HoneyTokenGenerator  # noqa: E402
from honeytokens.registry import HoneyTokenRegistry  # noqa: E402
from honeytokens.scanner import OutboundScanner  # noqa: E402
from honeytokens.seeder import SEED_SENTINEL, seed_vault  # noqa: E402


class SeederTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = os.path.join(self.tmp.name, "honey.db")
        self.registry = HoneyTokenRegistry(self.db)
        self.gen = HoneyTokenGenerator(self.registry)
        # Build a tiny mock vault.
        self.files = {
            "runbook.md": "# Runbook\n\nOriginal content A.\n",
            "oncall/escalation.md": "# Escalation\n\nOriginal content B.\n",
            "architecture.md": "# Architecture\n\nOriginal content C.\n",
        }
        for rel, body in self.files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_does_not_overwrite_original_content(self) -> None:
        seed_vault(
            self.root,
            count_per_category=1,
            generator=self.gen,
            rng=random.Random(1),
        )
        for rel, body in self.files.items():
            text = (self.root / rel).read_text()
            self.assertIn(body.strip(), text)

    def test_idempotent_reseed(self) -> None:
        seed_vault(
            self.root,
            count_per_category=1,
            generator=self.gen,
            rng=random.Random(42),
        )
        sizes_after_first = {rel: (self.root / rel).stat().st_size for rel in self.files}
        count_after_first = self.registry.count()
        # Second run should NOT duplicate seeded blocks in any file.
        seed_vault(
            self.root,
            count_per_category=1,
            generator=self.gen,
            rng=random.Random(42),
        )
        for rel in self.files:
            text = (self.root / rel).read_text()
            self.assertEqual(text.count(SEED_SENTINEL), 1)
            # file size grows only by the NEW tokens the generator made,
            # never by re-seeding an already-seeded file.
            self.assertGreaterEqual((self.root / rel).stat().st_size, sizes_after_first[rel])
        self.assertGreater(self.registry.count(), count_after_first)

    def test_scanner_finds_seeded_tokens(self) -> None:
        seed_vault(
            self.root,
            count_per_category=2,
            generator=self.gen,
            rng=random.Random(7),
        )
        scanner = OutboundScanner(self.registry)
        hits = []
        for md in self.root.rglob("*.md"):
            hits.extend(scanner.scan(md.read_text()))
        # Each registered token must appear somewhere in the vault.
        marker_set = set(self.registry.all_markers())
        hit_markers = {h.marker for h in hits}
        self.assertEqual(marker_set, hit_markers)

    def test_missing_vault_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            seed_vault(self.root / "does-not-exist", generator=self.gen)


if __name__ == "__main__":
    unittest.main()
