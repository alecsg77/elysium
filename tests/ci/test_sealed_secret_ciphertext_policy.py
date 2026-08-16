#!/usr/bin/env python3
"""Focused boundary tests for SealedSecret ciphertext CI policy."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/sealed_secret_ciphertext_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sealed_secret_ciphertext_policy", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


POLICY = load_module()


class CiphertextStructureTest(unittest.TestCase):
    def redact(self, content: str) -> list[str]:
        ranges = POLICY.ciphertext_ranges(content)
        return [POLICY.redact_line(line, number, ranges) for number, line in enumerate(content.splitlines(), start=1)]

    def test_only_exact_sealed_secret_encrypted_data_scalar_is_redacted(self) -> None:
        content = """apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  annotations:
    token: metadata-token-marker
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-marker # an outside comment marker
  template:
    metadata:
      name: demo
"""
        redacted = self.redact(content)
        self.assertIn("    SERVICE_TOKEN: <sealed-secret-ciphertext> # an outside comment marker", redacted)
        self.assertIn("    token: metadata-token-marker", redacted)
        self.assertNotIn("ciphertext-marker", "\n".join(redacted))
        self.assertIn("SERVICE_TOKEN", "\n".join(redacted))

    def test_plaintext_secret_and_nonmatching_kind_are_not_redacted(self) -> None:
        for kind in ("Secret", "sealedsecret"):
            content = f"""apiVersion: v1
kind: {kind}
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-marker
"""
            self.assertEqual(POLICY.ciphertext_ranges(content), [])

    def test_other_sealed_secret_fields_and_nested_documents_are_not_redacted(self) -> None:
        content = """apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: ciphertext-marker
spec:
  template:
    metadata:
      annotations:
        token: ciphertext-marker
---
items:
  - kind: SealedSecret
    spec:
      encryptedData:
        SERVICE_TOKEN: ciphertext-marker
"""
        self.assertEqual(POLICY.ciphertext_ranges(content), [])

    def test_malformed_duplicate_and_alias_input_fail_closed(self) -> None:
        malformed = """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: [ciphertext-marker
"""
        duplicate_root = """kind: SealedSecret
kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-marker
"""
        duplicate_encrypted_data_key = """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-marker
    SERVICE_TOKEN: different-ciphertext-marker
"""
        duplicate_metadata_key = """kind: SealedSecret
metadata:
  name: first
  name: second
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-marker
"""
        alias = """kind: SealedSecret
metadata:
  annotations:
    source: &ciphertext ciphertext-marker
spec:
  encryptedData:
    SERVICE_TOKEN: *ciphertext
"""
        for content in (malformed, duplicate_root, duplicate_encrypted_data_key, duplicate_metadata_key, alias):
            self.assertEqual(POLICY.ciphertext_ranges(content), [])

    def test_block_scalar_value_keeps_the_key_and_redacts_its_content(self) -> None:
        content = """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: |
      ciphertext-first-marker
      ciphertext-second-marker
"""
        redacted = self.redact(content)
        self.assertEqual(redacted[3], "    SERVICE_TOKEN: <sealed-secret-ciphertext>")
        self.assertEqual(redacted[4], "<sealed-secret-ciphertext>")
        self.assertEqual(redacted[5], "<sealed-secret-ciphertext>")


class FilteredDiffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.run_git("init")
        self.run_git("config", "user.email", "ci@example.invalid")
        self.run_git("config", "user.name", "CI Test")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *arguments], cwd=self.repo, text=True, capture_output=True, check=True)

    def write_and_commit(self, content: str, message: str) -> str:
        path = self.repo / "apps/example/secret.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-m", message)
        return self.run_git("rev-parse", "HEAD").stdout.strip()

    def test_diff_hides_only_rotated_sealed_secret_ciphertext(self) -> None:
        base = self.write_and_commit(
            """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-before-marker
""",
            "base",
        )
        head = self.write_and_commit(
            """kind: SealedSecret
metadata:
  annotations:
    token: outside-token-marker
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-after-marker
""",
            "head",
        )
        filtered = "\n".join(POLICY.filtered_added_lines(self.repo, base, head))
        self.assertIn("    SERVICE_TOKEN: <sealed-secret-ciphertext>", filtered)
        self.assertIn("outside-token-marker", filtered)
        self.assertNotIn("ciphertext-after-marker", filtered)

    def test_cli_does_not_print_or_write_recognized_ciphertext(self) -> None:
        base = self.write_and_commit(
            """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-before-marker
""",
            "base",
        )
        head = self.write_and_commit(
            """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: ciphertext-after-marker
""",
            "head",
        )
        output = self.repo / "filtered.diff"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "filter-added-diff",
                "--repo",
                str(self.repo),
                "--base-sha",
                base,
                "--head-sha",
                head,
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        filtered = output.read_text(encoding="utf-8")
        self.assertIn("SERVICE_TOKEN: <sealed-secret-ciphertext>", filtered)
        self.assertNotIn("ciphertext-after-marker", filtered)

    def test_diff_forces_text_when_proposed_attributes_disable_yaml_diffs(self) -> None:
        base = self.write_and_commit("kind: ConfigMap\n", "base")
        (self.repo / ".gitattributes").write_text("*.yaml -diff\n", encoding="utf-8")
        (self.repo / "apps/example/secret.yaml").write_text(
            """kind: Secret
spec:
  encryptedData:
    SERVICE_TOKEN: plaintext-token-marker
""",
            encoding="utf-8",
        )
        self.run_git("add", ".")
        self.run_git("commit", "-m", "attributes")
        head = self.run_git("rev-parse", "HEAD").stdout.strip()
        filtered = "\n".join(POLICY.filtered_added_lines(self.repo, base, head))
        self.assertIn("plaintext-token-marker", filtered)

    def test_diff_keeps_plaintext_secret_and_malformed_yaml_visible(self) -> None:
        base = self.write_and_commit("kind: ConfigMap\n", "base")
        head = self.write_and_commit(
            """kind: Secret
spec:
  encryptedData:
    SERVICE_TOKEN: plaintext-token-marker
""",
            "plaintext",
        )
        plaintext = "\n".join(POLICY.filtered_added_lines(self.repo, base, head))
        self.assertIn("plaintext-token-marker", plaintext)

        malformed_base = head
        malformed_head = self.write_and_commit(
            """kind: SealedSecret
spec:
  encryptedData:
    SERVICE_TOKEN: malformed-token-marker
    invalid: [
""",
            "malformed",
        )
        malformed = "\n".join(POLICY.filtered_added_lines(self.repo, malformed_base, malformed_head))
        self.assertIn("malformed-token-marker", malformed)


if __name__ == "__main__":
    unittest.main()
