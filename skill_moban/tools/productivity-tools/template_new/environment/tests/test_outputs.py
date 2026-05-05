#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from digest_oracle import APP_ROOT, build_expected_digest, render_markdown

OUTPUT_JSON = APP_ROOT / "output" / "feed_digest.json"
OUTPUT_MD = APP_ROOT / "output" / "feed_digest.md"


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert OUTPUT_JSON.exists(), "missing /app/output/feed_digest.json"
        assert OUTPUT_MD.exists(), "missing /app/output/feed_digest.md"
        cls.actual = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        cls.expected = build_expected_digest()
        cls.markdown = OUTPUT_MD.read_text(encoding="utf-8")

    def test_checkpoint_matches(self) -> None:
        self.assertEqual(self.actual["checkpoint_used"], self.expected["checkpoint_used"])

    def test_relevant_item_core_fields(self) -> None:
        actual_rows = sorted(
            [
            {
                key: row[key]
                for key in ["id", "title", "canonical_url", "published_at", "sources", "priority", "topic"]
            }
            for row in self.actual["new_relevant_items"]
            ],
            key=lambda row: (row["published_at"], row["canonical_url"], row["id"]),
            reverse=True,
        )
        expected_rows = sorted(
            [
            {
                key: row[key]
                for key in ["id", "title", "canonical_url", "published_at", "sources", "priority", "topic"]
            }
            for row in self.expected["new_relevant_items"]
            ],
            key=lambda row: (row["published_at"], row["canonical_url"], row["id"]),
            reverse=True,
        )
        self.assertEqual(actual_rows, expected_rows)

    def test_skipped_item_core_fields(self) -> None:
        actual_rows = sorted(
            [
            {key: row[key] for key in ["title", "canonical_url", "sources", "skip_reason"]}
            for row in self.actual["skipped_items"]
            ],
            key=lambda row: (row["canonical_url"], row["title"], row["skip_reason"], tuple(row["sources"])),
        )
        expected_rows = sorted(
            [
            {key: row[key] for key in ["title", "canonical_url", "sources", "skip_reason"]}
            for row in self.expected["skipped_items"]
            ],
            key=lambda row: (row["canonical_url"], row["title"], row["skip_reason"], tuple(row["sources"])),
        )
        self.assertEqual(actual_rows, expected_rows)

    def test_summary_and_relevance_are_present(self) -> None:
        for row in self.actual["new_relevant_items"]:
            self.assertIsInstance(row["summary"], str)
            self.assertGreaterEqual(len(row["summary"].strip()), 20)
            self.assertIsInstance(row["why_relevant"], str)
            self.assertGreaterEqual(len(row["why_relevant"].strip()), 20)

    def test_markdown_sections_exist(self) -> None:
        self.assertTrue(self.markdown.startswith("# Developer Productivity Feed Brief"))
        for heading in ["## High Priority", "## Medium Priority", "## Low Priority"]:
            self.assertIn(heading, self.markdown)

    def test_markdown_contains_each_item_once(self) -> None:
        for row in self.expected["new_relevant_items"]:
            matching_lines = [
                line
                for line in self.markdown.splitlines()
                if line.startswith("- ") and row["title"] in line
            ]
            self.assertEqual(len(matching_lines), 1)

    def test_markdown_priority_placement(self) -> None:
        lines = self.markdown.splitlines()
        sections: dict[str, list[str]] = {"high": [], "medium": [], "low": []}
        current = None
        for line in lines:
            if line == "## High Priority":
                current = "high"
                continue
            if line == "## Medium Priority":
                current = "medium"
                continue
            if line == "## Low Priority":
                current = "low"
                continue
            if current and line.startswith("- "):
                sections[current].append(line)

        for item in self.expected["new_relevant_items"]:
            section_lines = sections[item["priority"]]
            self.assertTrue(any(item["title"] in line for line in section_lines))


if __name__ == "__main__":
    unittest.main()
