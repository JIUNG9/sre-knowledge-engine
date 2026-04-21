"""Precision/recall tests for the outbound scanner."""

from __future__ import annotations

import os
import random
import string
import sys
import tempfile
import unittest

_THIS = os.path.dirname(os.path.abspath(__file__))
_AI_ENGINE = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _AI_ENGINE not in sys.path:
    sys.path.insert(0, _AI_ENGINE)

from honeytokens.generator import HoneyTokenGenerator  # noqa: E402
from honeytokens.registry import HoneyTokenRegistry  # noqa: E402
from honeytokens.scanner import OutboundScanner  # noqa: E402


def _noise(n: int, seed: int = 1) -> str:
    rng = random.Random(seed)
    alph = string.ascii_letters + string.digits + " \n\t.,:;/_-"
    return "".join(rng.choice(alph) for _ in range(n))


class ScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "honey.db")
        self.registry = HoneyTokenRegistry(self.db)
        self.gen = HoneyTokenGenerator(self.registry)
        self.scanner = OutboundScanner(self.registry)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_recall_single_token(self) -> None:
        t = self.gen.create("api_key")
        self.scanner.invalidate()
        haystack = _noise(5_000) + t.value + _noise(5_000)
        hits = self.scanner.scan(haystack)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].marker, t.marker)
        self.assertEqual(hits[0].category, "api_key")

    def test_recall_many_tokens(self) -> None:
        tokens = [self.gen.create("email") for _ in range(20)]
        self.scanner.invalidate()
        hay = "\n".join(_noise(200) + t.value + _noise(200) for t in tokens)
        hits = self.scanner.scan(hay)
        self.assertEqual(len(hits), len(tokens))
        self.assertEqual({h.marker for h in hits}, {t.marker for t in tokens})

    def test_precision_no_false_positives(self) -> None:
        self.gen.create("aws_key")
        self.scanner.invalidate()
        # 100KB of unrelated noise, including a fake AKIA... key that is
        # NOT one of ours.
        hay = _noise(100_000) + "\nAKIAFAKEFAKEFAKEFAKE" + _noise(100_000)
        self.assertEqual(self.scanner.scan(hay), [])

    def test_empty_registry_returns_empty(self) -> None:
        self.scanner.invalidate()
        self.assertEqual(self.scanner.scan("AEGIS-HONEY-000000000000 anywhere"), [])

    def test_invalidate_picks_up_new_tokens(self) -> None:
        t1 = self.gen.create("hostname")
        self.scanner.invalidate()
        self.assertEqual(len(self.scanner.scan(t1.value)), 1)
        t2 = self.gen.create("hostname")
        self.scanner.invalidate()
        combined = t1.value + "\n" + t2.value
        self.assertEqual({h.marker for h in self.scanner.scan(combined)}, {t1.marker, t2.marker})

    def test_context_includes_marker(self) -> None:
        t = self.gen.create("db_password")
        self.scanner.invalidate()
        hits = self.scanner.scan("header line\n" + t.value + "\nfooter line")
        self.assertEqual(len(hits), 1)
        self.assertIn(t.marker, hits[0].context)


if __name__ == "__main__":
    unittest.main()
