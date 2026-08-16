#!/usr/bin/env python3
"""Resolve candidate kubeconform schema locations from inert policy data."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as error:  # pragma: no cover - exercised by CI dependency setup
    raise SystemExit(f"PyYAML is required by resolve_kubeconform_schema_locations.py: {error}")


CATALOG_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SCHEMA_TEMPLATE = "{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, required=True, help="Inert proposed pr-gate workflow YAML")
    parser.add_argument(
        "--schemas-root",
        type=Path,
        required=True,
        help="Inert proposed local-schema directory, if present",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output file with one schema location per line")
    return parser.parse_args()


def catalog_commit(workflow: Path) -> str:
    try:
        document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"cannot parse candidate workflow {workflow}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("candidate workflow must be a YAML mapping")
    environment = document.get("env")
    if not isinstance(environment, dict):
        raise ValueError("candidate workflow is missing top-level env mapping")
    commit = environment.get("CRDS_CATALOG_COMMIT")
    if not isinstance(commit, str) or not CATALOG_COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("candidate CRDS_CATALOG_COMMIT must be exactly a 40-character lowercase SHA")
    return commit


def schema_locations(workflow: Path, schemas_root: Path) -> list[str]:
    locations: list[str] = []
    if schemas_root.exists():
        if not schemas_root.is_dir():
            raise ValueError(f"candidate schemas root is not a directory: {schemas_root}")
        locations.append(str(schemas_root / SCHEMA_TEMPLATE))
    commit = catalog_commit(workflow)
    locations.append(
        "https://raw.githubusercontent.com/datreeio/CRDs-catalog/"
        f"{commit}/{SCHEMA_TEMPLATE}"
    )
    return locations


def main() -> int:
    args = parse_args()
    try:
        locations = schema_locations(args.workflow, args.schemas_root)
    except ValueError as error:
        print(f"Unable to resolve candidate kubeconform schema locations: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(locations) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
