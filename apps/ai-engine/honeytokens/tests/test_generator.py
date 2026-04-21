"""Tests for the honey-token generator."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

# Make `apps/ai-engine` importable when run from any working dir.
_THIS = os.path.dirname(os.path.abspath(__file__))
_AI_ENGINE = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _AI_ENGINE not in sys.path:
    sys.path.insert(0, _AI_ENGINE)

from honeytokens.generator import (  # noqa: E402
    MARKER_PREFIX,
    HoneyTokenGenerator,
)
from honeytokens.registry import HoneyTokenRegistry  # noqa: E402


class GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "honey.db")
        self.registry = HoneyTokenRegistry(self.db)
        self.gen = HoneyTokenGenerator(self.registry)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_marker_prefix_on_every_category(self) -> None:
        for cat in self.gen.all_categories():
            t = self.gen.create(cat)
            self.assertTrue(t.marker.startswith(MARKER_PREFIX))
            self.assertIn(t.marker, t.value, f"marker missing in {cat} value")
            self.assertEqual(len(t.marker), len(MARKER_PREFIX) + 12)

    def test_uniqueness_across_many_tokens(self) -> None:
        markers = set()
        fingerprints = set()
        for _ in range(250):
            t = self.gen.create("api_key")
            self.assertNotIn(t.marker, markers)
            self.assertNotIn(t.fingerprint, fingerprints)
            markers.add(t.marker)
            fingerprints.add(t.fingerprint)

    def test_invalid_category_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.gen.create("not_a_category")  # type: ignore[arg-type]

    def test_persisted_across_registry_instances(self) -> None:
        t = self.gen.create("aws_key")
        fresh = HoneyTokenRegistry(self.db)
        meta = fresh.get_by_marker(t.marker)
        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertEqual(meta["category"], "aws_key")
        self.assertEqual(meta["value"], t.value)

    def test_category_specific_formatting(self) -> None:
        aws = self.gen.create("aws_key").value
        self.assertIn("AKIA", aws)
        email = self.gen.create("email").value
        self.assertIn("@aegis-honey.internal", email)
        pem = self.gen.create("pem_block").value
        self.assertIn("BEGIN RSA PRIVATE KEY", pem)
        self.assertIn("END RSA PRIVATE KEY", pem)


if __name__ == "__main__":
    unittest.main()
