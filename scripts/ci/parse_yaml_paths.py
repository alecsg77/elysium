#!/usr/bin/env python3
"""Parse selected YAML trees without executing configuration from those trees."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Tree containing YAML data to parse")
    parser.add_argument("--directory", action="append", required=True, help="Directory relative to --root")
    return parser.parse_args()


def yaml_paths(root: Path, directories: list[str]) -> list[Path]:
    paths: list[Path] = []
    for relative in directories:
        directory = root / relative
        if not directory.is_dir():
            raise ValueError(f"YAML directory is missing: {directory}")
        paths.extend(directory.rglob("*.yaml"))
    return sorted(paths)


def main() -> int:
    args = parse_args()
    try:
        for path in yaml_paths(args.root, args.directory):
            with path.open(encoding="utf-8") as stream:
                list(yaml.safe_load_all(stream))
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"::error::Could not parse YAML data: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
