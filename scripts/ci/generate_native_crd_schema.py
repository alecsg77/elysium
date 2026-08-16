#!/usr/bin/env python3
"""Derive the native Kubernetes CustomResourceDefinition JSON Schema from OpenAPI v3."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


OPENAPI_CRD_SCHEMA = (
    "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1.CustomResourceDefinition"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Pinned Kubernetes OpenAPI v3 JSON input")
    parser.add_argument("--output", type=Path, required=True, help="Derived self-contained JSON Schema output")
    return parser.parse_args()


def load_openapi(source: Path) -> dict[str, Any]:
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load OpenAPI source {source}: {error}") from error
    if not isinstance(document, dict) or document.get("openapi") != "3.0.0":
        raise ValueError("source must be an OpenAPI v3.0.0 document")
    components = document.get("components")
    if not isinstance(components, dict) or not isinstance(components.get("schemas"), dict):
        raise ValueError("source must contain components.schemas")
    if OPENAPI_CRD_SCHEMA not in components["schemas"]:
        raise ValueError(f"source does not define {OPENAPI_CRD_SCHEMA}")
    return document


def validate_references(value: Any, schema_names: set[str]) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            if not reference.startswith("#/components/schemas/"):
                raise ValueError(f"schema has a non-local reference {reference!r}")
            target = reference.removeprefix("#/components/schemas/")
            if target not in schema_names:
                raise ValueError(f"schema reference has no local target {reference!r}")
        for item in value.values():
            validate_references(item, schema_names)
    elif isinstance(value, list):
        for item in value:
            validate_references(item, schema_names)


def derive_schema(openapi: dict[str, Any]) -> dict[str, Any]:
    components = openapi["components"]
    schemas = components["schemas"]
    if not isinstance(schemas, dict):  # defended by load_openapi for direct callers
        raise ValueError("source components.schemas must be an object")
    schema_names = set(schemas)
    validate_references(schemas, schema_names)

    root = schemas[OPENAPI_CRD_SCHEMA]
    if not isinstance(root, dict) or not isinstance(root.get("properties"), dict):
        raise ValueError("native CRD OpenAPI schema must define properties")
    properties = root["properties"]
    for required_property in ("metadata", "spec", "status"):
        if required_property not in properties:
            raise ValueError(f"native CRD OpenAPI schema is missing {required_property}")

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Kubernetes apiextensions.k8s.io/v1 CustomResourceDefinition",
        "type": "object",
        "additionalProperties": False,
        "required": ["apiVersion", "kind", "metadata", "spec"],
        "properties": {
            "apiVersion": {"const": "apiextensions.k8s.io/v1"},
            "kind": {"const": "CustomResourceDefinition"},
            "metadata": properties["metadata"],
            "spec": properties["spec"],
            "status": properties["status"],
        },
        "components": {"schemas": schemas},
    }


def canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    args = parse_args()
    try:
        schema = derive_schema(load_openapi(args.source))
    except ValueError as error:
        print(f"Unable to derive native CRD schema: {error}", file=sys.stderr)
        return 1
    rendered = canonical_json(schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"sha256 {hashlib.sha256(rendered.encode('utf-8')).hexdigest()}  {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
