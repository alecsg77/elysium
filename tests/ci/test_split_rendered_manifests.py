#!/usr/bin/env python3
"""Tests for one-document kubeconform input preparation."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/split_rendered_manifests.py"


def load_module():
    spec = importlib.util.spec_from_file_location("split_rendered_manifests", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SPLITTER = load_module()


class SplitRenderedManifestsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.input = self.root / "rendered"
        self.output = self.root / "split"
        self.input.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_same_name_in_multiple_namespaces_gets_distinct_single_document_files(self) -> None:
        (self.input / "aggregate.yaml").write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: alpha\n---\n"
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: settings\n  namespace: beta\n",
            encoding="utf-8",
        )
        self.assertEqual(SPLITTER.split_rendered_manifests(self.input, self.output), 2)
        documents = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(self.output.rglob("*.yaml"))]
        self.assertEqual({document["metadata"]["namespace"] for document in documents}, {"alpha", "beta"})
        self.assertTrue(all(len(list(yaml.safe_load_all(path.read_text(encoding="utf-8")))) == 1 for path in self.output.rglob("*.yaml")))

    def test_non_mapping_rendered_document_fails_closed(self) -> None:
        (self.input / "invalid.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
        with self.assertRaisesRegex(SPLITTER.SplitError, "not a mapping"):
            SPLITTER.split_rendered_manifests(self.input, self.output)


if __name__ == "__main__":
    unittest.main()
