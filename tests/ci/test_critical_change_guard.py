#!/usr/bin/env python3
"""Regression tests for the trusted-base critical GitOps guard."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts/ci/critical_change_guard.py"
POLICY = ROOT / ".github/critical-resources.yaml"


class CriticalChangeGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name) / "base"
        self.head = Path(self.tempdir.name) / "head"
        # Terraform validation may create provider state below Coder templates.
        # Test fixtures copy only repository inputs, never generated runtime state.
        ignore = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".coder", ".terraform")
        shutil.copytree(ROOT, self.base, ignore=ignore)
        shutil.copytree(ROOT, self.head, ignore=ignore)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_guard(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(GUARD),
                "--base",
                str(self.base),
                "--head",
                str(self.head),
                "--policy",
                str(self.base / POLICY.relative_to(ROOT)),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_identical_trees_pass(self) -> None:
        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_missing_root_composition_fails(self) -> None:
        (self.head / "clusters/kyrion/kustomization.yaml").unlink()
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("protected file is missing or renamed", completed.stdout)

    def test_semantic_connector_removal_fails_without_intent(self) -> None:
        kustomization = self.head / "infrastructure/configs/tailscale/kustomization.yaml"
        kustomization.write_text(
            kustomization.read_text(encoding="utf-8").replace("  - connector.yaml\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("tailscale/connector remove", completed.stdout)
        self.assertIn("missing prior intent", completed.stdout)

    def test_consumed_intent_allows_connector_removal(self) -> None:
        intent_dir = self.base / ".github/critical-removal-intents"
        intent_dir.mkdir(parents=True, exist_ok=True)
        intent = {
            "resource": "tailscale/connector",
            "operation": "remove",
            "backup": "Not applicable: Connector has no persistent data.",
            "rollback": "Restore connector.yaml from the preceding known-good commit.",
        }
        intent_path = intent_dir / "tailscale__connector.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        shutil.copy2(intent_path, self.head / intent_path.relative_to(self.base))

        kustomization = self.head / "infrastructure/configs/tailscale/kustomization.yaml"
        kustomization.write_text(
            kustomization.read_text(encoding="utf-8").replace("  - connector.yaml\n", ""),
            encoding="utf-8",
        )
        (self.head / ".github/critical-removal-intents/tailscale__connector.yaml").unlink()

        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("permitted by a prior", completed.stdout)

    def test_copilot_api_removal_requires_intents_for_every_rendered_resource(self) -> None:
        kustomization = self.head / "apps/kyrion/ai/kustomization.yaml"
        kustomization.write_text(
            kustomization.read_text(encoding="utf-8")
            .replace("  - ../../base/copilot-api\n", "")
            .replace("  - copilot-api-sealed-secret.yaml\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        for resource_id in (
            "storage/copilot-api-pvc",
            "workload/copilot-api-deployment",
            "access/copilot-api-service",
            "access/copilot-api-ingress",
            "credentials/copilot-api",
        ):
            self.assertIn(f"{resource_id} remove", completed.stdout)
            self.assertIn("missing prior intent", completed.stdout)

    def test_bootstrap_dependency_change_fails_without_intent(self) -> None:
        manifest = self.head / "clusters/kyrion/apps.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace("  dependsOn:\n    - name: infra-configs\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("bootstrap/apps spec.dependsOn", completed.stdout)
        self.assertIn("missing prior intent", completed.stdout)

    def test_prune_deprotection_requires_new_intent(self) -> None:
        manifest = self.head / "clusters/kyrion/apps.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "    kustomize.toolkit.fluxcd.io/prune: disabled\n", ""
            ),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing preparation intent", completed.stdout)

    def test_prune_deprotection_with_new_intent_passes(self) -> None:
        manifest = self.head / "clusters/kyrion/apps.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "    kustomize.toolkit.fluxcd.io/prune: disabled\n", ""
            ),
            encoding="utf-8",
        )
        intent = {
            "resource": "bootstrap/apps",
            "operation": "remove",
            "backup": "Not applicable: this Kustomization has no persistent payload.",
            "rollback": "Restore apps.yaml from the known-good commit.",
        }
        intent_path = self.head / ".github/critical-removal-intents/bootstrap__apps.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("preparation intent", completed.stdout)

    def test_new_intent_requires_complete_machine_readable_evidence(self) -> None:
        intent = {
            "resource": "tailscale/connector",
            "operation": "remove",
            "backup": "",
            "rollback": "Restore connector.yaml from the known-good commit.",
        }
        intent_path = self.head / ".github/critical-removal-intents/tailscale__connector.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("has no backup evidence", completed.stdout)

    def test_consumed_intent_requires_matching_r2_operation(self) -> None:
        intent_dir = self.base / ".github/critical-removal-intents"
        intent_dir.mkdir(parents=True, exist_ok=True)
        intent = {
            "resource": "tailscale/connector",
            "operation": "change",
            "backup": "Not applicable: Connector has no persistent data.",
            "rollback": "Restore connector.yaml from the preceding known-good commit.",
        }
        intent_path = intent_dir / "tailscale__connector.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        shutil.copy2(intent_path, self.head / intent_path.relative_to(self.base))
        (self.head / ".github/critical-removal-intents/tailscale__connector.yaml").unlink()

        kustomization = self.head / "infrastructure/configs/tailscale/kustomization.yaml"
        kustomization.write_text(
            kustomization.read_text(encoding="utf-8").replace("  - connector.yaml\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("expected 'remove'", completed.stdout)

    def test_consumed_intent_requires_a_matching_r2_change(self) -> None:
        intent_dir = self.base / ".github/critical-removal-intents"
        intent_dir.mkdir(parents=True, exist_ok=True)
        intent = {
            "resource": "tailscale/connector",
            "operation": "remove",
            "backup": "Not applicable: Connector has no persistent data.",
            "rollback": "Restore connector.yaml from the preceding known-good commit.",
        }
        intent_path = intent_dir / "tailscale__connector.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        shutil.copy2(intent_path, self.head / intent_path.relative_to(self.base))
        (self.head / ".github/critical-removal-intents/tailscale__connector.yaml").unlink()

        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("consumed without a matching R2 operation", completed.stdout)

    def test_new_change_intent_with_evidence_is_allowed(self) -> None:
        intent = {
            "resource": "system-upgrade/plan-crd",
            "operation": "change",
            "backup": "Plan inventory and CRD backup reference before migration.",
            "rollback": "Restore the prior pinned CRD artifact from the known-good commit.",
        }
        intent_path = self.head / ".github/critical-removal-intents/system-upgrade__plan-crd.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_existing_intent_cannot_be_modified(self) -> None:
        intent_dir = self.base / ".github/critical-removal-intents"
        intent_dir.mkdir(parents=True, exist_ok=True)
        intent_path = intent_dir / "tailscale__connector.yaml"
        intent_path.write_text(
            yaml.safe_dump(
                {
                    "resource": "tailscale/connector",
                    "operation": "remove",
                    "backup": "Not applicable: Connector has no persistent data.",
                    "rollback": "Restore connector.yaml from the known-good commit.",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        head_intent = self.head / intent_path.relative_to(self.base)
        shutil.copy2(intent_path, head_intent)
        head_intent.write_text(
            head_intent.read_text(encoding="utf-8").replace(
                "Restore connector.yaml", "Replace the recovery procedure"
            ),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("existing R2 intent must not be modified", completed.stdout)

    def test_nested_remote_base_fails_before_rendering(self) -> None:
        nested = self.head / "apps/base/apprise-api/kustomization.yaml"
        nested.write_text(
            nested.read_text(encoding="utf-8").replace(
                "  - apprise-api.yaml\n",
                "  - apprise-api.yaml\n  - https://example.invalid/untrusted.yaml\n",
            ),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("remote resources entry", completed.stdout)

    def test_system_upgrade_crd_removal_fails_without_intent(self) -> None:
        kustomization = self.head / "infrastructure/controllers/system-upgrade/kustomization.yaml"
        kustomization.write_text(
            kustomization.read_text(encoding="utf-8").replace("  - crd.yaml\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("system-upgrade/plan-crd remove", completed.stdout)
        self.assertIn("missing prior intent", completed.stdout)

    def test_system_upgrade_crd_schema_change_fails_without_intent(self) -> None:
        manifest = self.head / "infrastructure/controllers/system-upgrade/crd.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace("  group: upgrade.cattle.io\n", "  group: unsafe.example\n", 1),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("system-upgrade/plan-crd change", completed.stdout)
        self.assertIn("missing prior intent", completed.stdout)

    def test_consumed_intent_allows_system_upgrade_crd_schema_change(self) -> None:
        intent_dir = self.base / ".github/critical-removal-intents"
        intent_dir.mkdir(parents=True, exist_ok=True)
        intent = {
            "resource": "system-upgrade/plan-crd",
            "operation": "change",
            "backup": "Plan inventory and CRD backup reference before migration.",
            "rollback": "Restore the prior pinned CRD artifact from the known-good commit.",
        }
        intent_path = intent_dir / "system-upgrade__plan-crd.yaml"
        intent_path.write_text(yaml.safe_dump(intent, sort_keys=False), encoding="utf-8")
        shutil.copy2(intent_path, self.head / intent_path.relative_to(self.base))

        manifest = self.head / "infrastructure/controllers/system-upgrade/crd.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace("  group: upgrade.cattle.io\n", "  group: upgraded.example\n", 1),
            encoding="utf-8",
        )
        (self.head / ".github/critical-removal-intents/system-upgrade__plan-crd.yaml").unlink()

        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("permitted by a prior", completed.stdout)

    def test_tier0_change_cannot_accompany_critical_change(self) -> None:
        policy = self.head / ".github/critical-resources.yaml"
        policy.write_text(policy.read_text(encoding="utf-8") + "\n# attempted weakening\n", encoding="utf-8")
        manifest = self.head / "clusters/kyrion/apps.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace("    - name: infra-configs\n", ""),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Tier 0 enforcement paths changed", completed.stdout)

    def test_safe_hardening_can_add_orphan_without_intent(self) -> None:
        manifest = self.base / "clusters/kyrion/apps.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "  # Orphan managed resources if this Kustomization object is deleted; normal\n"
                "  # source reconciliation still uses prune: true.\n"
                "  deletionPolicy: Orphan\n",
                "",
            ),
            encoding="utf-8",
        )
        completed = self.run_guard()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("safe hardening", completed.stdout)


if __name__ == "__main__":
    unittest.main()
