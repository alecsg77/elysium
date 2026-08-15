#!/usr/bin/env python3
"""Unit tests for trusted Checkov report normalization."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/normalize_checkov_reports.py"


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_checkov_reports", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


NORMALIZER = load_module()


class NormalizeCheckovReportsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def report(self, name: str, payload: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_missing_parsing_errors_is_normalized_to_empty_list(self) -> None:
        report = self.report("checkov.json", {"results": {"failed_checks": []}})

        NORMALIZER.normalize_report(report)

        self.assertEqual(
            json.loads(report.read_text(encoding="utf-8")),
            {"results": {"failed_checks": [], "parsing_errors": []}},
        )

    def test_existing_empty_parsing_errors_is_preserved(self) -> None:
        report = self.report("checkov.json", {"results": {"failed_checks": [], "parsing_errors": []}})

        NORMALIZER.normalize_report(report)

        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["results"]["parsing_errors"], [])

    def test_missing_results_object_fails_closed(self) -> None:
        report = self.report("checkov.json", {})

        with self.assertRaisesRegex(NORMALIZER.CheckovReportError, "no results object"):
            NORMALIZER.normalize_report(report)

    def test_missing_failed_checks_list_fails_closed(self) -> None:
        report = self.report("checkov.json", {"results": {}})

        with self.assertRaisesRegex(NORMALIZER.CheckovReportError, "invalid failed_checks"):
            NORMALIZER.normalize_report(report)

    def test_non_list_parsing_errors_fails_closed(self) -> None:
        report = self.report("checkov.json", {"results": {"failed_checks": [], "parsing_errors": {}}})

        with self.assertRaisesRegex(NORMALIZER.CheckovReportError, "invalid parsing_errors"):
            NORMALIZER.normalize_report(report)

    def test_non_empty_parsing_errors_fails_closed(self) -> None:
        report = self.report("checkov.json", {"results": {"failed_checks": [], "parsing_errors": ["invalid manifest"]}})

        with self.assertRaisesRegex(NORMALIZER.CheckovReportError, "contains parsing errors"):
            NORMALIZER.normalize_report(report)


if __name__ == "__main__":
    unittest.main()
