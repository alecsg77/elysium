#!/usr/bin/env python3
"""Identify Bitnami SealedSecret ciphertext without suppressing other YAML content.

This trusted CI helper recognizes only direct scalar values in
``spec.encryptedData`` for a YAML document whose top-level ``kind`` is exactly
``SealedSecret``. It deliberately fails closed: malformed YAML, duplicate keys,
aliases, and unsupported structures receive no ciphertext treatment.

The helper never prints source content. Its diff-filter command writes a private
Gitleaks input file containing all added lines, with only recognized ciphertext
scalar segments replaced by a fixed non-secret marker.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    import yaml
except ImportError as error:  # pragma: no cover - exercised by CI dependency setup
    raise SystemExit(f"PyYAML is required by sealed_secret_ciphertext_policy.py: {error}")


CIPHERTEXT_MARKER = "<sealed-secret-ciphertext>"
HUNK_HEADER = re.compile(r"^@@ -[0-9]+(?:,[0-9]+)? \+(?P<line>[0-9]+)(?:,[0-9]+)? @@")


class CiphertextPolicyError(RuntimeError):
    """Raised when trusted Git data cannot be processed safely."""


@dataclass(frozen=True)
class SourceRange:
    """A half-open scalar range expressed in zero-based YAML source locations."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int


def is_yaml_path(path: str) -> bool:
    return path.lower().endswith((".yaml", ".yml"))


