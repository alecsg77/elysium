#!/usr/bin/env python3
"""Exercise image selection using real temporary Git histories."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CHECKER = Path(__file__).resolve().parents[2] / "scripts/ci/plan-image-builds.py"


class ImageBuilds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Image tests")
        self.write("images/first/VERSION", "1.0.0\n")
        self.write("images/first/context/Dockerfile", "FROM scratch\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture", "--allow-empty")
        return self.git("rev-parse", "HEAD")

    def run_plan(self, base=None, succeeds=True):
        output = self.root / "matrix.json"
        result = subprocess.run([
            "python3", str(CHECKER), "--root", str(self.root), "--base", base or self.base,
            "--head", self.git("rev-parse", "HEAD"), "--output", str(output),
        ], capture_output=True, text=True, check=False)
        if not succeeds:
            self.assertNotEqual(result.returncode, 0)
            return result.stderr
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(output.read_text())["include"]

    def test_unchanged(self):
        self.assertEqual(self.run_plan(), [])

    def test_documentation_only(self):
        self.write("images/README.md", "Catalog\n")
        self.write("images/first/README.md", "Usage\n")
        self.commit()
        self.assertEqual(self.run_plan(), [])

    def test_first_publication(self):
        selected = self.run_plan(base="0" * 40)
        self.assertEqual([entry["image"] for entry in selected], ["first"])
        self.assertEqual(selected[0]["version"], "1.0.0")
        self.assertRegex(selected[0]["input_hash"], r"^[a-f0-9]{64}$")

    def test_new_image_only(self):
        self.write("images/second/VERSION", "0.1.0\n")
        self.write("images/second/context/Dockerfile", "FROM scratch\n")
        self.commit()
        self.assertEqual([entry["image"] for entry in self.run_plan()], ["second"])

    def test_missing_version(self):
        self.write("images/second/context/Dockerfile", "FROM scratch\n")
        self.commit()
        self.run_plan(succeeds=False)

    def test_changed_inputs_without_bump(self):
        self.write("images/first/context/start.sh", "#!/bin/sh\nexit 0\n")
        self.commit()
        self.assertIn("require VERSION greater than 1.0.0", self.run_plan(succeeds=False))

    def test_changed_inputs_with_bump(self):
        before = self.run_plan(base="0" * 40)[0]["input_hash"]
        self.write("images/first/context/start.sh", "#!/bin/sh\nexit 0\n")
        self.write("images/first/VERSION", "1.0.1\n")
        self.commit()
        selected = self.run_plan()
        self.assertEqual(selected[0]["version"], "1.0.1")
        self.assertNotEqual(selected[0]["input_hash"], before)

    def test_version_is_image_metadata(self):
        self.write("images/first/VERSION", "1.1.0\n")
        self.commit()
        self.assertEqual(self.run_plan()[0]["version"], "1.1.0")

    def test_numeric_ordering(self):
        self.write("images/first/VERSION", "1.9.0\n")
        base = self.commit()
        self.write("images/first/VERSION", "1.10.0\n")
        self.commit()
        self.assertEqual(self.run_plan(base=base)[0]["version"], "1.10.0")

    def test_invalid_versions(self):
        for value in ["01.0.0", "v1.0.0", "1.0", "1.0.1-r1", "1.0.0+build"]:
            with self.subTest(value=value):
                self.write("images/first/VERSION", value + "\n")
                self.commit()
                self.assertIn("stable SemVer", self.run_plan(succeeds=False))

    def test_downgrade(self):
        self.write("images/first/VERSION", "0.9.0\n")
        self.commit()
        self.run_plan(succeeds=False)

    def test_deleted_image(self):
        self.git("rm", "-qr", "images/first")
        self.commit()
        self.assertEqual(self.run_plan(), [])

    def test_workflow_change_only(self):
        self.write(".github/workflows/build-images.yml", "name: Build\n")
        self.commit()
        self.assertEqual(self.run_plan(), [])


if __name__ == "__main__":
    unittest.main()
