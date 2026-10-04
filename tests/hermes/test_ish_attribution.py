# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Keep repository-level authorship and license notices aligned."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AttributionTests(unittest.TestCase):
    def test_authors_notice_covers_ai_generated_glue_and_customizations(self) -> None:
        authors = (ROOT / "AUTHORS").read_text(encoding="utf-8")
        self.assertIn("glue", authors)
        self.assertIn("Blink modifications", authors)
        self.assertIn("generated with\nAI assistance", authors)

    def test_copying_lists_upstream_component_license_links(self) -> None:
        copying = (ROOT / "COPYING").read_text(encoding="utf-8")
        for component in (
            "Hermes Agent", "Hermes WebUI", "Blink Shell", "a-Shell",
            "CPython", "iSH", "ios_system",
        ):
            with self.subTest(component=component):
                self.assertIn(component, copying)
        self.assertNotIn("LICENSES/", copying)

    def test_file_by_file_ai_inventory_is_retired(self) -> None:
        self.assertFalse((ROOT / "AI-GENERATED-FILES.md").exists())


if __name__ == "__main__":
    unittest.main()
