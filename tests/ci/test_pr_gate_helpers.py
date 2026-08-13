#!/usr/bin/env python3
"""Regression tests for trusted PR Gate helper behavior."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/ci"


def load_module(filename: str):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DOMAINS = load_module("detect_pr_gate_domains.py")
SECRETS = load_module("check_changed_secrets.py")


class DomainDetectionTest(unittest.TestCase):
    def test_docs_only_change_skips_conditional_domains(self) -> None:
        self.assertEqual(
            DOMAINS.classify_paths(["docs/ci/pr-validation.md"]),
            {"gitops": False, "helm": False, "coder": False, "actions": False, "functions": False},
        )

    def test_tier_zero_helper_change_forces_every_domain(self) -> None:
        self.assertEqual(
            DOMAINS.classify_paths(["scripts/ci/check_changed_secrets.py"]),
            {"gitops": True, "helm": True, "coder": True, "actions": True, "functions": True},
        )

    def test_domains_are_classified_independently(self) -> None:
        self.assertEqual(
            DOMAINS.classify_paths(["apps/base/example/release.yaml", "charts/onechart/values.yaml", "functions/f.yaml"]),
            {"gitops": True, "helm": True, "coder": False, "actions": False, "functions": True},
        )


class ChangedSecretsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.run_git("init")
        self.run_git("config", "user.email", "ci@example.invalid")
        self.run_git("config", "user.name", "CI Test")
        (self.repo / "apps/base/example").mkdir(parents=True)
        (self.repo / "apps/base/example/config.yaml").write_text("kind: ConfigMap\n", encoding="utf-8")
        self.commit("base")
        self.base_sha = self.run_git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments], cwd=self.repo, text=True, capture_output=True, check=True
        )

    def commit(self, message: str) -> None:
        self.run_git("add", ".")
        self.run_git("commit", "-m", message)

    def run_checker(self) -> subprocess.CompletedProcess[str]:
        head_sha = self.run_git("rev-parse", "HEAD").stdout.strip()
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_changed_secrets.py"),
                "--repo",
                str(self.repo),
                "--base-sha",
                self.base_sha,
                "--head-sha",
                head_sha,
                "--pr-number",
                "1",
                "--skip-fetch",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_and_commit(self, relative: str, content: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.commit("change")

    def test_safe_yaml_passes(self) -> None:
        self.write_and_commit("apps/base/example/config.yaml", "kind: ConfigMap\nmetadata:\n  name: safe\n")
        self.assertEqual(self.run_checker().returncode, 0)

    def test_plaintext_secret_fails(self) -> None:
        self.write_and_commit("apps/base/example/secret.yaml", "apiVersion: v1\nkind: Secret\nmetadata:\n  name: forbidden\n")
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bare kind: Secret manifest", result.stderr)

    def test_nested_secret_fails(self) -> None:
        self.write_and_commit("apps/base/example/nested.yaml", "items:\n  - kind: Secret\n    metadata:\n      name: forbidden\n")
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bare kind: Secret manifest", result.stderr)

    def test_exact_controller_token_exception_passes(self) -> None:
        self.write_and_commit(
            "infrastructure/configs/ci/copilot-agent-rbac/secret.yaml",
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: copilot-agent-readonly-token\n  namespace: arc-runners\n  annotations:\n    kubernetes.io/service-account.name: copilot-agent-readonly\ntype: kubernetes.io/service-account-token\n",
        )
        self.assertEqual(self.run_checker().returncode, 0)

    def test_controller_token_exception_with_data_fails(self) -> None:
        self.write_and_commit(
            "infrastructure/configs/ci/copilot-agent-rbac/secret.yaml",
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: copilot-agent-readonly-token\n  namespace: arc-runners\n  annotations:\n    kubernetes.io/service-account.name: copilot-agent-readonly\ntype: kubernetes.io/service-account-token\ndata:\n  token: dGVzdA==\n",
        )
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bare kind: Secret manifest", result.stderr)

    def test_duplicate_yaml_key_fails_closed(self) -> None:
        self.write_and_commit("apps/base/example/duplicate.yaml", "kind: ConfigMap\nkind: Secret\n")
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not parse changed YAML", result.stderr)


class YAMLPathParserTest(unittest.TestCase):
    def test_parser_rejects_missing_directory(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "parse_yaml_paths.py"), "--root", str(ROOT), "--directory", "missing"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("YAML directory is missing", completed.stderr)


if __name__ == "__main__":
    unittest.main()
