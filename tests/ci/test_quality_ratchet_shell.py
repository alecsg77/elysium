#!/usr/bin/env python3
"""Behavior tests for the quality-ratchet shell entry point."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/run_quality_ratchet.sh"


class QualityRatchetShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.base = self.root / "base"
        self.head = self.root / "head"
        self.reports = self.root / "reports"
        self.prepare_tree(self.base)
        self.prepare_tree(self.head)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def prepare_tree(self, root: Path) -> None:
        for directory in ("clusters", "infrastructure", "apps", "monitoring", "functions"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / ".yamllint.yaml").write_text(
            "extends: default\n"
            "rules:\n"
            "  document-start: disable\n"
            "  line-length:\n"
            "    max: 10\n"
            "    level: warning\n",
            encoding="utf-8",
        )
        (root / "apps/example.yaml").write_text("value: inherited-long-value\n", encoding="utf-8")

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--tool",
                "yamllint",
                "--base-root",
                str(self.base),
                "--head-root",
                str(self.head),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report-dir",
                str(self.reports),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_unchanged_warning_passes_with_existing_debt(self) -> None:
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads((self.reports / "quality-yamllint.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["state"], "PASS WITH EXISTING DEBT")
        self.assertEqual(payload["counts"]["added"], 0)
        self.assertEqual(payload["counts"]["unchanged"], 1)

    def test_head_configuration_cannot_hide_a_new_warning(self) -> None:
        (self.head / ".yamllint.yaml").write_text("rules:\n  line-length: disable\n", encoding="utf-8")
        (self.head / "clusters/new.yaml").write_text("value: newly-introduced-long-value\n", encoding="utf-8")
        result = self.run_helper()
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads((self.reports / "quality-yamllint.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["state"], "FAIL: NEW DEBT")
        self.assertEqual(payload["counts"]["added"], 1)

    def test_missing_required_option_returns_usage_error(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--tool", "yamllint"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)


if __name__ == "__main__":
    unittest.main()
