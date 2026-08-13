#!/usr/bin/env python3
"""Reject changed plaintext Kubernetes Secret manifests from a verified PR diff.

The helper is executed from the trusted base checkout. Proposed content is read
only by explicit Git object ID and never through a PR-controlled script/config.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


ROOTS = ("apps", "clusters", "infrastructure", "monitoring", "functions")
EXCEPTION_PATH = "infrastructure/configs/ci/copilot-agent-rbac/secret.yaml"


class SecretCheckError(RuntimeError):
    """A malformed diff or YAML input that must fail the PR."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.YAMLError(f"duplicate mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="PR head checkout used only as a Git object database")
    parser.add_argument("--base-sha", required=True, help="Trusted base SHA")
    parser.add_argument("--head-sha", required=True, help="Proposed head SHA")
    parser.add_argument("--pr-number", required=True, help="PR number used to verify the fetched head")
    parser.add_argument("--skip-fetch", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=repo, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SecretCheckError(f"Unable to calculate the trusted base/head diff: {detail}")
    return completed.stdout


def verified_revisions(args: argparse.Namespace) -> None:
    if not args.skip_fetch:
        git(args.repo, "fetch", "--no-tags", "--depth=1", "origin", args.base_sha)
        git(
            args.repo,
            "fetch",
            "--no-tags",
            "--depth=1",
            "origin",
            f"pull/{args.pr_number}/head:refs/remotes/origin/pr-head",
        )
    if git(args.repo, "rev-parse", "HEAD").decode().strip() != args.head_sha:
        raise SecretCheckError("Proposed checkout HEAD does not match the PR head SHA")
    if git(args.repo, "rev-parse", args.base_sha).decode().strip() != args.base_sha:
        raise SecretCheckError("Trusted base SHA could not be resolved")
    if not args.skip_fetch and git(args.repo, "rev-parse", "refs/remotes/origin/pr-head").decode().strip() != args.head_sha:
        raise SecretCheckError("Fetched pull-request head does not match the PR payload")


def changed_yaml_paths(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    raw_diff = git(
        repo,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        "--diff-filter=ACMR",
        base_sha,
        head_sha,
        "--",
        *ROOTS,
    )
    fields = raw_diff.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()

    paths: list[str] = []
    index = 0
    while index < len(fields):
        try:
            status = fields[index].decode("ascii")
        except UnicodeDecodeError as error:
            raise SecretCheckError("Trusted diff returned a non-ASCII status") from error
        index += 1
        if not status or status[0] not in "ACMR":
            raise SecretCheckError(f"Trusted diff returned an unexpected status: {status!r}")
        if status[0] in "RC":
            if index + 1 >= len(fields):
                raise SecretCheckError("Trusted diff ended while reading a rename or copy")
            index += 1  # Old path; only the proposed destination is checked.
        if index >= len(fields):
            raise SecretCheckError("Trusted diff ended while reading a changed path")
        try:
            path = fields[index].decode("utf-8")
        except UnicodeDecodeError as error:
            raise SecretCheckError("Trusted diff contains a non-UTF-8 path") from error
        index += 1
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise SecretCheckError(f"Trusted diff returned an unsafe path: {path}")
        if not any(path == root or path.startswith(f"{root}/") for root in ROOTS):
            raise SecretCheckError(f"Trusted diff returned a path outside the GitOps roots: {path}")
        if path.lower().endswith((".yaml", ".yml")):
            paths.append(path)
    return paths


def exact_service_account_token_exception(document: Any) -> bool:
    return (
        isinstance(document, dict)
        and set(document) == {"apiVersion", "kind", "metadata", "type"}
        and document["apiVersion"] == "v1"
        and document["kind"] == "Secret"
        and document["type"] == "kubernetes.io/service-account-token"
        and document["metadata"]
        == {
            "name": "copilot-agent-readonly-token",
            "namespace": "arc-runners",
            "annotations": {"kubernetes.io/service-account.name": "copilot-agent-readonly"},
        }
    )


def find_secret_mappings(value: Any, seen: set[int] | None = None) -> list[dict[str, Any]]:
    if seen is None:
        seen = set()
    if isinstance(value, (dict, list)):
        if id(value) in seen:
            return []
        seen.add(id(value))
    if isinstance(value, dict):
        matches = [value] if value.get("kind") == "Secret" else []
        for child in value.values():
            matches.extend(find_secret_mappings(child, seen))
        return matches
    if isinstance(value, list):
        matches: list[dict[str, Any]] = []
        for child in value:
            matches.extend(find_secret_mappings(child, seen))
        return matches
    return []


def check_changed_secrets(repo: Path, base_sha: str, head_sha: str) -> None:
    for path in changed_yaml_paths(repo, base_sha, head_sha):
        try:
            content = git(repo, "show", f"{head_sha}:{path}")
            documents = list(yaml.load_all(content, Loader=UniqueKeyLoader))
        except (yaml.YAMLError, UnicodeDecodeError) as error:
            raise SecretCheckError(f"Could not parse changed YAML document {path}: {error}") from error
        secret_documents = [secret for document in documents for secret in find_secret_mappings(document)]
        if not secret_documents:
            continue
        if (
            path == EXCEPTION_PATH
            and len(documents) == 1
            and len(secret_documents) == 1
            and secret_documents[0] is documents[0]
            and exact_service_account_token_exception(documents[0])
        ):
            continue
        raise SecretCheckError(
            f"Bare kind: Secret manifest in {path} is forbidden; use SealedSecret or a consumer-native Secret reference."
        )


def main() -> int:
    args = parse_args()
    try:
        verified_revisions(args)
        check_changed_secrets(args.repo, args.base_sha, args.head_sha)
    except SecretCheckError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
