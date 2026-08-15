#!/usr/bin/env python3
"""Normalize Checkov 3.3 JSON reports before trusted quality-ratchet comparison.

Checkov 3.3 omits ``results.parsing_errors`` when there are no parsing errors.
The quality-ratchet parser intentionally requires an explicit list so malformed
scanner output fails closed. This helper accepts only that absent-and-equivalent
shape and writes the explicit empty list to a separate trusted output path.

Checkov's container action may make its workspace report files root-owned. The
helper therefore never mutates its input report; callers provide a writable
output path, normally under ``RUNNER_TEMP``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class CheckovReportError(RuntimeError):
    """Raised when a Checkov report is missing required trustworthy structure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        action="append",
        nargs=2,
        metavar=("INPUT", "OUTPUT"),
        required=True,
        help="Read INPUT Checkov JSON and write a normalized copy to OUTPUT; may be specified multiple times.",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CheckovReportError(f"Checkov report is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise CheckovReportError(f"Checkov report is not valid JSON: {path}: {error}") from error

    if not isinstance(payload, dict):
        raise CheckovReportError(f"Checkov report must be a JSON object: {path}")
    return payload


def normalize_report(input_path: Path, output_path: Path) -> None:
    """Validate INPUT and write its normalized representation to OUTPUT."""
    payload = load_report(input_path)
    results = payload.get("results")
    if not isinstance(results, dict):
        raise CheckovReportError(f"Checkov report has no results object: {input_path}")

    failed_checks = results.get("failed_checks")
    if not isinstance(failed_checks, list):
        raise CheckovReportError(f"Checkov report has invalid failed_checks list: {input_path}")

    if "parsing_errors" not in results:
        results["parsing_errors"] = []
    else:
        parsing_errors = results["parsing_errors"]
        if not isinstance(parsing_errors, list):
            raise CheckovReportError(f"Checkov report has invalid parsing_errors list: {input_path}")
        if parsing_errors:
            raise CheckovReportError(f"Checkov report contains parsing errors: {input_path}")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    except OSError as error:
        raise CheckovReportError(f"Cannot write normalized Checkov report: {output_path}: {error}") from error


def main() -> int:
    args = parse_args()
    try:
        for input_path, output_path in args.report:
            normalize_report(input_path, output_path)
    except CheckovReportError as error:
        raise SystemExit(str(error)) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
