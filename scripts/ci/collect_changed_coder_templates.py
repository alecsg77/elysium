#!/usr/bin/env python3
"""Write PR Gate's changed Coder template list from verified Git revisions.

This helper is invoked from the trusted base checkout. Template directories in the
proposed checkout are data only; no Terraform or PR-controlled script is run here.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="Proposed checkout containing the Git object database")
    parser.add_argument("--base-sha", required=True, help="Trusted base SHA")
    parser.add_argument("--head-sha", required=True, help="Proposed PR head SHA")
    parser.add_argument("--pr-number", required=True, help="Pull request number used to verify the head")
    parser.add_argument("--output", type=Path, required=True, help="File to receive one template directory name per line")
    return parser.parse_args()


def git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=repo, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def changed_templates(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    changed = git(repo, "diff", "--name-only", "-z", base_sha, head_sha, "--", "coder/templates/")
    templates = {
        path.decode("utf-8").split("/", 3)[2]
        for path in changed.split(b"\0")
        if path and path.startswith(b"coder/templates/") and len(path.split(b"/")) >= 3
    }
    return sorted(templates)


def all_templates(repo: Path) -> list[str]:
    directory = repo / "coder/templates"
    if not directory.is_dir():
        raise RuntimeError(f"Coder template directory is missing: {directory}")
    return sorted(path.name for path in directory.iterdir() if path.is_dir())


def main() -> int:
    args = parse_args()
    try:
        git(args.repo, "fetch", "--no-tags", "--depth=1", "origin", args.base_sha)
        git(
            args.repo,
            "fetch",
            "--no-tags",
            "--depth=1",
            "origin",
            f"pull/{args.pr_number}/head:refs/remotes/origin/pr-head",
        )
        if git(args.repo, "rev-parse", "refs/remotes/origin/pr-head").decode().strip() != args.head_sha:
            raise RuntimeError("Fetched pull-request head does not match the PR payload")
        templates = changed_templates(args.repo, args.base_sha, args.head_sha) or all_templates(args.repo)
        if not templates:
            raise RuntimeError("No Coder templates are available to validate")
    except (RuntimeError, UnicodeDecodeError) as error:
        print(f"::error::Unable to identify Coder templates: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(templates) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
