#!/usr/bin/env python3
"""Tests for the checked-in native CustomResourceDefinition schema generator."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/generate_native_crd_schema.py"


def load_module():
    spec = importlib.util.spec_from_file_location(SCRIPT.stem, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = load_module()


def openapi_fixture() -> dict[str, object]:
    root_name = GENERATOR.OPENAPI_CRD_SCHEMA
    return {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                root_name: {
                    "type": "object",
                    "properties": {
                        "apiVersion": {"type": "string"},
                        "kind": {"type": "string"},
                        "metadata": {"$ref": "#/components/schemas/ObjectMeta"},
                        "spec": {"$ref": "#/components/schemas/Spec"},
                        "status": {"$ref": "#/components/schemas/Status"},
                    },
                },
                "ObjectMeta": {"type": "object"},
                "Spec": {"type": "object"},
                "Status": {"type": "object"},
            }
        },
    }


class NativeCRDSchemaGeneratorTest(unittest.TestCase):
    def test_derived_schema_closes_and_requires_native_envelope(self) -> None:
        schema = GENERATOR.derive_schema(openapi_fixture())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["apiVersion", "kind", "metadata", "spec"])
        self.assertEqual(schema["properties"]["apiVersion"], {"const": "apiextensions.k8s.io/v1"})
        self.assertEqual(schema["properties"]["kind"], {"const": "CustomResourceDefinition"})
        self.assertIn("status", schema["properties"])
        self.assertIn("ObjectMeta", schema["components"]["schemas"])

    def test_rejects_external_component_reference(self) -> None:
        fixture = openapi_fixture()
        schemas = fixture["components"]["schemas"]
        schemas["Spec"] = {"$ref": "https://example.invalid/schema.json"}
        with self.assertRaisesRegex(ValueError, "non-local reference"):
            GENERATOR.derive_schema(fixture)


if __name__ == "__main__":
    unittest.main()
