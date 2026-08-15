#!/usr/bin/env python3
"""Unit tests for the trusted base/head quality-ratchet helper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/quality_ratchet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("quality_ratchet", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


QUALITY = load_module()


class QualityRatchetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.base = self.root / "base"
        self.head = self.root / "head"
        self.base.mkdir()
        self.head.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def report(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def kube_report(self, name: str, resources: list[dict]) -> Path:
        path = self.root / name
        path.write_text(json.dumps({"resources": resources}), encoding="utf-8")
        return path

    def checkov_report(self, name: str, failed: list[dict], parsing_errors: list[object] | None = None) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps({"results": {"failed_checks": failed, "parsing_errors": parsing_errors or []}}),
            encoding="utf-8",
        )
        return path

    def test_unchanged_and_removed_findings_pass(self) -> None:
        base = [QUALITY.Finding("one", "one"), QUALITY.Finding("two", "two")]
        head = [QUALITY.Finding("one", "one")]
        state, added, removed, unchanged, _ = QUALITY.summarize("checkov", base, head)
        self.assertEqual(state, "PASS WITH DEBT REDUCTION")
        self.assertFalse(added)
        self.assertEqual(removed, {"two": 1})
        self.assertEqual(unchanged, {"one": 1})

    def test_replacing_a_finding_is_a_regression(self) -> None:
        state, added, removed, _, _ = QUALITY.summarize(
            "checkov", [QUALITY.Finding("old", "old")], [QUALITY.Finding("new", "new")]
        )
        self.assertEqual(state, "FAIL: NEW DEBT")
        self.assertEqual(added, {"new": 1})
        self.assertEqual(removed, {"old": 1})

    def test_yamllint_line_shift_is_not_new_debt(self) -> None:
        self.write(self.base, "apps/example.yaml", "# comment\nvalue: super-secret-value\n")
        self.write(self.head, "apps/example.yaml", "# extra comment\n# comment\nvalue: super-secret-value\n")
        base_report = self.report(
            "base-yamllint.txt", "apps/example.yaml:2:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        head_report = self.report(
            "head-yamllint.txt", "apps/example.yaml:3:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        state, added, removed, _, _ = QUALITY.summarize(
            "yamllint",
            QUALITY.parse_yamllint(base_report, self.base),
            QUALITY.parse_yamllint(head_report, self.head),
        )
        self.assertEqual(state, "PASS WITH EXISTING DEBT")
        self.assertFalse(added)
        self.assertFalse(removed)

    def test_yamllint_changed_offending_line_is_new_debt(self) -> None:
        self.write(self.base, "apps/example.yaml", "value: original-value\n")
        self.write(self.head, "apps/example.yaml", "value: changed-value\n")
        base_report = self.report(
            "base-yamllint.txt", "apps/example.yaml:1:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        head_report = self.report(
            "head-yamllint.txt", "apps/example.yaml:1:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        state, added, _, _, _ = QUALITY.summarize(
            "yamllint",
            QUALITY.parse_yamllint(base_report, self.base),
            QUALITY.parse_yamllint(head_report, self.head),
        )
        self.assertEqual(state, "FAIL: NEW DEBT")
        self.assertEqual(sum(added.values()), 1)

    def test_yamllint_duplicate_occurrence_is_new_debt(self) -> None:
        finding = QUALITY.Finding("same", "same")
        state, added, _, _, _ = QUALITY.summarize("yamllint", [finding], [finding, finding])
        self.assertEqual(state, "FAIL: NEW DEBT")
        self.assertEqual(added, {"same": 1})

    def test_kubeconform_duplicate_render_records_are_deduplicated(self) -> None:
        rendered = self.write(
            self.base,
            "rendered.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\nextra: invalid\n",
        )
        resource = {
            "filename": str(rendered),
            "version": "v1",
            "kind": "ConfigMap",
            "name": "settings",
            "status": "statusInvalid",
            "validationErrors": [{"path": "/extra", "msg": "additional property not allowed"}],
        }
        findings = QUALITY.parse_kubeconform(self.kube_report("kube.json", [resource, resource]), None)
        self.assertEqual(len(findings), 1)
        self.assertIn("ConfigMap/demo/settings", findings[0].display)

    def test_kubeconform_content_variants_are_retained(self) -> None:
        first = self.write(
            self.base,
            "first.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\ndata:\n  value: first\nextra: invalid\n",
        )
        second = self.write(
            self.base,
            "second.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\ndata:\n  value: second\nextra: invalid\n",
        )
        resources = [
            {
                "filename": str(first),
                "version": "v1",
                "kind": "ConfigMap",
                "name": "settings",
                "status": "statusInvalid",
                "validationErrors": [{"path": "/extra", "msg": "additional property not allowed"}],
            },
            {
                "filename": str(second),
                "version": "v1",
                "kind": "ConfigMap",
                "name": "settings",
                "status": "statusInvalid",
                "validationErrors": [{"path": "/extra", "msg": "additional property not allowed"}],
            },
        ]
        findings = QUALITY.parse_kubeconform(self.kube_report("kube.json", resources), None)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all("render_variant=" in finding.identity for finding in findings))

    def test_kubeconform_variant_identity_stays_stable_when_a_sibling_is_removed(self) -> None:
        base_first = self.write(
            self.base,
            "first.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\ndata:\n  value: retained\nextra: invalid\n",
        )
        base_second = self.write(
            self.base,
            "second.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\ndata:\n  value: removed\nextra: invalid\n",
        )
        head_first = self.write(
            self.head,
            "first.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\ndata:\n  value: retained\nextra: invalid\n",
        )

        def resource(path: Path) -> dict:
            return {
                "filename": str(path),
                "version": "v1",
                "kind": "ConfigMap",
                "name": "settings",
                "status": "statusInvalid",
                "validationErrors": [{"path": "/extra", "msg": "additional property not allowed"}],
            }

        state, added, removed, unchanged, _ = QUALITY.summarize(
            "kubeconform",
            QUALITY.parse_kubeconform(self.kube_report("base-kube.json", [resource(base_first), resource(base_second)]), None),
            QUALITY.parse_kubeconform(self.kube_report("head-kube.json", [resource(head_first)]), None),
        )
        self.assertEqual(state, "PASS WITH DEBT REDUCTION")
        self.assertFalse(added)
        self.assertEqual(sum(removed.values()), 1)
        self.assertEqual(sum(unchanged.values()), 1)

    def test_kubeconform_single_document_files_distinguish_reused_namespaces(self) -> None:
        alpha = self.write(
            self.base,
            "alpha/0001.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: alpha\nextra: invalid\n",
        )
        beta = self.write(
            self.base,
            "beta/0001.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: beta\nextra: invalid\n",
        )
        resources = [
            {
                "filename": str(path),
                "version": "v1",
                "kind": "ConfigMap",
                "name": "settings",
                "status": "statusInvalid",
                "validationErrors": [{"path": "/extra", "msg": "additional property not allowed"}],
            }
            for path in (alpha, beta)
        ]
        findings = QUALITY.parse_kubeconform(self.kube_report("kube.json", resources), None)
        self.assertEqual(len(findings), 2)
        self.assertEqual({finding.display for finding in findings}, {"ConfigMap/alpha/settings", "ConfigMap/beta/settings"})

    def test_kubeconform_missing_schema_is_ratchet_debt(self) -> None:
        rendered = self.write(
            self.base,
            "rendered.yaml",
            "apiVersion: example.invalid/v1\nkind: Example\nmetadata:\n  name: sample\n  namespace: demo\n",
        )
        findings = QUALITY.parse_kubeconform(
            self.kube_report(
                "kube.json",
                [
                    {
                        "filename": str(rendered),
                        "version": "example.invalid/v1",
                        "kind": "Example",
                        "name": "sample",
                        "status": "statusError",
                        "msg": "could not find schema for Example",
                    }
                ],
            ),
            None,
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("status=statusMissingSchema", findings[0].identity)

    def test_kubeconform_unexpected_error_fails_closed(self) -> None:
        rendered = self.write(
            self.base,
            "rendered.yaml",
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: demo\n",
        )
        report = self.kube_report(
            "kube.json",
            [
                {
                    "filename": str(rendered),
                    "version": "v1",
                    "kind": "ConfigMap",
                    "name": "settings",
                    "status": "statusError",
                    "msg": "network request failed",
                }
            ],
        )
        with self.assertRaisesRegex(QUALITY.QualityRatchetError, "execution/schema error"):
            QUALITY.parse_kubeconform(report, None)

    def test_kubeconform_execution_error_fails_closed(self) -> None:
        report = self.kube_report(
            "kube.json",
            [
                {
                    "filename": "missing.yaml",
                    "version": "v1",
                    "kind": "ConfigMap",
                    "name": "settings",
                    "status": "statusError",
                }
            ],
        )
        with self.assertRaisesRegex(QUALITY.QualityRatchetError, "unavailable rendered file"):
            QUALITY.parse_kubeconform(report, None)

    def test_checkov_deduplicates_rendered_resource(self) -> None:
        failure = {
            "check_id": "CKV_K8S_22",
            "resource": "Deployment.ai.copilot-api",
            "check_result": {"evaluated_keys": ["spec.template.spec.containers.*.securityContext"]},
        }
        findings = QUALITY.parse_checkov(self.checkov_report("checkov.json", [failure, failure]), None)
        self.assertEqual(len(findings), 1)
        self.assertIn("CKV_K8S_22", findings[0].identity)
        self.assertIn("Deployment/ai/copilot-api", findings[0].display)

    def test_checkov_parsing_error_fails_closed(self) -> None:
        report = self.checkov_report("checkov.json", [], parsing_errors=["bad manifest"])
        with self.assertRaisesRegex(QUALITY.QualityRatchetError, "parsing errors"):
            QUALITY.parse_checkov(report, None)

    def test_checkov_report_missing_failed_checks_fails_closed(self) -> None:
        report = self.report("checkov.json", json.dumps({"results": {"parsing_errors": []}}))
        with self.assertRaisesRegex(QUALITY.QualityRatchetError, "missing failed_checks"):
            QUALITY.parse_checkov(report, None)

    def test_checkov_report_missing_parsing_errors_is_treated_as_empty(self) -> None:
        report = self.report("checkov.json", json.dumps({"results": {"failed_checks": []}}))
        self.assertEqual(QUALITY.parse_checkov(report, None), [])

    def test_checkov_report_invalid_parsing_errors_fails_closed(self) -> None:
        report = self.report("checkov.json", json.dumps({"results": {"failed_checks": [], "parsing_errors": {}}}))
        with self.assertRaisesRegex(QUALITY.QualityRatchetError, "invalid parsing_errors"):
            QUALITY.parse_checkov(report, None)

    def test_reject_removed_marks_policy_suppression_as_failure(self) -> None:
        base = self.report(
            "base-yamllint.txt", "apps/example.yaml:1:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        head = self.report("head-yamllint.txt", "")
        self.write(self.base, "apps/example.yaml", "value: inherited-long-value\n")
        self.write(self.head, "apps/example.yaml", "value: inherited-long-value\n")
        output = self.root / "policy.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--tool",
                "yamllint",
                "--base-report",
                str(base),
                "--head-report",
                str(head),
                "--base-root",
                str(self.base),
                "--head-root",
                str(self.head),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report",
                str(output),
                "--reject-removed",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["state"], "FAIL: POLICY CHANGES FINDING SET")

    def test_cli_writes_redacted_report_and_fails_for_new_debt(self) -> None:
        self.write(self.base, "apps/example.yaml", "value: inherited-secret\n")
        self.write(self.head, "apps/example.yaml", "value: new-secret\n")
        base_report = self.report(
            "base-yamllint.txt", "apps/example.yaml:1:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        head_report = self.report(
            "head-yamllint.txt", "apps/example.yaml:1:1: [warning] line too long (130 > 120 characters) (line-length)\n"
        )
        output = self.root / "quality-report.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--tool",
                "yamllint",
                "--base-report",
                str(base_report),
                "--head-report",
                str(head_report),
                "--base-root",
                str(self.base),
                "--head-root",
                str(self.head),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        content = output.read_text(encoding="utf-8")
        self.assertIn("FAIL: NEW DEBT", content)
        self.assertNotIn("new-secret", content)
        self.assertNotIn("inherited-secret", content)

    def test_checkov_report_does_not_persist_code_blocks(self) -> None:
        base_report = self.checkov_report("base-checkov.json", [])
        head_report = self.checkov_report(
            "head-checkov.json",
            [
                {
                    "check_id": "CKV_K8S_22",
                    "resource": "Deployment.ai.example",
                    "check_result": {"evaluated_keys": ["spec.template.spec.containers"]},
                    "code_block": [[1, "token: checkov-secret-value\\n"]],
                }
            ],
        )
        output = self.root / "quality-checkov.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--tool",
                "checkov",
                "--base-report",
                str(base_report),
                "--head-report",
                str(head_report),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        content = output.read_text(encoding="utf-8")
        self.assertNotIn("checkov-secret-value", content)
        self.assertNotIn("code_block", content)

    def test_cli_rejects_unexpected_scanner_exit_code(self) -> None:
        report = self.report("empty.txt", "")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--tool",
                "yamllint",
                "--base-report",
                str(report),
                "--head-report",
                str(report),
                "--base-root",
                str(self.base),
                "--head-root",
                str(self.head),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--base-exit-code",
                "2",
                "--report",
                str(self.root / "result.json"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exited 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
