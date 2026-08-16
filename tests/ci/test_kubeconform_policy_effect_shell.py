#!/usr/bin/env python3
"""Behavior tests for the trusted kubeconform policy-effect helper."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/run_kubeconform_policy_effect.sh"
CATALOG = "59abc9f9403c92e3d8f8873e250ca10dcd5b2c0d"


class KubeconformPolicyEffectShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.rendered = self.root / "rendered"
        self.rendered.mkdir()
        self.base_schemas = self.root / "base-schemas"
        self.candidate = self.root / "candidate"
        self.candidate_schemas = self.candidate / ".github/schemas"
        self.candidate_schemas.mkdir(parents=True)
        workflow = self.candidate / ".github/workflows/pr-gate.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(f"env:\n  CRDS_CATALOG_COMMIT: {CATALOG}\n", encoding="utf-8")
        self.workflow = workflow
        self.report_dir = self.root / "reports"
        self.binary_dir = self.root / "bin"
        self.binary_dir.mkdir()
        fake = self.binary_dir / "kubeconform"
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "last=\"${!#}\"\n"
            "if [[ \"$last\" == *invalid-native-customresourcedefinition.yaml ]]; then\n"
            "  printf '%s\\n' '{\"resources\":[{\"status\":\"statusInvalid\"}],\"summary\":{\"valid\":0,\"invalid\":1,\"errors\":0,\"skipped\":0}}'\n"
            "  exit 1\n"
            "fi\n"
            "printf '%s\\n' '{\"resources\":[],\"summary\":{\"valid\":1,\"invalid\":0,\"errors\":0,\"skipped\":0}}'\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def add_candidate_schema_bundle(self, checksum: str | None = None) -> None:
        schema = self.candidate_schemas / "apiextensions.k8s.io/customresourcedefinition_v1.json"
        schema.parent.mkdir(parents=True)
        schema.write_text('{"type":"object"}\n', encoding="utf-8")
        actual = hashlib.sha256(schema.read_bytes()).hexdigest()
        (self.candidate_schemas / "SHA256SUMS").write_text(
            f"{checksum or actual}  apiextensions.k8s.io/customresourcedefinition_v1.json\n",
            encoding="utf-8",
        )
        (self.candidate_schemas / "README.md").write_text("schema provenance\n", encoding="utf-8")

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ | {"PATH": f"{self.binary_dir}{os.pathsep}{os.environ['PATH']}"}
        return subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--rendered-root",
                str(self.rendered),
                "--base-schemas-root",
                str(self.base_schemas),
                "--base-catalog-commit",
                CATALOG,
                "--candidate-workflow",
                str(self.workflow),
                "--candidate-schemas-root",
                str(self.candidate_schemas),
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--report-dir",
                str(self.report_dir),
            ],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

    def test_candidate_native_schema_requires_verified_bundle_and_rejects_fixture(self) -> None:
        self.add_candidate_schema_bundle()
        completed = self.run_helper()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue((self.report_dir / "invalid-native-customresourcedefinition.json").is_file())

    def test_candidate_schema_checksum_failure_fails_closed(self) -> None:
        self.add_candidate_schema_bundle(checksum="0" * 64)
        completed = self.run_helper()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("FAILED", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
