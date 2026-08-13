#!/usr/bin/env python3
"""Classify a pull request into PR Gate validation domains.

This helper is executed from the trusted base checkout by the pull_request_target
workflow. It only reads the proposed revision through verified Git object IDs and
writes GitHub step outputs; it never checks out or executes PR-controlled files.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DOMAIN_NAMES = ("gitops", "helm", "coder", "actions", "functions")
TIER0_FILES = {
    ".github/CODEOWNERS",
    ".github/actionlint.yaml",
    ".github/critical-resources.yaml",
}
TIER0_PREFIXES = (".github/workflows/", "scripts/ci/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="Trusted checkout containing the Git remote")
    parser.add_argument("--base-sha", required=True, help="Trusted PR base SHA")
    parser.add_argument("--head-sha", required=True, help="Proposed PR head SHA")
    parser.add_argument("--pr-number", required=True, help="Pull request number used to fetch the head")
    parser.add_argument("--github-output", type=Path, required=True, help="GitHub step output file")
    return parser.parse_args()


def classify_paths(paths: Iterable[str]) -> dict[str, bool]:
    """Return applicable validator domains for the given changed paths."""
    result = {name: False for name in DOMAIN_NAMES}
    for path in paths:
        if path.startswith(("clusters/", "infrastructure/", "apps/", "monitoring/")):
            result["gitops"] = True
        if path.startswith("charts/") or path == "ct.yaml":
            result["helm"] = True
        if path.startswith("coder/templates/"):
            result["coder"] = True
        if path.startswith((".github/workflows/", ".github/actions/", "scripts/")):
            result["actions"] = True
        if path.startswith("functions/"):
            result["functions"] = True
        if path in TIER0_FILES or path.startswith(TIER0_PREFIXES):
            return {name: True for name in DOMAIN_NAMES}
    return result


def git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=repo, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def main() -> int:
    args = parse_args()
    try:
        git(
            args.repo,
            "fetch",
            "--no-tags",
            "--depth=1",
            "origin",
            f"pull/{args.pr_number}/head:refs/remotes/origin/pr-head",
        )
        checked_out_base = git(args.repo, "rev-parse", "HEAD").decode().strip()
        if checked_out_base != args.base_sha:
            raise RuntimeError(f"trusted checkout {checked_out_base} does not match {args.base_sha}")
        fetched_head = git(args.repo, "rev-parse", "refs/remotes/origin/pr-head").decode().strip()
        if fetched_head != args.head_sha:
            raise RuntimeError(f"fetched pull-request head {fetched_head} does not match {args.head_sha}")
        changed = git(args.repo, "diff", "--name-only", "-z", args.base_sha, args.head_sha)
        paths = [path.decode("utf-8") for path in changed.split(b"\0") if path]
        domains = classify_paths(paths)
    except (RuntimeError, UnicodeDecodeError) as error:
        print(f"::error::Unable to classify PR Gate validation domains: {error}", file=sys.stderr)
        return 1

    lines = [f"base_sha={args.base_sha}", f"head_sha={args.head_sha}"]
    lines.extend(f"{domain}={'true' if domains[domain] else 'false'}" for domain in DOMAIN_NAMES)
    args.github_output.parent.mkdir(parents=True, exist_ok=True)
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
