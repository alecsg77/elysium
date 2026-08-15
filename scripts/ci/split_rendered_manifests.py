#!/usr/bin/env python3
"""Split rendered multi-document Kubernetes YAML into one trusted document per file."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml


class SplitError(RuntimeError):
    """Raised when rendered YAML cannot be safely prepared for a validator."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Directory of rendered YAML artifacts")
    parser.add_argument("--output", type=Path, required=True, help="Directory for one-document YAML files")
    return parser.parse_args()


def output_path(output: Path, source: Path, input_root: Path, document_index: int) -> Path:
    relative = source.relative_to(input_root)
    return output / relative.with_suffix("") / f"{document_index:04d}.yaml"


def split_rendered_manifests(input_root: Path, output: Path) -> int:
    if not input_root.is_dir():
        raise SplitError(f"Rendered input directory is missing: {input_root}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    count = 0
    for source in sorted(input_root.rglob("*.yaml")):
        try:
            documents = list(yaml.safe_load_all(source.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError) as error:
            raise SplitError(f"Cannot parse rendered YAML {source}: {error}") from error
        for index, document in enumerate(documents, start=1):
            if document is None:
                continue
            if not isinstance(document, dict):
                raise SplitError(f"Rendered YAML {source} document {index} is not a mapping")
            destination = output_path(output, source, input_root, index)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                yaml.safe_dump(document, sort_keys=False, explicit_start=True), encoding="utf-8"
            )
            count += 1
    if count == 0:
        raise SplitError(f"Rendered input directory contains no YAML documents: {input_root}")
    return count


def main() -> int:
    args = parse_args()
    try:
        count = split_rendered_manifests(args.input, args.output)
    except SplitError as error:
        print(f"::error title=Rendered manifest split failed::{error}", file=sys.stderr)
        return 1
    print(f"Prepared {count} single-document YAML files for kubeconform.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
