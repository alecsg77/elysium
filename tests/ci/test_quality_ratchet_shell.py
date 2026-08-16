#!/usr/bin/env python3
"""Behavior tests for the quality-ratchet shell entry point."""

from __future__ import annotations

import json
import os
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

    def install_fake_kubeconform(self) -> Path:
        executable = self.root / "bin" / "kubeconform"
        executable.parent.mkdir(exist_ok=True)
        executable.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$@\" >> \"${KUBECONFORM_ARGS:?}\"\n"
            "printf '%s\\n' --CALL-- >> \"${KUBECONFORM_ARGS:?}\"\n"
            "printf '%s\\n' '{\"resources\": []}'\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return executable.parent

    def run_kubeconform_helper(self, *schema_arguments: str) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
        binary_dir = self.install_fake_kubeconform()
        arguments_log = self.root / "kubeconform-arguments.txt"
        environment = os.environ | {
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "KUBECONFORM_ARGS": str(arguments_log),
        }
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--tool",
                "kubeconform",
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
                *schema_arguments,
            ],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        calls = []
        if arguments_log.exists():
            calls = [
                call.splitlines()
                for call in arguments_log.read_text(encoding="utf-8").split("--CALL--\n")
                if call
            ]
        return result, calls

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

    def test_proposed_policy_cannot_suppress_existing_warning(self) -> None:
        (self.head / ".yamllint.yaml").write_text("rules:\n  line-length: disable\n", encoding="utf-8")
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--tool",
                "yamllint",
                "--base-root",
                str(self.base),
                "--head-root",
                str(self.head),
                "--head-scan-root",
                str(self.base),
                "--base-config",
                str(self.base / ".yamllint.yaml"),
                "--head-config",
                str(self.head / ".yamllint.yaml"),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report-dir",
                str(self.reports),
                "--reject-removed",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads((self.reports / "quality-yamllint.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["state"], "FAIL: POLICY CHANGES FINDING SET")
        self.assertEqual(payload["counts"]["removed"], 1)

    def test_missing_required_option_returns_usage_error(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--tool", "yamllint"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)

    def test_kubeconform_passes_repeated_schema_locations_in_order(self) -> None:
        result, calls = self.run_kubeconform_helper(
            "--schema-location",
            "local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "--schema-location",
            "catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [
            "-strict",
            "-output",
            "json",
            "-summary",
            "-schema-location",
            "default",
            "-schema-location",
            "local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "-schema-location",
            "catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
        ]
        self.assertEqual(calls, [expected + [str(self.base)], expected + [str(self.head)]])

    def test_kubeconform_policy_comparison_uses_distinct_schema_sets(self) -> None:
        result, calls = self.run_kubeconform_helper(
            "--base-schema-location",
            "base-local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "--base-schema-location",
            "base-catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "--head-schema-location",
            "head-local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "--head-schema-location",
            "head-catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        base_expected = [
            "-strict",
            "-output",
            "json",
            "-summary",
            "-schema-location",
            "default",
            "-schema-location",
            "base-local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "-schema-location",
            "base-catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            str(self.base),
        ]
        head_expected = [
            "-strict",
            "-output",
            "json",
            "-summary",
            "-schema-location",
            "default",
            "-schema-location",
            "head-local/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            "-schema-location",
            "head-catalog/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
            str(self.head),
        ]
        self.assertEqual(calls, [base_expected, head_expected])

    def test_kubeconform_rejects_missing_or_ambiguous_schema_locations(self) -> None:
        missing, _ = self.run_kubeconform_helper()
        self.assertEqual(missing.returncode, 2)
        self.assertIn("requires --schema-location", missing.stderr)

        ambiguous, _ = self.run_kubeconform_helper(
            "--schema-location",
            "catalog",
            "--base-schema-location",
            "base-catalog",
            "--head-schema-location",
            "head-catalog",
        )
        self.assertEqual(ambiguous.returncode, 2)
        self.assertIn("either --schema-location", ambiguous.stderr)


if __name__ == "__main__":
    unittest.main()