def unique_mapping_value(mapping: yaml.MappingNode, expected_key: str) -> yaml.Node | None:
    """Return a direct mapping value only when the key appears exactly once."""
    matches = [
        value
        for key, value in mapping.value
        if isinstance(key, yaml.ScalarNode) and key.value == expected_key
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def direct_scalar_value(
    content: str, key: yaml.Node, value: yaml.Node
) -> SourceRange | None:
    """Return a source range only for an unaliased direct ``key: scalar`` value."""
    if not isinstance(key, yaml.ScalarNode) or not isinstance(value, yaml.ScalarNode):
        return None
    if value.start_mark.index < key.end_mark.index:
        return None

    between = content[key.end_mark.index : value.start_mark.index]
    if not re.fullmatch(r":[ \t]*(?:\r?\n[ \t]*)*", between):
        # Anchors, aliases, comments before a continuation value, and other
        # unsupported representations remain scanner-visible.
        return None

    return SourceRange(
        start_line=value.start_mark.line,
        start_column=value.start_mark.column,
        end_line=value.end_mark.line,
        end_column=value.end_mark.column,
    )


def mapping_keys_are_unambiguous(node: yaml.Node | None, seen: set[int] | None = None) -> bool:
    """Reject duplicate, complex, and non-string mapping keys anywhere in a document."""
    if node is None:
        return True
    if seen is None:
        seen = set()
    if id(node) in seen:
        return True
    seen.add(id(node))

    if isinstance(node, yaml.MappingNode):
        keys: set[str] = set()
        for key, value in node.value:
            if (
                not isinstance(key, yaml.ScalarNode)
                or key.tag != "tag:yaml.org,2002:str"
                or key.value in keys
            ):
                return False
            keys.add(key.value)
            if not mapping_keys_are_unambiguous(value, seen):
                return False
        return True
    if isinstance(node, yaml.SequenceNode):
        return all(mapping_keys_are_unambiguous(value, seen) for value in node.value)
    return True


def contains_alias(content: str) -> bool:
    """Treat YAML aliases as unsupported rather than resolving their source marks."""
    try:
        return any(isinstance(event, yaml.events.AliasEvent) for event in yaml.parse(content))
    except yaml.YAMLError:
        return True


def document_ciphertext_ranges(content: str, document: yaml.Node | None) -> list[SourceRange]:
    """Return direct SealedSecret ciphertext ranges for one parsed document."""
    if not isinstance(document, yaml.MappingNode):
        return []

    kind = unique_mapping_value(document, "kind")
    if not isinstance(kind, yaml.ScalarNode) or kind.value != "SealedSecret":
        return []

    spec = unique_mapping_value(document, "spec")
    if not isinstance(spec, yaml.MappingNode):
        return []
    encrypted_data = unique_mapping_value(spec, "encryptedData")
    if not isinstance(encrypted_data, yaml.MappingNode):
        return []

    keys: set[str] = set()
    ranges: list[SourceRange] = []
    for key, value in encrypted_data.value:
        # Duplicate or complex keys make the selected structure ambiguous. Do
        # not exempt any values from this document in that case.
        if not isinstance(key, yaml.ScalarNode) or key.value in keys:
            return []
        keys.add(key.value)
        scalar_range = direct_scalar_value(content, key, value)
        if scalar_range is not None:
            ranges.append(scalar_range)
    return ranges


def ciphertext_ranges(content: str) -> list[SourceRange]:
    """Return recognized ciphertext ranges, or none when parsing is unsafe."""
    if contains_alias(content):
        return []
    try:
        documents = list(yaml.compose_all(content))
    except yaml.YAMLError:
        return []

    ranges: list[SourceRange] = []
    for document in documents:
        if not mapping_keys_are_unambiguous(document):
            # One malformed or ambiguous document invalidates the file-wide
            # exemption, so a mixed multi-document file cannot hide content.
            return []
        ranges.extend(document_ciphertext_ranges(content, document))
    return ranges


def redact_line(line: str, line_number: int, ranges: Iterable[SourceRange]) -> str:
    """Replace recognized scalar portions of one 1-based source line with a marker."""
    replacements: list[tuple[int, int]] = []
    zero_based_line = line_number - 1
    for source_range in ranges:
        if zero_based_line < source_range.start_line or zero_based_line > source_range.end_line:
            continue
        start = source_range.start_column if zero_based_line == source_range.start_line else 0
        end = source_range.end_column if zero_based_line == source_range.end_line else len(line)
        start = min(max(start, 0), len(line))
        end = min(max(end, start), len(line))
        replacements.append((start, end))

    if not replacements:
        return line

    # Valid YAML scalar node ranges cannot overlap. Treat an unexpected overlap
    # as unsafe rather than coalescing it into an exemption.
    replacements.sort()
    if any(right[0] < left[1] for left, right in zip(replacements, replacements[1:])):
        return line

    chunks: list[str] = []
    cursor = 0
    for start, end in replacements:
        chunks.append(line[cursor:start])
        chunks.append(CIPHERTEXT_MARKER)
        cursor = end
    chunks.append(line[cursor:])
    return "".join(chunks)


def git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=repo, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        raise CiphertextPolicyError("Unable to calculate the trusted base-to-head diff")
    return completed.stdout


def changed_paths(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    raw = git(
        repo,
        "diff",
        "--name-only",
        "-z",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--diff-filter=ACMR",
        base_sha,
        head_sha,
        "--",
    )
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()

    paths: list[str] = []
    for field in fields:
        try:
            path = field.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CiphertextPolicyError("Trusted diff contains a non-UTF-8 path") from error
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or not path:
            raise CiphertextPolicyError("Trusted diff contains an unsafe path")
        paths.append(path)
    return paths


def added_lines(repo: Path, base_sha: str, head_sha: str, path: str) -> list[tuple[int, str]]:
    try:
        patch = git(
            repo,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--text",
            "--no-renames",
            "--unified=0",
            base_sha,
            head_sha,
            "--",
            path,
        ).decode("utf-8")
    except UnicodeDecodeError as error:
        raise CiphertextPolicyError("Trusted diff contains non-UTF-8 content") from error

    result: list[tuple[int, str]] = []
    head_line: int | None = None
    for raw_line in patch.splitlines():
        match = HUNK_HEADER.match(raw_line)
        if match is not None:
            head_line = int(match.group("line"))
            continue
        if head_line is None:
            continue
        if raw_line.startswith("\\ No newline at end of file"):
            continue
        if raw_line.startswith("+"):
            result.append((head_line, raw_line[1:]))
            head_line += 1
        elif raw_line.startswith("-"):
            continue
        elif raw_line.startswith(" "):
            head_line += 1
        else:
            raise CiphertextPolicyError("Trusted diff contains an unexpected hunk record")
    return result


def head_ciphertext_ranges(repo: Path, head_sha: str, path: str) -> list[SourceRange]:
    if not is_yaml_path(path):
        return []
    try:
        content = git(repo, "show", f"{head_sha}:{path}").decode("utf-8")
    except (CiphertextPolicyError, UnicodeDecodeError):
        # A malformed or non-text YAML candidate remains entirely scanner-visible.
        return []
    return ciphertext_ranges(content)


def filtered_added_lines(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    """Return every added line, replacing only recognized ciphertext segments."""
    result: list[str] = []
    for path in changed_paths(repo, base_sha, head_sha):
        ranges = head_ciphertext_ranges(repo, head_sha, path)
        for line_number, line in added_lines(repo, base_sha, head_sha, path):
            result.append(redact_line(line, line_number, ranges))
    return result


def write_filtered_added_diff(repo: Path, base_sha: str, head_sha: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for line in filtered_added_lines(repo, base_sha, head_sha):
            stream.write(line)
            stream.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    filter_parser = subparsers.add_parser("filter-added-diff")
    filter_parser.add_argument("--repo", type=Path, required=True)
    filter_parser.add_argument("--base-sha", required=True)
    filter_parser.add_argument("--head-sha", required=True)
    filter_parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_filtered_added_diff(args.repo, args.base_sha, args.head_sha, args.output)
    except CiphertextPolicyError as error:
        print(f"::error title=SealedSecret ciphertext policy integrity error::{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
